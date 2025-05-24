"""Health check endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio
from typing import Dict, Any
from datetime import datetime

from ..database import get_async_db
from ..config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "service": settings.app_name
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_async_db)) -> Dict[str, Any]:
    """Detailed health check including database and external services."""
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "service": settings.app_name,
        "checks": {}
    }
    
    # Database check
    try:
        result = await db.execute(text("SELECT 1"))
        health_data["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Redis check (for Celery)
    try:
        import redis
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        health_data["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_data["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
    
    # File system check
    try:
        import os
        os.makedirs(settings.upload_dir, exist_ok=True)
        health_data["checks"]["filesystem"] = {
            "status": "healthy",
            "message": f"Upload directory accessible: {settings.upload_dir}"
        }
    except Exception as e:
        health_data["checks"]["filesystem"] = {
            "status": "unhealthy",
            "message": f"Upload directory not accessible: {str(e)}"
        }
    
    return health_data


@router.get("/health/readiness")
async def readiness_check(db: AsyncSession = Depends(get_async_db)):
    """Kubernetes readiness probe endpoint."""
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"} 