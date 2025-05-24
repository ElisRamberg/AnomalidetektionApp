"""Strategy management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
from datetime import datetime

from ..database import get_async_db
from ..config import get_settings
from ..models.strategy import Strategy
from ..schemas.strategy import (
    StrategyCreateRequest, StrategyUpdateRequest, StrategyResponse,
    StrategyListResponse, StrategyPreviewResponse
)
from ..algorithms import AlgorithmRegistry
from ..utils.exceptions import StrategyConfigurationError

router = APIRouter()
settings = get_settings()
algorithm_registry = AlgorithmRegistry()


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get paginated list of strategies with optional filtering."""
    # Build query
    query = select(Strategy)
    
    if is_active is not None:
        query = query.where(Strategy.is_active == is_active)
    
    if created_by:
        query = query.where(Strategy.created_by == created_by)
    
    # Count total records
    count_result = await db.execute(
        select(Strategy.id).where(query.whereclause if query.whereclause is not None else True)
    )
    total = len(count_result.all())
    
    # Get paginated results
    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Strategy.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    strategies = result.scalars().all()
    
    return StrategyListResponse(
        strategies=[StrategyResponse.from_orm(strategy) for strategy in strategies],
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + per_page < total,
        has_prev=page > 1
    )


@router.post("/strategies", response_model=StrategyResponse)
async def create_strategy(
    request: StrategyCreateRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new detection strategy."""
    # Validate strategy configuration
    try:
        _validate_strategy_configuration(request.configuration)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid strategy configuration: {str(e)}")
    
    # Create strategy record
    strategy = Strategy(
        id=uuid.uuid4(),
        name=request.name,
        description=request.description,
        configuration=request.configuration,
        is_active=request.is_active,
        created_by=request.created_by or "system"
    )
    
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    
    return StrategyResponse.from_orm(strategy)


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific strategy by ID."""
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return StrategyResponse.from_orm(strategy)


@router.put("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: uuid.UUID,
    request: StrategyUpdateRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Update an existing strategy."""
    # Get existing strategy
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Update fields if provided
    if request.name is not None:
        strategy.name = request.name
    
    if request.description is not None:
        strategy.description = request.description
    
    if request.configuration is not None:
        # Validate new configuration
        try:
            _validate_strategy_configuration(request.configuration)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid strategy configuration: {str(e)}")
        strategy.configuration = request.configuration
    
    if request.is_active is not None:
        strategy.is_active = request.is_active
    
    strategy.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(strategy)
    
    return StrategyResponse.from_orm(strategy)


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a strategy."""
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # TODO: Check if strategy is being used in active analysis runs
    # For now, we'll allow deletion but this should be prevented in production
    
    await db.delete(strategy)
    await db.commit()
    
    return {"message": "Strategy deleted successfully"}


@router.get("/strategies/{strategy_id}/preview", response_model=StrategyPreviewResponse)
async def preview_strategy(
    strategy_id: uuid.UUID,
    sample_size: int = Query(100, ge=10, le=1000, description="Number of sample transactions"),
    db: AsyncSession = Depends(get_async_db)
):
    """Preview strategy impact using sample data."""
    # Get strategy
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # TODO: Implement actual preview logic
    # This would involve:
    # 1. Getting sample transactions from the database
    # 2. Running the strategy algorithms on the sample
    # 3. Calculating expected results and performance metrics
    
    preview_data = {
        "strategy": strategy,
        "sample_stats": {
            "transactions_analyzed": 0,
            "estimated_anomalies": 0,
            "estimated_processing_time": 0.0,
            "algorithms_to_run": []
        },
        "algorithm_impacts": [],
        "estimated_performance": {
            "precision": None,
            "recall": None,
            "f1_score": None
        }
    }
    
    return StrategyPreviewResponse(**preview_data)


@router.get("/strategies/presets", response_model=List[dict])
async def get_strategy_presets():
    """Get predefined strategy templates."""
    presets = [
        {
            "name": "Basic Statistical Detection",
            "description": "Simple Z-score based anomaly detection with standard thresholds",
            "configuration": {
                "algorithms": [
                    {
                        "type": "statistical",
                        "name": "zscore",
                        "enabled": True,
                        "config": {
                            "threshold": 3.0,
                            "window_size": 30
                        }
                    }
                ],
                "global_settings": {
                    "aggregation_method": "max",
                    "confidence_threshold": 0.7
                }
            }
        },
        {
            "name": "Comprehensive Multi-Algorithm",
            "description": "Uses multiple algorithms for robust anomaly detection",
            "configuration": {
                "algorithms": [
                    {
                        "type": "statistical",
                        "name": "zscore",
                        "enabled": True,
                        "config": {
                            "threshold": 2.5,
                            "window_size": 50
                        }
                    },
                    {
                        "type": "rule_based",
                        "name": "weekend_threshold",
                        "enabled": True,
                        "config": {
                            "weekday_multiplier": 1.0,
                            "weekend_multiplier": 0.3
                        }
                    },
                    {
                        "type": "ml_based",
                        "name": "isolation_forest",
                        "enabled": True,
                        "config": {
                            "contamination": 0.1,
                            "n_estimators": 100
                        }
                    }
                ],
                "global_settings": {
                    "aggregation_method": "weighted_average",
                    "confidence_threshold": 0.6,
                    "weights": {
                        "statistical": 0.4,
                        "rule_based": 0.3,
                        "ml_based": 0.3
                    }
                }
            }
        },
        {
            "name": "Rule-Based Only",
            "description": "Uses only domain-specific business rules for detection",
            "configuration": {
                "algorithms": [
                    {
                        "type": "rule_based",
                        "name": "weekend_threshold",
                        "enabled": True,
                        "config": {
                            "weekday_multiplier": 1.0,
                            "weekend_multiplier": 0.2
                        }
                    },
                    {
                        "type": "rule_based",
                        "name": "periodization",
                        "enabled": True,
                        "config": {
                            "period_type": "monthly",
                            "threshold_multiplier": 2.0
                        }
                    }
                ],
                "global_settings": {
                    "aggregation_method": "max",
                    "confidence_threshold": 0.8
                }
            }
        }
    ]
    
    return presets


@router.get("/strategies/algorithms", response_model=dict)
async def get_available_algorithms():
    """Get list of available algorithms for strategy configuration."""
    return algorithm_registry.list_algorithms()


def _validate_strategy_configuration(configuration: dict) -> None:
    """
    Validate strategy configuration structure and algorithm parameters.
    
    Args:
        configuration: Strategy configuration to validate
        
    Raises:
        StrategyConfigurationError: If configuration is invalid
    """
    if not isinstance(configuration, dict):
        raise StrategyConfigurationError("Configuration must be a dictionary")
    
    # Check required top-level keys
    if "algorithms" not in configuration:
        raise StrategyConfigurationError("Configuration must include 'algorithms' section")
    
    algorithms = configuration["algorithms"]
    if not isinstance(algorithms, list) or len(algorithms) == 0:
        raise StrategyConfigurationError("Algorithms must be a non-empty list")
    
    # Validate each algorithm configuration
    for i, algo_config in enumerate(algorithms):
        if not isinstance(algo_config, dict):
            raise StrategyConfigurationError(f"Algorithm {i} configuration must be a dictionary")
        
        # Check required algorithm fields
        required_fields = ["type", "name", "enabled"]
        for field in required_fields:
            if field not in algo_config:
                raise StrategyConfigurationError(f"Algorithm {i} missing required field: {field}")
        
        algo_type = algo_config["type"]
        algo_name = algo_config["name"]
        
        # Validate algorithm exists in registry
        try:
            algorithm = algorithm_registry.get_algorithm(algo_type, algo_name)
            
            # Validate algorithm-specific configuration
            if "config" in algo_config:
                algorithm.validate_config(algo_config["config"])
                
        except Exception as e:
            raise StrategyConfigurationError(
                f"Algorithm {i} ({algo_type}.{algo_name}) validation failed: {str(e)}"
            )
    
    # Validate global settings if present
    if "global_settings" in configuration:
        global_settings = configuration["global_settings"]
        if not isinstance(global_settings, dict):
            raise StrategyConfigurationError("Global settings must be a dictionary")
        
        # Validate aggregation method
        if "aggregation_method" in global_settings:
            valid_methods = ["max", "min", "mean", "weighted_average"]
            if global_settings["aggregation_method"] not in valid_methods:
                raise StrategyConfigurationError(
                    f"Invalid aggregation method. Must be one of: {valid_methods}"
                ) 