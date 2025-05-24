"""Strategy database model."""

from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from ..database import Base


class Strategy(Base):
    """Model for storing anomaly detection strategy configurations."""
    
    __tablename__ = "strategies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Strategy configuration stored as JSON
    configuration = Column(JSONB, nullable=False)
    
    # Strategy metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_preset = Column(Boolean, default=False, nullable=False)  # System presets vs custom
    
    # Audit fields
    created_by = Column(String(255), nullable=True)  # User who created the strategy
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Strategy(id={self.id}, name={self.name}, is_active={self.is_active})>"
    
    @property
    def enabled_algorithms(self) -> list:
        """Get list of enabled algorithms in this strategy."""
        if not self.configuration:
            return []
        
        algorithms = []
        for algo_type in ["statistical", "rule_based", "ml_based"]:
            if algo_type in self.configuration:
                for algo_name, config in self.configuration[algo_type].items():
                    if config.get("enabled", False):
                        algorithms.append(f"{algo_type}.{algo_name}")
        
        return algorithms
    
    @property
    def algorithm_count(self) -> int:
        """Get total number of enabled algorithms."""
        return len(self.enabled_algorithms)
    
    def get_algorithm_config(self, algorithm_type: str, algorithm_name: str) -> dict:
        """Get configuration for a specific algorithm."""
        if not self.configuration:
            return {}
        
        return (
            self.configuration
            .get(algorithm_type, {})
            .get(algorithm_name, {})
        )
    
    def is_algorithm_enabled(self, algorithm_type: str, algorithm_name: str) -> bool:
        """Check if a specific algorithm is enabled in this strategy."""
        config = self.get_algorithm_config(algorithm_type, algorithm_name)
        return config.get("enabled", False)
    
    def to_dict(self) -> dict:
        """Convert strategy to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "configuration": self.configuration,
            "is_active": self.is_active,
            "is_preset": self.is_preset,
            "enabled_algorithms": self.enabled_algorithms,
            "algorithm_count": self.algorithm_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def create_default_strategy(cls) -> dict:
        """Create configuration for a default balanced strategy."""
        return {
            "statistical": {
                "zscore": {
                    "enabled": True,
                    "threshold": 3.0,
                    "window_size": 30
                },
                "correlation": {
                    "enabled": True,
                    "correlation_threshold": 0.8,
                    "min_transactions": 10
                }
            },
            "rule_based": {
                "weekend_threshold": {
                    "enabled": True,
                    "weekend_multiplier": 2.0,
                    "min_amount": 1000
                },
                "periodization": {
                    "enabled": True,
                    "check_monthly_patterns": True,
                    "deviation_threshold": 0.5
                }
            },
            "ml_based": {
                "isolation_forest": {
                    "enabled": True,
                    "contamination": 0.1,
                    "random_state": 42
                }
            }
        } 