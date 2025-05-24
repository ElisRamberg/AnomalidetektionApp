"""Transaction-related Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from uuid import UUID


class TransactionBase(BaseModel):
    """Base schema for transaction data."""
    external_transaction_id: Optional[str] = None
    amount: Decimal = Field(..., description="Transaction amount")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    account_id: str = Field(..., description="Account identifier")
    description: Optional[str] = None
    category: Optional[str] = None
    reference: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Schema for creating transactions."""
    raw_data: Dict[str, Any] = Field(..., description="Original raw data from file")


class TransactionResponse(TransactionBase):
    """Schema for transaction responses."""
    id: UUID
    upload_id: UUID
    day_of_week: Optional[str] = None
    hour_of_day: Optional[str] = None
    is_weekend: Optional[bool] = None
    month: Optional[str] = None
    quarter: Optional[str] = None
    raw_data: Dict[str, Any]
    processed_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    # Anomaly information (if available)
    anomaly_scores: Optional[List[Dict[str, Any]]] = None
    rule_flags: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        from_attributes = True


class TransactionFilter(BaseModel):
    """Schema for filtering transactions."""
    upload_id: Optional[UUID] = None
    account_id: Optional[str] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    category: Optional[str] = None
    is_weekend: Optional[bool] = None
    day_of_week: Optional[str] = None
    has_anomalies: Optional[bool] = None
    
    # Pagination
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=1000)
    
    # Sorting
    sort_by: Optional[str] = Field(default="timestamp", description="Field to sort by")
    sort_order: Optional[str] = Field(default="desc", description="Sort order: asc or desc")
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v


class TransactionListResponse(BaseModel):
    """Schema for paginated transaction list responses."""
    transactions: List[TransactionResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
    filters_applied: Dict[str, Any]


class TransactionStats(BaseModel):
    """Schema for transaction statistics."""
    total_transactions: int
    total_amount: Decimal
    average_amount: Decimal
    min_amount: Decimal
    max_amount: Decimal
    unique_accounts: int
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    transactions_by_day: Dict[str, int]
    transactions_by_category: Dict[str, int]


class TransactionAnomalyResponse(TransactionResponse):
    """Schema for transactions with anomaly information."""
    max_anomaly_score: Optional[float] = None
    anomaly_algorithms_triggered: List[str] = []
    rule_flags_triggered: List[str] = []
    anomaly_summary: Optional[Dict[str, Any]] = None 