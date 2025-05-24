"""Upload-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID


class FileUploadRequest(BaseModel):
    """Schema for file upload requests."""
    # This will be used for multipart file uploads
    # The actual file will be handled separately as UploadFile
    auto_analyze: bool = Field(default=False, description="Whether to automatically start analysis after upload")
    strategy_id: Optional[UUID] = Field(default=None, description="Strategy to use for auto-analysis")


class FileUploadResponse(BaseModel):
    """Schema for file upload responses."""
    id: UUID
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    mime_type: Optional[str] = None
    status: str
    upload_timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class FileUploadStatus(BaseModel):
    """Schema for file upload status responses."""
    id: UUID
    filename: str
    status: str
    upload_timestamp: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    rows_processed: Optional[int] = None
    rows_valid: Optional[int] = None
    rows_invalid: Optional[int] = None
    
    class Config:
        from_attributes = True


class FileUploadListResponse(BaseModel):
    """Schema for paginated file upload list responses."""
    uploads: list[FileUploadResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class FileUploadStats(BaseModel):
    """Schema for upload statistics."""
    total_uploads: int
    successful_uploads: int
    failed_uploads: int
    processing_uploads: int
    total_size_bytes: int
    total_transactions_processed: int 