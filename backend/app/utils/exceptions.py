"""Custom exceptions for the anomaly detection application."""


class AnomalyDetectionError(Exception):
    """Base exception for all anomaly detection related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class FileProcessingError(AnomalyDetectionError):
    """Exception raised during file processing operations."""
    pass


class UnsupportedFileTypeError(FileProcessingError):
    """Exception raised for unsupported file types."""
    pass


class FileValidationError(FileProcessingError):
    """Exception raised when file validation fails."""
    pass


class DataTransformationError(AnomalyDetectionError):
    """Exception raised during data transformation operations."""
    pass


class AlgorithmError(AnomalyDetectionError):
    """Exception raised during algorithm execution."""
    pass


class AlgorithmConfigurationError(AlgorithmError):
    """Exception raised for invalid algorithm configurations."""
    pass


class StrategyError(AnomalyDetectionError):
    """Exception raised during strategy operations."""
    pass


class StrategyConfigurationError(StrategyError):
    """Exception raised for invalid strategy configurations."""
    pass


class AnalysisError(AnomalyDetectionError):
    """Exception raised during analysis operations."""
    pass


class DatabaseError(AnomalyDetectionError):
    """Exception raised for database operations."""
    pass


class TaskError(AnomalyDetectionError):
    """Exception raised during Celery task execution."""
    pass


class ValidationError(AnomalyDetectionError):
    """Exception raised for validation errors."""
    pass


class ConfigurationError(AnomalyDetectionError):
    """Exception raised for configuration errors."""
    pass


class ResourceNotFoundError(AnomalyDetectionError):
    """Exception raised when a requested resource is not found."""
    pass


class ResourceAlreadyExistsError(AnomalyDetectionError):
    """Exception raised when trying to create a resource that already exists."""
    pass


class AuthenticationError(AnomalyDetectionError):
    """Exception raised for authentication failures."""
    pass


class AuthorizationError(AnomalyDetectionError):
    """Exception raised for authorization failures."""
    pass


class RateLimitExceededError(AnomalyDetectionError):
    """Exception raised when rate limits are exceeded."""
    pass 