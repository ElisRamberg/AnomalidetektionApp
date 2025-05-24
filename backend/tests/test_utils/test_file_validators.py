"""Tests for file validator utilities."""

import pytest
import tempfile
import os
from unittest.mock import patch, mock_open
import io

from app.utils.file_validators import FileValidator, FileTypeDetector
from app.utils.exceptions import FileValidationError


class TestFileValidator:
    """Test cases for FileValidator utility."""

    @pytest.fixture
    def validator(self):
        """Create FileValidator instance."""
        return FileValidator()

    def test_validate_file_size_success(self, validator):
        """Test successful file size validation."""
        content = b"small file content"
        max_size = 1024 * 1024  # 1MB
        
        # Should not raise exception
        validator.validate_file_size(content, max_size)

    def test_validate_file_size_too_large(self, validator):
        """Test file size validation failure."""
        content = b"x" * (2 * 1024 * 1024)  # 2MB content
        max_size = 1024 * 1024  # 1MB limit
        
        with pytest.raises(FileValidationError, match="File size.*exceeds maximum allowed"):
            validator.validate_file_size(content, max_size)

    def test_validate_file_size_empty(self, validator):
        """Test empty file validation."""
        content = b""
        max_size = 1024 * 1024
        
        with pytest.raises(FileValidationError, match="File is empty"):
            validator.validate_file_size(content, max_size)

    def test_validate_mime_type_csv(self, validator):
        """Test MIME type validation for CSV."""
        # Valid CSV MIME types
        valid_types = ["text/csv", "application/csv", "text/plain"]
        
        for mime_type in valid_types:
            validator.validate_mime_type(mime_type, "csv")  # Should not raise

    def test_validate_mime_type_json(self, validator):
        """Test MIME type validation for JSON."""
        valid_types = ["application/json", "text/json"]
        
        for mime_type in valid_types:
            validator.validate_mime_type(mime_type, "json")  # Should not raise

    def test_validate_mime_type_excel(self, validator):
        """Test MIME type validation for Excel."""
        valid_types = [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel"
        ]
        
        for mime_type in valid_types:
            validator.validate_mime_type(mime_type, "excel")  # Should not raise

    def test_validate_mime_type_invalid(self, validator):
        """Test invalid MIME type validation."""
        with pytest.raises(FileValidationError, match="Invalid MIME type"):
            validator.validate_mime_type("application/pdf", "csv")

    def test_validate_filename_valid(self, validator):
        """Test valid filename validation."""
        valid_filenames = [
            "data.csv",
            "transactions_2023.json",
            "report-final.xlsx",
            "file_with_underscore.csv",
            "file with spaces.json"
        ]
        
        for filename in valid_filenames:
            validator.validate_filename(filename)  # Should not raise

    def test_validate_filename_invalid_extension(self, validator):
        """Test invalid filename extension."""
        with pytest.raises(FileValidationError, match="Unsupported file extension"):
            validator.validate_filename("document.pdf")

    def test_validate_filename_no_extension(self, validator):
        """Test filename without extension."""
        with pytest.raises(FileValidationError, match="File must have an extension"):
            validator.validate_filename("filename_without_extension")

    def test_validate_filename_dangerous_characters(self, validator):
        """Test filename with dangerous characters."""
        dangerous_filenames = [
            "../../../etc/passwd",
            "file<script>.csv",
            "file>output.csv",
            "file|pipe.csv",
            "file:colon.csv",
            "file*wildcard.csv",
            "file?question.csv",
            'file"quote.csv'
        ]
        
        for filename in dangerous_filenames:
            with pytest.raises(FileValidationError, match="contains invalid characters"):
                validator.validate_filename(filename)

    def test_validate_filename_too_long(self, validator):
        """Test filename that's too long."""
        long_filename = "x" * 300 + ".csv"
        
        with pytest.raises(FileValidationError, match="Filename is too long"):
            validator.validate_filename(long_filename)

    def test_validate_csv_structure_valid(self, validator):
        """Test valid CSV structure validation."""
        csv_content = b"""amount,timestamp,account_id
100.50,2023-01-01T10:00:00Z,ACC001
-25.00,2023-01-01T11:00:00Z,ACC002"""
        
        result = validator.validate_csv_structure(csv_content)
        
        assert result["valid"] is True
        assert "headers" in result
        assert "row_count" in result
        assert result["headers"] == ["amount", "timestamp", "account_id"]
        assert result["row_count"] == 2

    def test_validate_csv_structure_empty(self, validator):
        """Test empty CSV validation."""
        csv_content = b""
        
        result = validator.validate_csv_structure(csv_content)
        
        assert result["valid"] is False
        assert "error" in result

    def test_validate_csv_structure_no_headers(self, validator):
        """Test CSV without headers."""
        csv_content = b"100.50,2023-01-01T10:00:00Z,ACC001"
        
        result = validator.validate_csv_structure(csv_content)
        
        assert result["valid"] is False
        assert "error" in result

    def test_validate_csv_structure_inconsistent_columns(self, validator):
        """Test CSV with inconsistent column counts."""
        csv_content = b"""amount,timestamp,account_id
100.50,2023-01-01T10:00:00Z,ACC001
-25.00,2023-01-01T11:00:00Z"""  # Missing column
        
        result = validator.validate_csv_structure(csv_content)
        
        assert result["valid"] is False
        assert "error" in result

    def test_validate_json_structure_valid(self, validator):
        """Test valid JSON structure validation."""
        json_content = b"""[
            {
                "amount": 100.50,
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
            },
            {
                "amount": -25.00,
                "timestamp": "2023-01-01T11:00:00Z",
                "account_id": "ACC002"
            }
        ]"""
        
        result = validator.validate_json_structure(json_content)
        
        assert result["valid"] is True
        assert "data_type" in result
        assert "record_count" in result
        assert result["data_type"] == "array"
        assert result["record_count"] == 2

    def test_validate_json_structure_object(self, validator):
        """Test JSON object structure validation."""
        json_content = b"""{
            "transactions": [
                {"amount": 100.50, "account_id": "ACC001"}
            ]
        }"""
        
        result = validator.validate_json_structure(json_content)
        
        assert result["valid"] is True
        assert result["data_type"] == "object"

    def test_validate_json_structure_invalid(self, validator):
        """Test invalid JSON validation."""
        json_content = b"""{"invalid": json,}"""
        
        result = validator.validate_json_structure(json_content)
        
        assert result["valid"] is False
        assert "error" in result

    def test_validate_excel_structure_valid(self, validator):
        """Test valid Excel structure validation."""
        # Create a simple Excel file in memory
        import io
        from openpyxl import Workbook
        
        wb = Workbook()
        ws = wb.active
        ws.append(["amount", "timestamp", "account_id"])
        ws.append([100.50, "2023-01-01T10:00:00Z", "ACC001"])
        ws.append([-25.00, "2023-01-01T11:00:00Z", "ACC002"])
        
        output = io.BytesIO()
        wb.save(output)
        excel_content = output.getvalue()
        
        result = validator.validate_excel_structure(excel_content)
        
        assert result["valid"] is True
        assert "headers" in result
        assert "row_count" in result
        assert "sheet_count" in result

    def test_validate_excel_structure_invalid(self, validator):
        """Test invalid Excel file validation."""
        invalid_content = b"not an excel file"
        
        result = validator.validate_excel_structure(invalid_content)
        
        assert result["valid"] is False
        assert "error" in result

    def test_check_required_columns_present(self, validator):
        """Test required columns validation."""
        headers = ["amount", "timestamp", "account_id", "extra_column"]
        
        # Should not raise for valid headers
        validator.check_required_columns(headers)

    def test_check_required_columns_missing(self, validator):
        """Test missing required columns."""
        headers = ["amount", "timestamp"]  # Missing account_id
        
        with pytest.raises(FileValidationError, match="Missing required columns"):
            validator.check_required_columns(headers)

    def test_estimate_processing_time(self, validator):
        """Test processing time estimation."""
        # Small file
        small_estimate = validator.estimate_processing_time(1000, "csv")
        assert isinstance(small_estimate, dict)
        assert "estimated_seconds" in small_estimate
        assert "confidence" in small_estimate
        
        # Large file
        large_estimate = validator.estimate_processing_time(1000000, "excel")
        assert large_estimate["estimated_seconds"] > small_estimate["estimated_seconds"]

    def test_validate_file_encoding(self, validator):
        """Test file encoding validation."""
        # UTF-8 content
        utf8_content = "Hello, 世界!".encode('utf-8')
        encoding = validator.validate_file_encoding(utf8_content)
        assert encoding in ["utf-8", "ascii"]
        
        # ASCII content
        ascii_content = b"Hello, World!"
        encoding = validator.validate_file_encoding(ascii_content)
        assert encoding in ["utf-8", "ascii"]

    def test_scan_for_malicious_content(self, validator):
        """Test malicious content scanning."""
        # Safe content
        safe_content = b"amount,timestamp,account_id\n100.50,2023-01-01,ACC001"
        assert validator.scan_for_malicious_content(safe_content) is True
        
        # Potentially dangerous content
        dangerous_content = b"<script>alert('xss')</script>"
        assert validator.scan_for_malicious_content(dangerous_content) is False

    def test_full_validation_pipeline(self, validator):
        """Test complete validation pipeline."""
        # Create valid CSV content
        csv_content = b"""amount,timestamp,account_id
100.50,2023-01-01T10:00:00Z,ACC001
-25.00,2023-01-01T11:00:00Z,ACC002"""
        
        filename = "test_data.csv"
        mime_type = "text/csv"
        max_size = 1024 * 1024
        
        # Should complete without errors
        validation_result = validator.validate_file_complete(
            content=csv_content,
            filename=filename,
            mime_type=mime_type,
            max_size=max_size
        )
        
        assert validation_result["valid"] is True
        assert "file_info" in validation_result
        assert "structure_info" in validation_result
        assert "security_info" in validation_result


class TestFileTypeDetector:
    """Test cases for FileTypeDetector utility."""

    @pytest.fixture
    def detector(self):
        """Create FileTypeDetector instance."""
        return FileTypeDetector()

    def test_detect_csv_by_extension(self, detector):
        """Test CSV detection by file extension."""
        result = detector.detect_file_type("data.csv", b"amount,timestamp\n100,2023-01-01")
        assert result["file_type"] == "csv"
        assert result["confidence"] > 0.8

    def test_detect_json_by_extension(self, detector):
        """Test JSON detection by file extension."""
        content = b'[{"amount": 100, "timestamp": "2023-01-01"}]'
        result = detector.detect_file_type("data.json", content)
        assert result["file_type"] == "json"
        assert result["confidence"] > 0.8

    def test_detect_excel_by_extension(self, detector):
        """Test Excel detection by file extension."""
        # Mock Excel content (simplified)
        excel_content = b"PK\x03\x04"  # ZIP file signature (Excel is a ZIP)
        result = detector.detect_file_type("data.xlsx", excel_content)
        assert result["file_type"] == "excel"

    def test_detect_by_content_csv(self, detector):
        """Test CSV detection by content analysis."""
        csv_content = b"amount,timestamp,account_id\n100.50,2023-01-01,ACC001"
        result = detector.detect_by_content(csv_content)
        assert result["file_type"] == "csv"

    def test_detect_by_content_json(self, detector):
        """Test JSON detection by content analysis."""
        json_content = b'[{"amount": 100.50, "account_id": "ACC001"}]'
        result = detector.detect_by_content(json_content)
        assert result["file_type"] == "json"

    def test_detect_by_content_xml(self, detector):
        """Test XML detection by content analysis."""
        xml_content = b'<?xml version="1.0"?><transactions><transaction amount="100.50"/></transactions>'
        result = detector.detect_by_content(xml_content)
        assert result["file_type"] == "xml"

    def test_detect_conflicting_extension_content(self, detector):
        """Test handling of conflicting extension and content."""
        # JSON content with CSV extension
        json_content = b'[{"amount": 100.50}]'
        result = detector.detect_file_type("data.csv", json_content)
        
        # Should detect the conflict
        assert "content_mismatch" in result
        assert result["content_mismatch"] is True

    def test_detect_unknown_file_type(self, detector):
        """Test detection of unknown file types."""
        unknown_content = b"This is some unknown binary content\x00\x01\x02"
        result = detector.detect_file_type("data.unknown", unknown_content)
        
        assert result["file_type"] == "unknown"
        assert result["confidence"] == 0.0

    def test_get_supported_extensions(self, detector):
        """Test getting supported file extensions."""
        extensions = detector.get_supported_extensions()
        
        assert isinstance(extensions, list)
        assert "csv" in extensions
        assert "json" in extensions
        assert "xlsx" in extensions
        assert "xml" in extensions

    def test_is_supported_file_type(self, detector):
        """Test checking if file type is supported."""
        assert detector.is_supported_file_type("csv") is True
        assert detector.is_supported_file_type("json") is True
        assert detector.is_supported_file_type("excel") is True
        assert detector.is_supported_file_type("pdf") is False
        assert detector.is_supported_file_type("unknown") is False

    def test_get_file_type_info(self, detector):
        """Test getting file type information."""
        csv_info = detector.get_file_type_info("csv")
        
        assert isinstance(csv_info, dict)
        assert "description" in csv_info
        assert "mime_types" in csv_info
        assert "extensions" in csv_info
        assert "parser_available" in csv_info

    def test_validate_file_type_compatibility(self, detector):
        """Test file type compatibility validation."""
        # CSV should be compatible with transaction data
        assert detector.validate_file_type_compatibility("csv", "transaction") is True
        
        # Unknown types should not be compatible
        assert detector.validate_file_type_compatibility("pdf", "transaction") is False

    def test_suggest_file_type_correction(self, detector):
        """Test file type correction suggestions."""
        # Test with common misspellings/variations
        suggestions = detector.suggest_file_type_correction("csv")
        assert "csv" in suggestions
        
        suggestions = detector.suggest_file_type_correction("xls")
        assert "excel" in suggestions or "xlsx" in suggestions

    def test_analyze_file_header(self, detector):
        """Test file header analysis."""
        # CSV header analysis
        csv_content = b"amount,timestamp,account_id\n100,2023-01-01,ACC001"
        analysis = detector.analyze_file_header(csv_content, "csv")
        
        assert "columns_detected" in analysis
        assert "delimiter" in analysis
        assert analysis["columns_detected"] == 3

    def test_performance_with_large_content(self, detector):
        """Test performance with large file content."""
        # Create large CSV content
        large_csv = b"amount,timestamp,account_id\n"
        for i in range(10000):
            large_csv += f"{i*10.5},2023-01-01T{i%24:02d}:00:00Z,ACC{i%100:03d}\n".encode()
        
        import time
        start_time = time.time()
        result = detector.detect_file_type("large_data.csv", large_csv)
        detection_time = time.time() - start_time
        
        # Should detect correctly and quickly
        assert result["file_type"] == "csv"
        assert detection_time < 5.0  # Should complete in under 5 seconds

    def test_edge_case_empty_file(self, detector):
        """Test edge case with empty file."""
        result = detector.detect_file_type("empty.csv", b"")
        
        assert result["file_type"] == "unknown"
        assert result["confidence"] == 0.0

    def test_edge_case_binary_file(self, detector):
        """Test edge case with binary file."""
        binary_content = bytes(range(256))  # Binary content
        result = detector.detect_file_type("binary.dat", binary_content)
        
        assert result["file_type"] == "unknown"
        assert result["confidence"] == 0.0 