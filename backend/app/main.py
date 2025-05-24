"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .database import init_db, close_db
from .api import health


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    print("Database initialized")
    
    yield
    
    # Shutdown
    await close_db()
    print("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for anomaly detection system with ETL capabilities",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(
    health.router,
    prefix=settings.api_v1_prefix,
    tags=["health"]
)

# TODO: Add other routers as they are implemented
# app.include_router(upload.router, prefix=settings.api_v1_prefix, tags=["upload"])
# app.include_router(analysis.router, prefix=settings.api_v1_prefix, tags=["analysis"])
# app.include_router(transactions.router, prefix=settings.api_v1_prefix, tags=["transactions"])
# app.include_router(strategies.router, prefix=settings.api_v1_prefix, tags=["strategies"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Anomaly Detection API",
        "version": settings.app_version,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    ) 