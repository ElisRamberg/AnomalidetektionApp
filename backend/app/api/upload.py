"""File upload endpoints - Simplified working version."""

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

router = APIRouter()
settings = get_settings()


# Simplified file validation
def validate_file_basic(file: UploadFile) -> tuple[str, str]:
    """Basic file validation - returns file_type and error message if any."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Check file size (basic check on filename, full check after read)
    if file.size and file.size > settings.max_file_size:
        max_mb = settings.max_file_size / (1024 * 1024)
        raise HTTPException(
            status_code=400, detail=f"File too large. Maximum size: {max_mb:.1f}MB"
        )

    # Get file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    extension_to_type = {
        ".csv": "csv",
        ".json": "json",
        ".xlsx": "xlsx",
        ".xls": "xls",
        ".xml": "xml",
    }

    if file_extension not in extension_to_type:
        allowed_types = ", ".join(extension_to_type.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {allowed_types}",
        )

    return extension_to_type[file_extension], ""


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    auto_analyze: bool = Form(False),
    strategy_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Upload a file for processing and analysis.

    Currently supports CSV, JSON, Excel, and XML files.
    """
    # Basic validation
    file_type, error = validate_file_basic(file)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Read file content
    try:
        file_content = await file.read()
        await file.seek(0)  # Reset file position

        # Validate file size after reading
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        if len(file_content) > settings.max_file_size:
            max_mb = settings.max_file_size / (1024 * 1024)
            current_mb = len(file_content) / (1024 * 1024)
            msg = f"File size ({current_mb:.1f}MB) exceeds " f"limit ({max_mb:.1f}MB)"
            raise HTTPException(status_code=400, detail=msg)

    except Exception as e:
        msg = f"Failed to read file: {str(e)}"
        raise HTTPException(status_code=500, detail=msg)

    # Generate unique filename and path
    file_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    stored_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(settings.upload_dir, stored_filename)

    # Create upload directory if needed
    try:
        os.makedirs(settings.upload_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create upload directory: {str(e)}"
        )

    # Save file and create database record in transaction
    try:
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
            file_metadata={
                "auto_analyze": auto_analyze,
                "strategy_id": strategy_id,
                "upload_method": "api",
            },
        )

        db.add(upload_record)
        await db.commit()
        await db.refresh(upload_record)

        # For now, just mark as uploaded. Processing will be added in next layer
        return FileUploadResponse.from_orm(upload_record)

    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            try:
            os.remove(file_path)
            except OSError:
                pass  # Don't fail on cleanup failure

        # Rollback database transaction
        await db.rollback()
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

    # Count total records - simplified approach
    count_result = await db.execute(query)
    all_uploads = count_result.scalars().all()
    total = len(all_uploads)

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
    # Get all uploads - simplified for now
    all_uploads_result = await db.execute(select(FileUpload))
    uploads = all_uploads_result.scalars().all()

    total_uploads = len(uploads)
    successful_uploads = len([u for u in uploads if u.status == "processed"])
    failed_uploads = len([u for u in uploads if u.status == "failed"])
    processing_uploads = len(
        [u for u in uploads if u.status in ["uploaded", "processing"]]
    )
    total_size_bytes = sum(u.file_size for u in uploads)

    return FileUploadStats(
        total_uploads=total_uploads,
        successful_uploads=successful_uploads,
        failed_uploads=failed_uploads,
        processing_uploads=processing_uploads,
        total_size_bytes=total_size_bytes,
        total_transactions_processed=0,  # Will implement in processing layer
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
        try:
        os.remove(file_path)
        except Exception:
            pass  # Continue even if file deletion fails

    # Delete from database
    await db.delete(upload)
    await db.commit()

    return {"message": "Upload deleted successfully"}
