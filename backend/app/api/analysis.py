"""Analysis management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import uuid
from datetime import datetime

from ..database import get_async_db
from ..config import get_settings
from ..models.analysis import AnalysisRun
from ..models.upload import FileUpload
from ..models.strategy import Strategy
from ..schemas.analysis import (
    AnalysisRunRequest, AnalysisRunResponse, AnalysisRunStatus,
    AnalysisRunListResponse, AnalysisResultsResponse
)
from ..utils.exceptions import AnalysisError

router = APIRouter()
settings = get_settings()


@router.post("/analysis/run", response_model=AnalysisRunResponse)
async def start_analysis_run(
    request: AnalysisRunRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Start a new analysis run for uploaded data.
    
    This endpoint triggers anomaly detection algorithms based on the specified strategy.
    """
    # Validate that upload exists
    upload_result = await db.execute(
        select(FileUpload).where(FileUpload.id == request.upload_id)
    )
    upload = upload_result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    if upload.status != "processed":
        raise HTTPException(
            status_code=400, 
            detail=f"Upload must be processed before analysis. Current status: {upload.status}"
        )
    
    # Validate that strategy exists if provided
    strategy = None
    if request.strategy_id:
        strategy_result = await db.execute(
            select(Strategy).where(Strategy.id == request.strategy_id)
        )
        strategy = strategy_result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        if not strategy.is_active:
            raise HTTPException(status_code=400, detail="Strategy is not active")
    
    # Create analysis run record
    analysis_run = AnalysisRun(
        id=uuid.uuid4(),
        upload_id=request.upload_id,
        strategy_id=request.strategy_id,
        status="pending",
        metadata={
            "request_parameters": request.dict(),
            "created_by": getattr(request, 'created_by', 'system')
        }
    )
    
    db.add(analysis_run)
    await db.commit()
    await db.refresh(analysis_run)
    
    # TODO: Trigger async analysis processing with Celery
    # This will be implemented when Celery tasks are added
    # celery_task = run_anomaly_detection.delay(str(analysis_run.id))
    # analysis_run.metadata['celery_task_id'] = celery_task.id
    # await db.commit()
    
    return AnalysisRunResponse.from_orm(analysis_run)


@router.get("/analysis/{run_id}/status", response_model=AnalysisRunStatus)
async def get_analysis_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Get the status of an analysis run."""
    result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    analysis_run = result.scalar_one_or_none()
    
    if not analysis_run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    
    return AnalysisRunStatus.from_orm(analysis_run)


@router.get("/analysis/{run_id}/results", response_model=AnalysisResultsResponse)
async def get_analysis_results(
    run_id: uuid.UUID,
    include_scores: bool = Query(True, description="Include individual anomaly scores"),
    include_flags: bool = Query(True, description="Include rule flags"),
    threshold: Optional[float] = Query(None, description="Filter scores above threshold"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get complete analysis results."""
    # Get analysis run
    result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    analysis_run = result.scalar_one_or_none()
    
    if not analysis_run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    
    if analysis_run.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Analysis not completed. Current status: {analysis_run.status}"
        )
    
    # TODO: Fetch anomaly scores and rule flags from database
    # This will be implemented when the anomaly_scores and rule_flags tables are populated
    anomaly_scores = []
    rule_flags = []
    
    # Build response
    response_data = {
        "analysis_run": analysis_run,
        "summary": {
            "total_transactions": 0,  # TODO: Calculate from actual data
            "anomalies_detected": 0,  # TODO: Calculate from actual data
            "algorithms_used": [],    # TODO: Get from actual results
            "execution_time_seconds": None
        }
    }
    
    if include_scores:
        response_data["anomaly_scores"] = anomaly_scores
    
    if include_flags:
        response_data["rule_flags"] = rule_flags
    
    return AnalysisResultsResponse(**response_data)


@router.get("/analysis/runs", response_model=AnalysisRunListResponse)
async def list_analysis_runs(
    upload_id: Optional[uuid.UUID] = Query(None, description="Filter by upload ID"),
    strategy_id: Optional[uuid.UUID] = Query(None, description="Filter by strategy ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get paginated list of analysis runs with optional filtering."""
    # Build query
    query = select(AnalysisRun)
    
    if upload_id:
        query = query.where(AnalysisRun.upload_id == upload_id)
    
    if strategy_id:
        query = query.where(AnalysisRun.strategy_id == strategy_id)
    
    if status:
        query = query.where(AnalysisRun.status == status)
    
    # Count total records
    count_result = await db.execute(
        select(AnalysisRun.id).where(query.whereclause if query.whereclause is not None else True)
    )
    total = len(count_result.all())
    
    # Get paginated results
    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(AnalysisRun.started_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    analysis_runs = result.scalars().all()
    
    return AnalysisRunListResponse(
        runs=[AnalysisRunResponse.from_orm(run) for run in analysis_runs],
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + per_page < total,
        has_prev=page > 1
    )


@router.post("/analysis/{run_id}/cancel")
async def cancel_analysis_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Cancel a running analysis."""
    result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    analysis_run = result.scalar_one_or_none()
    
    if not analysis_run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    
    if analysis_run.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel analysis with status: {analysis_run.status}"
        )
    
    # TODO: Cancel Celery task if running
    # if analysis_run.metadata.get('celery_task_id'):
    #     celery_app.control.revoke(analysis_run.metadata['celery_task_id'], terminate=True)
    
    # Update status
    analysis_run.status = "cancelled"
    analysis_run.completed_at = datetime.utcnow()
    analysis_run.error_message = "Analysis cancelled by user"
    
    await db.commit()
    
    return {"message": "Analysis run cancelled successfully"}


@router.delete("/analysis/{run_id}")
async def delete_analysis_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete an analysis run and all associated results."""
    result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    analysis_run = result.scalar_one_or_none()
    
    if not analysis_run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    
    # TODO: Delete associated anomaly scores and rule flags
    # This will be implemented when those models are properly integrated
    
    # Delete analysis run
    await db.delete(analysis_run)
    await db.commit()
    
    return {"message": "Analysis run deleted successfully"} 