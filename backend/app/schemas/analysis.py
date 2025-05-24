"""Analysis-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import UUID


class AnalysisRunCreate(BaseModel):
    """Schema for creating analysis runs."""
    upload_id: UUID = Field(..., description="ID of the uploaded file to analyze")
    strategy_id: UUID = Field(..., description="ID of the strategy to use")


class AnalysisRunResponse(BaseModel):
    """Schema for analysis run responses."""
    id: UUID
    upload_id: UUID
    strategy_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    total_transactions: Optional[int] = None
    processed_transactions: int
    progress_percentage: float
    duration_seconds: float
    
    class Config:
        from_attributes = True


class AnalysisRunListResponse(BaseModel):
    """Schema for paginated analysis run list responses."""
    analysis_runs: List[AnalysisRunResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class AnomalyScoreResponse(BaseModel):
    """Schema for anomaly score responses."""
    id: UUID
    transaction_id: UUID
    analysis_run_id: UUID
    algorithm_type: str
    algorithm_name: str
    full_algorithm_name: str
    score: float
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class RuleFlagResponse(BaseModel):
    """Schema for rule flag responses."""
    id: UUID
    transaction_id: UUID
    analysis_run_id: UUID
    rule_name: str
    triggered: bool
    flag_value: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnalysisResultsResponse(BaseModel):
    """Schema for complete analysis results."""
    analysis_run: AnalysisRunResponse
    anomaly_scores: List[AnomalyScoreResponse]
    rule_flags: List[RuleFlagResponse]
    summary: Dict[str, Any]


class AnalysisResultsSummary(BaseModel):
    """Schema for analysis results summary."""
    analysis_run_id: UUID
    total_transactions: int
    anomalous_transactions: int
    anomaly_percentage: float
    algorithm_results: Dict[str, Dict[str, Any]]
    rule_results: Dict[str, Dict[str, Any]]
    top_anomalies: List[Dict[str, Any]]
    distribution_stats: Dict[str, Any]


class AnalysisFilter(BaseModel):
    """Schema for filtering analysis results."""
    upload_id: Optional[UUID] = None
    strategy_id: Optional[UUID] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Pagination
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=1000)
    
    # Sorting
    sort_by: str = Field(default="started_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order: asc or desc")


class AnalysisProgress(BaseModel):
    """Schema for analysis progress updates."""
    analysis_run_id: UUID
    status: str
    progress_percentage: float
    current_step: str
    estimated_completion: Optional[datetime] = None
    messages: List[str] = []


class AlgorithmResult(BaseModel):
    """Schema for individual algorithm results."""
    algorithm_type: str
    algorithm_name: str
    transactions_analyzed: int
    anomalies_found: int
    average_score: float
    max_score: float
    execution_time_seconds: float
    parameters_used: Dict[str, Any]


class AnalysisPerformanceMetrics(BaseModel):
    """Schema for analysis performance metrics."""
    analysis_run_id: UUID
    total_execution_time: float
    algorithm_execution_times: Dict[str, float]
    memory_usage_peak: Optional[float] = None
    transactions_per_second: float
    algorithms_executed: List[AlgorithmResult] 