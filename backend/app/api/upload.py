"""File upload endpoints."""

import os
import uuid
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_async_db
from ..models.upload import FileUpload
from ..schemas.upload import (
    FileUploadListResponse,
    FileUploadResponse,
    FileUploadStats,
    FileUploadStatus,
)
from ..services.file_processor import FileProcessorService
from ..utils.exceptions import FileProcessingError, UnsupportedFileTypeError
from ..utils.file_validators import FileValidator

router = APIRouter()
settings = get_settings()
file_processor = FileProcessorService()
file_validator = FileValidator()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    auto_analyze: bool = Form(False),
    strategy_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Upload a file for processing and analysis.

    Supports CSV, JSON, Excel, XML, and SIE4 file formats.
    """
    # Validate file
    try:
        file_content = await file.read()
        await file.seek(0)  # Reset file position

        # Basic file validation
        file_validator.validate_file_size(len(file_content))
        file_validator.validate_file_type(file.filename)

        # Get file type
        file_type = file_validator.get_file_type(file.filename)

        # Validate file structure
        validation_result = file_processor.validate_file(
            file_content, file.filename, file_type
        )

        if not validation_result.get("valid", False):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file structure: {validation_result.get('error', 'Unknown error')}",
            )

    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File validation failed: {str(e)}")

    # Generate unique filename
    file_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    stored_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(settings.upload_dir, stored_filename)

    try:
        # Create upload directory if it doesn't exist
        os.makedirs(settings.upload_dir, exist_ok=True)

        # Save file to disk
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        # Create database record
        upload_record = FileUpload(
            id=file_id,
            filename=stored_filename,
            original_filename=file.filename,
            file_size=len(file_content),
            file_type=file_type,
            mime_type=file.content_type,
            status="uploaded",
            metadata={
                "validation_result": validation_result,
                "auto_analyze": auto_analyze,
                "strategy_id": strategy_id,
            },
        )

        db.add(upload_record)
        await db.commit()
        await db.refresh(upload_record)

        # TODO: Trigger async processing if auto_analyze is True
        # This will be implemented when Celery tasks are added

        return FileUploadResponse.from_orm(upload_record)

    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/upload/{upload_id}/status", response_model=FileUploadStatus)
async def get_upload_status(
    upload_id: uuid.UUID, db: AsyncSession = Depends(get_async_db)
):
    """Get the status of a file upload."""
    result = await db.execute(select(FileUpload).where(FileUpload.id == upload_id))
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    return FileUploadStatus.from_orm(upload)


@router.get("/upload/history", response_model=FileUploadListResponse)
async def get_upload_history(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Get paginated list of file uploads."""
    if per_page > 100:
        per_page = 100

    # Build query
    query = select(FileUpload)

    if status:
        query = query.where(FileUpload.status == status)

    # Count total records
    count_result = await db.execute(
        select(FileUpload.id).where(
            query.whereclause if query.whereclause is not None else True
        )
    )
    total = len(count_result.all())

    # Get paginated results
    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(FileUpload.upload_timestamp.desc())
        .offset(offset)
        .limit(per_page)
    )
    uploads = result.scalars().all()

    return FileUploadListResponse(
        uploads=[FileUploadResponse.from_orm(upload) for upload in uploads],
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + per_page < total,
        has_prev=page > 1,
    )


@router.get("/upload/stats", response_model=FileUploadStats)
async def get_upload_stats(db: AsyncSession = Depends(get_async_db)):
    """Get upload statistics."""
    # Count uploads by status
    all_uploads = await db.execute(select(FileUpload))
    uploads = all_uploads.scalars().all()

    total_uploads = len(uploads)
    successful_uploads = len([u for u in uploads if u.status == "processed"])
    failed_uploads = len([u for u in uploads if u.status == "failed"])
    processing_uploads = len(
        [u for u in uploads if u.status in ["uploaded", "processing"]]
    )

    total_size_bytes = sum(u.file_size for u in uploads)

    # TODO: Calculate total_transactions_processed from transaction table
    # This will be implemented when transaction endpoints are added
    total_transactions_processed = 0

    return FileUploadStats(
        total_uploads=total_uploads,
        successful_uploads=successful_uploads,
        failed_uploads=failed_uploads,
        processing_uploads=processing_uploads,
        total_size_bytes=total_size_bytes,
        total_transactions_processed=total_transactions_processed,
    )


@router.delete("/upload/{upload_id}")
async def delete_upload(upload_id: uuid.UUID, db: AsyncSession = Depends(get_async_db)):
    """Delete an uploaded file."""
    result = await db.execute(select(FileUpload).where(FileUpload.id == upload_id))
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Delete file from disk
    file_path = os.path.join(settings.upload_dir, upload.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from database
    await db.delete(upload)
    await db.commit()

    return {"message": "Upload deleted successfully"}
