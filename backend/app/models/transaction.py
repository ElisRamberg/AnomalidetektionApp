"""Transaction database model."""

from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..database import Base


class Transaction(Base):
    """Model for storing transaction data (both raw and processed)."""
    
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID(as_uuid=True), ForeignKey("file_uploads.id"), nullable=False)
    
    # Transaction identifiers
    external_transaction_id = Column(String(255), nullable=True)
    
    # Core transaction data
    amount = Column(Numeric(15, 2), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    account_id = Column(String(255), nullable=False)
    
    # Optional transaction fields
    description = Column(String(1000), nullable=True)
    category = Column(String(100), nullable=True)
    reference = Column(String(255), nullable=True)
    
    # Data storage
    raw_data = Column(JSONB, nullable=False)  # Original data as uploaded
    processed_data = Column(JSONB, nullable=True)  # Cleaned and enriched data
    
    # Enriched fields (computed during processing)
    day_of_week = Column(String(10), nullable=True)
    hour_of_day = Column(String(5), nullable=True)
    is_weekend = Column(String(5), nullable=True)  # Store as string for JSON compatibility
    month = Column(String(10), nullable=True)
    quarter = Column(String(5), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to upload
    upload = relationship("FileUpload", back_populates="transactions")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_transactions_upload_id", "upload_id"),
        Index("idx_transactions_timestamp", "timestamp"),
        Index("idx_transactions_account_id", "account_id"),
        Index("idx_transactions_external_id", "external_transaction_id"),
        Index("idx_transactions_amount", "amount"),
        Index("idx_transactions_day_of_week", "day_of_week"),
        Index("idx_transactions_is_weekend", "is_weekend"),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, account_id={self.account_id}, amount={self.amount})>"
    
    @property
    def is_large_amount(self) -> bool:
        """Check if this is a large transaction (can be configured)."""
        # This is a simple threshold - in practice this would be configurable
        return self.amount > 10000
    
    @property
    def is_weekend_transaction(self) -> bool:
        """Check if transaction occurred on weekend."""
        return self.is_weekend == "true"
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary for API responses."""
        return {
            "id": str(self.id),
            "upload_id": str(self.upload_id),
            "external_transaction_id": self.external_transaction_id,
            "amount": float(self.amount) if self.amount else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "account_id": self.account_id,
            "description": self.description,
            "category": self.category,
            "reference": self.reference,
            "day_of_week": self.day_of_week,
            "hour_of_day": self.hour_of_day,
            "is_weekend": self.is_weekend == "true",
            "month": self.month,
            "quarter": self.quarter,
            "raw_data": self.raw_data,
            "processed_data": self.processed_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Add the back reference to FileUpload
from .upload import FileUpload
FileUpload.transactions = relationship("Transaction", back_populates="upload") 