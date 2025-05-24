"""Tests for custom exception utilities."""

import pytest

from app.utils.exceptions import (
    # Base exceptions
    AnomalyDetectionError,
    
    # File-related exceptions
    FileValidationError,
    FileProcessingError,
    UnsupportedFileTypeError,
    
    # Data-related exceptions
    DataTransformationError,
    ValidationError,
    
    # Algorithm-related exceptions
    AlgorithmError,
    AlgorithmConfigurationError,
    
    # Analysis-related exceptions
    AnalysisError,
    StrategyError,
    StrategyConfigurationError,
    
    # Database-related exceptions
    DatabaseError,
    
    # Other exceptions
    TaskError,
    ConfigurationError,
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError
)


class TestBaseExceptions:
    """Test cases for base exception classes."""

    def test_anomaly_detection_error_basic(self):
        """Test basic AnomalyDetectionError functionality."""
        message = "Test error message"
        error = AnomalyDetectionError(message)
        
        assert str(error) == message
        assert error.message == message
        assert error.error_code is None
        assert error.details == {}

    def test_anomaly_detection_error_with_code(self):
        """Test AnomalyDetectionError with error code."""
        message = "Test error"
        code = "TEST_ERROR_001"
        error = AnomalyDetectionError(message, error_code=code)
        
        assert error.error_code == code

    def test_anomaly_detection_error_with_details(self):
        """Test AnomalyDetectionError with details."""
        message = "Test error"
        details = {"file_id": "123", "line_number": 42}
        error = AnomalyDetectionError(message, details=details)
        
        assert error.details == details

    def test_anomaly_detection_error_inheritance(self):
        """Test that custom exceptions inherit from base exception."""
        error = FileValidationError("Test file error")
        
        assert isinstance(error, AnomalyDetectionError)
        assert isinstance(error, Exception)


class TestFileExceptions:
    """Test cases for file-related exceptions."""

    def test_file_validation_error(self):
        """Test FileValidationError functionality."""
        message = "Invalid file format"
        error = FileValidationError(message)
        
        assert str(error) == message
        assert isinstance(error, FileProcessingError)
        assert isinstance(error, AnomalyDetectionError)

    def test_file_processing_error(self):
        """Test FileProcessingError functionality."""
        message = "Processing failed"
        error_code = "FILE_PROC_001"
        details = {"stage": "parsing"}
        error = FileProcessingError(message, error_code=error_code, details=details)
        
        assert error.error_code == error_code
        assert error.details == details

    def test_unsupported_file_type_error(self):
        """Test UnsupportedFileTypeError functionality."""
        message = "Unsupported file type: pdf"
        details = {"file_type": "pdf", "supported_types": ["csv", "json", "xlsx"]}
        error = UnsupportedFileTypeError(message, details=details)
        
        assert error.details["file_type"] == "pdf"
        assert "csv" in error.details["supported_types"]
        assert isinstance(error, FileProcessingError)


class TestDataExceptions:
    """Test cases for data-related exceptions."""

    def test_data_transformation_error(self):
        """Test DataTransformationError functionality."""
        message = "Transformation failed"
        details = {"transformation_step": "normalization"}
        error = DataTransformationError(message, details=details)
        
        assert error.details["transformation_step"] == "normalization"

    def test_validation_error(self):
        """Test ValidationError functionality."""
        message = "Invalid data"
        details = {"field_name": "amount", "invalid_value": "not_a_number"}
        error = ValidationError(message, details=details)
        
        assert error.details["field_name"] == "amount"
        assert error.details["invalid_value"] == "not_a_number"


class TestAlgorithmExceptions:
    """Test cases for algorithm-related exceptions."""

    def test_algorithm_error(self):
        """Test AlgorithmError functionality."""
        message = "Algorithm failed"
        details = {"algorithm_name": "zscore"}
        error = AlgorithmError(message, details=details)
        
        assert error.details["algorithm_name"] == "zscore"

    def test_algorithm_configuration_error(self):
        """Test AlgorithmConfigurationError functionality."""
        message = "Invalid configuration"
        details = {"config_parameter": "threshold", "invalid_value": -1}
        error = AlgorithmConfigurationError(message, details=details)
        
        assert error.details["config_parameter"] == "threshold"
        assert error.details["invalid_value"] == -1
        assert isinstance(error, AlgorithmError)


class TestAnalysisExceptions:
    """Test cases for analysis-related exceptions."""

    def test_analysis_error(self):
        """Test AnalysisError functionality."""
        message = "Analysis failed"
        details = {"analysis_id": "analysis_123"}
        error = AnalysisError(message, details=details)
        
        assert error.details["analysis_id"] == "analysis_123"

    def test_strategy_error(self):
        """Test StrategyError functionality."""
        message = "Strategy failed"
        error = StrategyError(message)
        
        assert str(error) == message

    def test_strategy_configuration_error(self):
        """Test StrategyConfigurationError functionality."""
        message = "Invalid strategy"
        details = {"strategy_name": "test_strategy", "validation_issues": ["missing_algorithm"]}
        error = StrategyConfigurationError(message, details=details)
        
        assert error.details["strategy_name"] == "test_strategy"
        assert isinstance(error, StrategyError)


class TestOtherExceptions:
    """Test cases for other exception types."""

    def test_database_error(self):
        """Test DatabaseError functionality."""
        message = "Database connection failed"
        details = {"operation": "insert"}
        error = DatabaseError(message, details=details)
        
        assert error.details["operation"] == "insert"

    def test_task_error(self):
        """Test TaskError functionality."""
        message = "Task execution failed"
        details = {"task_id": "task_123", "retry_count": 3}
        error = TaskError(message, details=details)
        
        assert error.details["task_id"] == "task_123"
        assert error.details["retry_count"] == 3

    def test_configuration_error(self):
        """Test ConfigurationError functionality."""
        message = "Invalid configuration"
        error = ConfigurationError(message)
        
        assert str(error) == message

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError functionality."""
        message = "Resource not found"
        details = {"resource_id": "123", "resource_type": "upload"}
        error = ResourceNotFoundError(message, details=details)
        
        assert error.details["resource_id"] == "123"
        assert error.details["resource_type"] == "upload"

    def test_resource_already_exists_error(self):
        """Test ResourceAlreadyExistsError functionality."""
        message = "Resource already exists"
        details = {"resource_name": "duplicate_strategy"}
        error = ResourceAlreadyExistsError(message, details=details)
        
        assert error.details["resource_name"] == "duplicate_strategy"

    def test_authentication_error(self):
        """Test AuthenticationError functionality."""
        message = "Authentication failed"
        details = {"user_id": "user123", "reason": "invalid_token"}
        error = AuthenticationError(message, details=details)
        
        assert error.details["user_id"] == "user123"
        assert error.details["reason"] == "invalid_token"

    def test_authorization_error(self):
        """Test AuthorizationError functionality."""
        message = "Access denied"
        details = {"required_permission": "admin", "user_role": "user"}
        error = AuthorizationError(message, details=details)
        
        assert error.details["required_permission"] == "admin"
        assert error.details["user_role"] == "user"

    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceededError functionality."""
        message = "Rate limit exceeded"
        details = {"limit": 100, "current_count": 150, "reset_time": "2023-01-01T12:00:00Z"}
        error = RateLimitExceededError(message, details=details)
        
        assert error.details["limit"] == 100
        assert error.details["current_count"] == 150


class TestExceptionUtilities:
    """Test cases for exception utility methods."""

    def test_exception_inheritance_chain(self):
        """Test exception inheritance chain is correct."""
        # File exceptions
        assert issubclass(UnsupportedFileTypeError, FileProcessingError)
        assert issubclass(FileValidationError, FileProcessingError)
        assert issubclass(FileProcessingError, AnomalyDetectionError)
        
        # Algorithm exceptions
        assert issubclass(AlgorithmConfigurationError, AlgorithmError)
        assert issubclass(AlgorithmError, AnomalyDetectionError)
        
        # Strategy exceptions
        assert issubclass(StrategyConfigurationError, StrategyError)
        assert issubclass(StrategyError, AnomalyDetectionError)

    def test_exception_with_all_parameters(self):
        """Test exception with all parameters."""
        message = "Test error"
        error_code = "TEST_001"
        details = {"key": "value", "number": 42}
        
        error = AnomalyDetectionError(message, error_code=error_code, details=details)
        
        assert str(error) == message
        assert error.message == message
        assert error.error_code == error_code
        assert error.details == details

    def test_exception_details_mutation(self):
        """Test that exception details can be modified after creation."""
        error = AnomalyDetectionError("Test error")
        
        # Initially empty details
        assert error.details == {}
        
        # Can add details
        error.details["new_key"] = "new_value"
        assert error.details["new_key"] == "new_value"

    def test_exception_error_code_uniqueness(self):
        """Test that different exception types can have unique error codes."""
        errors = [
            FileValidationError("Test", error_code="FILE_001"),
            DataTransformationError("Test", error_code="DATA_001"),
            AlgorithmError("Test", error_code="ALG_001"),
            AnalysisError("Test", error_code="ANALYSIS_001")
        ]
        
        error_codes = [e.error_code for e in errors]
        assert len(set(error_codes)) == len(error_codes)  # All unique

    def test_exception_string_representation(self):
        """Test exception string representation."""
        error = FileProcessingError("File processing failed")
        
        # String representation should be the message
        assert str(error) == "File processing failed"
        
        # Should work with repr as well
        repr_str = repr(error)
        assert "FileProcessingError" in repr_str or "File processing failed" in repr_str 