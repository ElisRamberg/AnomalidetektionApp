"""Analysis database models."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Boolean, Text, Index, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..database import Base


class AnalysisRun(Base):
    """Model for tracking analysis runs and their status."""
    
    __tablename__ = "analysis_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID(as_uuid=True), ForeignKey("file_uploads.id"), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False)
    
    # Status tracking
    status = Column(String(50), nullable=False, default="pending")
    # Status options: pending, running, completed, failed, cancelled
    
    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    
    # Results metadata
    metadata = Column(JSONB, nullable=True)
    
    # Progress tracking
    total_transactions = Column(BigInteger, nullable=True)
    processed_transactions = Column(BigInteger, default=0)
    
    # Relationships
    upload = relationship("FileUpload")
    strategy = relationship("Strategy")
    anomaly_scores = relationship("AnomalyScore", back_populates="analysis_run")
    rule_flags = relationship("RuleFlag", back_populates="analysis_run")
    
    # Indexes
    __table_args__ = (
        Index("idx_analysis_runs_upload_id", "upload_id"),
        Index("idx_analysis_runs_strategy_id", "strategy_id"),
        Index("idx_analysis_runs_status", "status"),
        Index("idx_analysis_runs_started_at", "started_at"),
    )
    
    def __repr__(self):
        return f"<AnalysisRun(id={self.id}, status={self.status}, strategy_id={self.strategy_id})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if analysis run is completed."""
        return self.status == "completed"
    
    @property
    def is_running(self) -> bool:
        """Check if analysis run is currently running."""
        return self.status == "running"
    
    @property
    def has_errors(self) -> bool:
        """Check if analysis run has errors."""
        return self.status == "failed"
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if not self.total_transactions or self.total_transactions == 0:
            return 0.0
        
        return min(100.0, (self.processed_transactions / self.total_transactions) * 100)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if not self.started_at:
            return 0.0
        
        end_time = self.completed_at or func.now()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> dict:
        """Convert analysis run to dictionary for API responses."""
        return {
            "id": str(self.id),
            "upload_id": str(self.upload_id),
            "strategy_id": str(self.strategy_id),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "metadata": self.metadata,
            "total_transactions": self.total_transactions,
            "processed_transactions": self.processed_transactions,
            "progress_percentage": self.progress_percentage,
            "duration_seconds": self.duration_seconds,
        }


class AnomalyScore(Base):
    """Model for storing anomaly scores from detection algorithms."""
    
    __tablename__ = "anomaly_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    
    # Algorithm information
    algorithm_type = Column(String(100), nullable=False)  # statistical, rule_based, ml_based
    algorithm_name = Column(String(100), nullable=False)  # zscore, isolation_forest, etc.
    
    # Score information
    score = Column(Numeric(10, 6), nullable=False)  # The anomaly score
    confidence = Column(Numeric(5, 4), nullable=True)  # Confidence in the score (0-1)
    
    # Additional metadata
    metadata = Column(JSONB, nullable=True)  # Algorithm-specific data
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    transaction = relationship("Transaction")
    analysis_run = relationship("AnalysisRun", back_populates="anomaly_scores")
    
    # Indexes
    __table_args__ = (
        Index("idx_anomaly_scores_transaction_analysis", "transaction_id", "analysis_run_id"),
        Index("idx_anomaly_scores_algorithm", "algorithm_type", "algorithm_name"),
        Index("idx_anomaly_scores_score", "score"),
        Index("idx_anomaly_scores_analysis_run", "analysis_run_id"),
    )
    
    def __repr__(self):
        return f"<AnomalyScore(id={self.id}, algorithm={self.algorithm_type}.{self.algorithm_name}, score={self.score})>"
    
    @property
    def full_algorithm_name(self) -> str:
        """Get full algorithm name."""
        return f"{self.algorithm_type}.{self.algorithm_name}"
    
    def to_dict(self) -> dict:
        """Convert anomaly score to dictionary for API responses."""
        return {
            "id": str(self.id),
            "transaction_id": str(self.transaction_id),
            "analysis_run_id": str(self.analysis_run_id),
            "algorithm_type": self.algorithm_type,
            "algorithm_name": self.algorithm_name,
            "full_algorithm_name": self.full_algorithm_name,
            "score": float(self.score) if self.score else None,
            "confidence": float(self.confidence) if self.confidence else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RuleFlag(Base):
    """Model for storing rule-based flags and their values."""
    
    __tablename__ = "rule_flags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)
    
    # Rule information
    rule_name = Column(String(100), nullable=False)
    triggered = Column(Boolean, nullable=False)
    
    # Rule-specific data
    flag_value = Column(Text, nullable=True)  # Additional information about the flag
    metadata = Column(JSONB, nullable=True)  # Rule-specific metadata
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    transaction = relationship("Transaction")
    analysis_run = relationship("AnalysisRun", back_populates="rule_flags")
    
    # Indexes
    __table_args__ = (
        Index("idx_rule_flags_transaction_analysis", "transaction_id", "analysis_run_id"),
        Index("idx_rule_flags_rule_name", "rule_name"),
        Index("idx_rule_flags_triggered", "triggered"),
        Index("idx_rule_flags_analysis_run", "analysis_run_id"),
    )
    
    def __repr__(self):
        return f"<RuleFlag(id={self.id}, rule_name={self.rule_name}, triggered={self.triggered})>"
    
    def to_dict(self) -> dict:
        """Convert rule flag to dictionary for API responses."""
        return {
            "id": str(self.id),
            "transaction_id": str(self.transaction_id),
            "analysis_run_id": str(self.analysis_run_id),
            "rule_name": self.rule_name,
            "triggered": self.triggered,
            "flag_value": self.flag_value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Import fix for missing BigInteger
from sqlalchemy import BigInteger
AnalysisRun.total_transactions = Column(BigInteger, nullable=True)
AnalysisRun.processed_transactions = Column(BigInteger, default=0) 