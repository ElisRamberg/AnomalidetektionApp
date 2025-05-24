"""Transaction data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
import uuid
from datetime import datetime, date

from ..database import get_async_db
from ..config import get_settings
from ..models.transaction import Transaction
from ..models.upload import FileUpload
from ..schemas.transaction import (
    TransactionResponse, TransactionListResponse, TransactionStatsResponse,
    TransactionAnomalyResponse
)

router = APIRouter()
settings = get_settings()


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    upload_id: Optional[uuid.UUID] = Query(None, description="Filter by upload ID"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    amount_min: Optional[float] = Query(None, description="Minimum transaction amount"),
    amount_max: Optional[float] = Query(None, description="Maximum transaction amount"),
    date_from: Optional[date] = Query(None, description="Filter transactions from date"),
    date_to: Optional[date] = Query(None, description="Filter transactions to date"),
    search: Optional[str] = Query(None, description="Search in transaction data"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("timestamp", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get paginated list of transactions with filtering and search capabilities."""
    # Build query
    query = select(Transaction)
    
    # Apply filters
    if upload_id:
        query = query.where(Transaction.upload_id == upload_id)
    
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    
    if amount_min is not None:
        query = query.where(Transaction.amount >= amount_min)
    
    if amount_max is not None:
        query = query.where(Transaction.amount <= amount_max)
    
    if date_from:
        query = query.where(Transaction.timestamp >= date_from)
    
    if date_to:
        # Add one day to include transactions on the end date
        date_to_inclusive = datetime.combine(date_to, datetime.max.time())
        query = query.where(Transaction.timestamp <= date_to_inclusive)
    
    if search:
        # Search in external_transaction_id and raw_data
        search_filter = or_(
            Transaction.external_transaction_id.ilike(f"%{search}%"),
            Transaction.raw_data.astext.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
    
    # Count total records
    count_query = select(func.count()).select_from(
        query.subquery() if hasattr(query, 'whereclause') and query.whereclause is not None 
        else Transaction
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = getattr(Transaction, sort_by, Transaction.timestamp)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    transactions = result.scalars().all()
    
    return TransactionListResponse(
        transactions=[TransactionResponse.from_orm(t) for t in transactions],
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + per_page < total,
        has_prev=page > 1,
        filters_applied={
            "upload_id": upload_id,
            "account_id": account_id,
            "amount_range": [amount_min, amount_max] if amount_min or amount_max else None,
            "date_range": [date_from, date_to] if date_from or date_to else None,
            "search": search
        }
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionAnomalyResponse)
async def get_transaction_detail(
    transaction_id: uuid.UUID,
    include_anomaly_scores: bool = Query(True, description="Include anomaly scores"),
    include_rule_flags: bool = Query(True, description="Include rule flags"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get detailed transaction information including anomaly scores and flags."""
    # Get transaction
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # TODO: Fetch anomaly scores and rule flags
    # This will be implemented when anomaly_scores and rule_flags tables are integrated
    anomaly_scores = []
    rule_flags = []
    
    response_data = {
        "transaction": transaction,
        "anomaly_summary": {
            "max_score": 0.0,
            "algorithms_triggered": 0,
            "rules_triggered": 0,
            "risk_level": "low"  # TODO: Calculate based on actual scores
        }
    }
    
    if include_anomaly_scores:
        response_data["anomaly_scores"] = anomaly_scores
    
    if include_rule_flags:
        response_data["rule_flags"] = rule_flags
    
    return TransactionAnomalyResponse(**response_data)


@router.get("/transactions/anomalies", response_model=TransactionListResponse)
async def list_anomalous_transactions(
    upload_id: Optional[uuid.UUID] = Query(None, description="Filter by upload ID"),
    analysis_run_id: Optional[uuid.UUID] = Query(None, description="Filter by analysis run"),
    min_score: float = Query(0.7, description="Minimum anomaly score threshold"),
    algorithm_type: Optional[str] = Query(None, description="Filter by algorithm type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get transactions flagged as anomalies based on analysis results."""
    # TODO: This will be properly implemented when anomaly_scores table is integrated
    # For now, return empty list with proper structure
    
    return TransactionListResponse(
        transactions=[],
        total=0,
        page=page,
        per_page=per_page,
        has_next=False,
        has_prev=False,
        filters_applied={
            "upload_id": upload_id,
            "analysis_run_id": analysis_run_id,
            "min_score": min_score,
            "algorithm_type": algorithm_type
        }
    )


@router.get("/transactions/stats", response_model=TransactionStatsResponse)
async def get_transaction_stats(
    upload_id: Optional[uuid.UUID] = Query(None, description="Filter by upload ID"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    date_from: Optional[date] = Query(None, description="Stats from date"),
    date_to: Optional[date] = Query(None, description="Stats to date"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get transaction statistics with optional filtering."""
    # Build base query
    query = select(Transaction)
    
    # Apply filters
    if upload_id:
        query = query.where(Transaction.upload_id == upload_id)
    
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    
    if date_from:
        query = query.where(Transaction.timestamp >= date_from)
    
    if date_to:
        date_to_inclusive = datetime.combine(date_to, datetime.max.time())
        query = query.where(Transaction.timestamp <= date_to_inclusive)
    
    # Get all matching transactions
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    if not transactions:
        return TransactionStatsResponse(
            total_transactions=0,
            total_amount=0.0,
            average_amount=0.0,
            min_amount=0.0,
            max_amount=0.0,
            unique_accounts=0,
            date_range=None,
            anomalies_detected=0,
            anomaly_rate=0.0
        )
    
    # Calculate statistics
    amounts = [t.amount for t in transactions]
    account_ids = list(set(t.account_id for t in transactions))
    timestamps = [t.timestamp for t in transactions]
    
    stats = TransactionStatsResponse(
        total_transactions=len(transactions),
        total_amount=sum(amounts),
        average_amount=sum(amounts) / len(amounts),
        min_amount=min(amounts),
        max_amount=max(amounts),
        unique_accounts=len(account_ids),
        date_range={
            "from": min(timestamps).date(),
            "to": max(timestamps).date()
        },
        anomalies_detected=0,  # TODO: Calculate from anomaly_scores table
        anomaly_rate=0.0       # TODO: Calculate from anomaly_scores table
    )
    
    return stats


@router.get("/transactions/accounts", response_model=List[dict])
async def list_account_summaries(
    upload_id: Optional[uuid.UUID] = Query(None, description="Filter by upload ID"),
    min_transactions: int = Query(1, description="Minimum number of transactions"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get summary statistics for each account."""
    # Build query
    query = select(Transaction)
    
    if upload_id:
        query = query.where(Transaction.upload_id == upload_id)
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    # Group by account
    account_stats = {}
    for transaction in transactions:
        account_id = transaction.account_id
        if account_id not in account_stats:
            account_stats[account_id] = {
                "account_id": account_id,
                "transaction_count": 0,
                "total_amount": 0.0,
                "amounts": [],
                "timestamps": []
            }
        
        account_stats[account_id]["transaction_count"] += 1
        account_stats[account_id]["total_amount"] += transaction.amount
        account_stats[account_id]["amounts"].append(transaction.amount)
        account_stats[account_id]["timestamps"].append(transaction.timestamp)
    
    # Calculate summary statistics
    summaries = []
    for account_id, stats in account_stats.items():
        if stats["transaction_count"] >= min_transactions:
            amounts = stats["amounts"]
            timestamps = stats["timestamps"]
            
            summary = {
                "account_id": account_id,
                "transaction_count": stats["transaction_count"],
                "total_amount": stats["total_amount"],
                "average_amount": stats["total_amount"] / len(amounts),
                "min_amount": min(amounts),
                "max_amount": max(amounts),
                "first_transaction": min(timestamps),
                "last_transaction": max(timestamps),
                "anomalies_detected": 0  # TODO: Calculate from anomaly_scores
            }
            summaries.append(summary)
    
    # Sort by transaction count (descending)
    summaries.sort(key=lambda x: x["transaction_count"], reverse=True)
    
    return summaries 