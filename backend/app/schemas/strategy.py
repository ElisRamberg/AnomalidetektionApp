"""Strategy-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from uuid import UUID


class StrategyBase(BaseModel):
    """Base schema for strategy data."""
    name: str = Field(..., min_length=1, max_length=255, description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    configuration: Dict[str, Any] = Field(..., description="Strategy configuration")


class StrategyCreate(StrategyBase):
    """Schema for creating strategies."""
    is_active: bool = Field(default=True, description="Whether strategy is active")
    created_by: Optional[str] = Field(None, description="User who created the strategy")


class StrategyUpdate(BaseModel):
    """Schema for updating strategies."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class StrategyResponse(StrategyBase):
    """Schema for strategy responses."""
    id: UUID
    is_active: bool
    is_preset: bool
    enabled_algorithms: List[str]
    algorithm_count: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    """Schema for strategy list responses."""
    strategies: List[StrategyResponse]
    total: int


class StrategyPreview(BaseModel):
    """Schema for strategy preview responses."""
    strategy_id: UUID
    estimated_impact: Dict[str, Any]
    algorithm_summary: Dict[str, Any]
    sample_results: List[Dict[str, Any]]
    estimated_processing_time: float


class AlgorithmConfig(BaseModel):
    """Schema for algorithm configuration within strategies."""
    enabled: bool = Field(..., description="Whether algorithm is enabled")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Algorithm parameters")
    
    @validator('parameters')
    def validate_parameters(cls, v):
        # Basic validation - specific algorithms will have their own validation
        if not isinstance(v, dict):
            raise ValueError('parameters must be a dictionary')
        return v


class StatisticalAlgorithmsConfig(BaseModel):
    """Schema for statistical algorithms configuration."""
    zscore: Optional[AlgorithmConfig] = None
    correlation: Optional[AlgorithmConfig] = None
    timeseries: Optional[AlgorithmConfig] = None


class RuleBasedAlgorithmsConfig(BaseModel):
    """Schema for rule-based algorithms configuration."""
    weekend_threshold: Optional[AlgorithmConfig] = None
    periodization: Optional[AlgorithmConfig] = None


class MLBasedAlgorithmsConfig(BaseModel):
    """Schema for ML-based algorithms configuration."""
    isolation_forest: Optional[AlgorithmConfig] = None
    autoencoder: Optional[AlgorithmConfig] = None
    clustering: Optional[AlgorithmConfig] = None


class FullStrategyConfiguration(BaseModel):
    """Schema for complete strategy configuration."""
    statistical: Optional[StatisticalAlgorithmsConfig] = None
    rule_based: Optional[RuleBasedAlgorithmsConfig] = None
    ml_based: Optional[MLBasedAlgorithmsConfig] = None
    
    @validator('*')
    def at_least_one_algorithm(cls, v, values):
        # Check that at least one algorithm type is configured
        if all(config is None for config in values.values()):
            raise ValueError('At least one algorithm type must be configured')
        return v


class StrategyValidationResponse(BaseModel):
    """Schema for strategy validation responses."""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    algorithm_count: int
    estimated_performance: Optional[Dict[str, Any]] = None 