"""Celery tasks for file processing operations."""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import delete, select

from ..celery_app import celery_app
from ..config import get_settings
from ..database import get_async_db
from ..models.transaction import Transaction
from ..models.upload import FileUpload
from ..services.data_transformer import DataTransformerService
from ..services.file_processor import FileProcessorService
from ..utils.exceptions import FileProcessingError

settings = get_settings()


@celery_app.task(bind=True)
def process_uploaded_file(self, upload_id: str) -> Dict[str, Any]:
    """
    Process an uploaded file: parse, validate, transform, and store transactions.

    Args:
        upload_id: ID of the uploaded file to process

    Returns:
        Processing results dictionary
    """
    # Use synchronous database operations to avoid async context issues
    from sqlalchemy import select

    from ..database import SessionLocal

    file_processor = FileProcessorService()
    data_transformer = DataTransformerService()

    with SessionLocal() as db:
        try:
            # Update task status
            self.update_state(state="PROGRESS", meta={"status": "Loading file"})

            # Get upload record
            upload = db.execute(
                select(FileUpload).where(FileUpload.id == upload_id)
            ).scalar_one_or_none()

            if not upload:
                raise FileProcessingError(f"Upload {upload_id} not found")

            # Update upload status
            upload.status = "processing"
            db.commit()

            # Read file from disk (access attributes within session context)
            filename = upload.filename
            original_filename = upload.original_filename
            file_type = upload.file_type
            file_path = os.path.join(settings.upload_dir, filename)
            if not os.path.exists(file_path):
                raise FileProcessingError(f"File not found: {file_path}")

            self.update_state(state="PROGRESS", meta={"status": "Parsing file"})

            # Parse file
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Process file and convert to list
            parsed_data = list(
                file_processor.process_file(file_content, original_filename, file_type)
            )

            if not parsed_data or len(parsed_data) == 0:
                raise FileProcessingError("No valid data found in file")

            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "Transforming data",
                    "records_found": len(parsed_data),
                },
            )

            # Transform data
            original_count = len(parsed_data)
            transactions_df = data_transformer.transform_transactions(
                parsed_data, str(upload_id)
            )

            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "Storing transactions",
                    "original_count": original_count,
                    "final_count": len(transactions_df),
                },
            )

            # Store transactions in database
            transactions_stored = 0
            batch_size = 1000

            for i in range(0, len(transactions_df), batch_size):
                batch = transactions_df.iloc[i : i + batch_size]

                # Convert batch to Transaction objects
                transaction_objects = []
                for _, row in batch.iterrows():
                    transaction = Transaction(
                        id=row["id"],
                        upload_id=upload_id,
                        amount=float(row["amount"]),
                        timestamp=row["timestamp"],
                        account_id=str(row["account_id"]),
                        external_transaction_id=row.get("external_transaction_id"),
                        raw_data=row["raw_data"],
                        processed_data={
                            "year": int(row.get("year", 0)),
                            "month": int(row.get("month", 0)),
                            "day": int(row.get("day", 0)),
                            "hour": int(row.get("hour", 0)),
                            "day_of_week": int(row.get("day_of_week", 0)),
                            "is_weekend": bool(row.get("is_weekend", False)),
                            "is_business_hours": bool(
                                row.get("is_business_hours", False)
                            ),
                            "amount_abs": float(row.get("amount_abs", 0)),
                            "is_debit": bool(row.get("is_debit", False)),
                            "is_credit": bool(row.get("is_credit", False)),
                            "amount_category": str(
                                row.get("amount_category", "unknown")
                            ),
                            "transaction_sequence": int(
                                row.get("transaction_sequence", 0)
                            ),
                            "time_since_prev_hours": (
                                float(row.get("time_since_prev_hours", 0))
                                if row.get("time_since_prev_hours")
                                else None
                            ),
                        },
                    )
                    transaction_objects.append(transaction)

                # Bulk insert batch
                db.add_all(transaction_objects)
                db.commit()

                transactions_stored += len(transaction_objects)

                # Update progress
                progress = (transactions_stored / len(transactions_df)) * 100
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "status": f"Storing transactions "
                        f"({transactions_stored}/{len(transactions_df)})",
                        "progress": progress,
                    },
                )

            # Get transformation stats
            transformation_stats = data_transformer.get_transformation_stats(
                original_count, transactions_df
            )

            # Update upload record with success
            upload.status = "processed"
            upload.processed_at = datetime.utcnow()
            if upload.file_metadata is None:
                upload.file_metadata = {}
            upload.file_metadata.update(
                {
                    "processing_completed": True,
                    "transformation_stats": transformation_stats,
                    "transactions_stored": transactions_stored,
                    "processing_time_seconds": None,  # Calculated by Celery
                }
            )
            db.commit()

            return {
                "status": "completed",
                "upload_id": upload_id,
                "transactions_stored": transactions_stored,
                "transformation_stats": transformation_stats,
            }

        except Exception as e:
            # Update upload with error status
            try:
                upload.status = "failed"
                upload.processed_at = datetime.utcnow()
                upload.error_message = str(e)
                db.commit()
            except Exception:
                pass  # Don't fail on status update failure

            # Re-raise for Celery to handle
            raise FileProcessingError(f"File processing failed: {str(e)}")


@celery_app.task
def validate_file_async(
    file_content: bytes, filename: str, file_type: str
) -> Dict[str, Any]:
    """
    Validate a file asynchronously before processing.

    Args:
        file_content: Raw file content
        filename: Original filename
        file_type: Detected file type

    Returns:
        Validation results
    """
    file_processor = FileProcessorService()

    try:
        # Validate file structure
        validation_result = file_processor.validate_file(
            file_content, filename, file_type
        )

        # If valid, get a sample of parsed data for preview
        if validation_result.get("valid", False):
            try:
                parsed_sample = list(
                    file_processor.process_file(file_content, filename, file_type)
                )
                # First 5 rows
                validation_result["sample_data"] = parsed_sample[:5]
                validation_result["total_rows_estimated"] = (
                    len(parsed_sample) if len(parsed_sample) < 10 else "10+"
                )
            except Exception as e:
                validation_result["sample_error"] = str(e)

        return validation_result

    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "validation_type": "async_validation",
        }


@celery_app.task
def cleanup_old_uploads() -> Dict[str, Any]:
    """
    Periodic task to clean up old upload files and records.

    Returns:
        Cleanup results
    """
    return asyncio.run(_cleanup_old_uploads_async())


async def _cleanup_old_uploads_async() -> Dict[str, Any]:
    """Async implementation of upload cleanup."""
    cutoff_date = datetime.utcnow() - timedelta(days=settings.file_retention_days or 30)
    files_deleted = 0
    records_deleted = 0
    errors = []

    async for db in get_async_db():
        try:
            # Find old uploads
            result = await db.execute(
                select(FileUpload).where(FileUpload.upload_timestamp < cutoff_date)
            )
            old_uploads = result.scalars().all()

            for upload in old_uploads:
                try:
                    # Delete file from disk
                    file_path = os.path.join(settings.upload_dir, upload.filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        files_deleted += 1

                    # Delete associated transactions
                    await db.execute(
                        delete(Transaction).where(Transaction.upload_id == upload.id)
                    )

                    # Delete upload record
                    await db.delete(upload)
                    records_deleted += 1

                except Exception as e:
                    errors.append(f"Failed to cleanup upload {upload.id}: {str(e)}")

            await db.commit()

            return {
                "files_deleted": files_deleted,
                "records_deleted": records_deleted,
                "errors": errors,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            return {
                "error": str(e),
                "files_deleted": files_deleted,
                "records_deleted": records_deleted,
            }


@celery_app.task
def get_file_processing_stats() -> Dict[str, Any]:
    """
    Get statistics about file processing operations.

    Returns:
        Processing statistics
    """
    return asyncio.run(_get_file_processing_stats_async())


async def _get_file_processing_stats_async() -> Dict[str, Any]:
    """Async implementation of stats collection."""
    async for db in get_async_db():
        try:
            # Get upload statistics
            all_uploads_result = await db.execute(select(FileUpload))
            all_uploads = all_uploads_result.scalars().all()

            # Count by status
            status_counts = {}
            total_size = 0
            processing_times = []

            for upload in all_uploads:
                status = upload.status
                status_counts[status] = status_counts.get(status, 0) + 1
                total_size += upload.file_size

                # Calculate processing time if available
                if upload.processed_at and upload.upload_timestamp:
                    processing_time = (
                        upload.processed_at - upload.upload_timestamp
                    ).total_seconds()
                    processing_times.append(processing_time)

            # Get transaction count
            transactions_result = await db.execute(select(Transaction))
            total_transactions = len(transactions_result.scalars().all())

            return {
                "total_uploads": len(all_uploads),
                "status_breakdown": status_counts,
                "total_file_size_bytes": total_size,
                "total_transactions_processed": total_transactions,
                "average_processing_time_seconds": (
                    sum(processing_times) / len(processing_times)
                    if processing_times
                    else 0
                ),
                "stats_generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "error": str(e),
                "stats_generated_at": datetime.utcnow().isoformat(),
            }
