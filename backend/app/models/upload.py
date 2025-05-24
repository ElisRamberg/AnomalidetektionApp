"""File upload database model."""

from sqlalchemy import Column, String, BigInteger, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from ..database import Base


class FileUpload(Base):
    """Model for tracking file uploads and their processing status."""
    
    __tablename__ = "file_uploads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)
    mime_type = Column(String(100), nullable=True)
    
    # Status tracking
    status = Column(String(50), nullable=False, default="uploaded")
    # Status options: uploaded, processing, processed, failed, deleted
    
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    
    # Metadata storage
    metadata = Column(JSONB, nullable=True)
    
    # Processing statistics
    rows_processed = Column(BigInteger, nullable=True)
    rows_valid = Column(BigInteger, nullable=True)
    rows_invalid = Column(BigInteger, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<FileUpload(id={self.id}, filename={self.filename}, status={self.status})>"
    
    @property
    def is_processed(self) -> bool:
        """Check if file has been successfully processed."""
        return self.status == "processed"
    
    @property
    def has_errors(self) -> bool:
        """Check if file processing has errors."""
        return self.status == "failed"
    
    @property
    def is_processing(self) -> bool:
        """Check if file is currently being processed."""
        return self.status == "processing" 