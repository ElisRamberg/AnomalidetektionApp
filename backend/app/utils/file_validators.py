"""File validation utilities."""

import mimetypes
import magic
from typing import Dict, Any, List, Optional
from pathlib import Path

from .exceptions import FileValidationError, UnsupportedFileTypeError
from ..config import get_settings

settings = get_settings()


class FileValidator:
    """Validator for uploaded files."""
    
    # MIME type mappings for supported file types
    SUPPORTED_MIME_TYPES = {
        'csv': ['text/csv', 'application/csv', 'text/plain'],
        'json': ['application/json', 'text/json'],
        'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        'xls': ['application/vnd.ms-excel'],
        'xml': ['application/xml', 'text/xml'],
        'sie4': ['text/plain', 'application/octet-stream']  # SIE4 is text-based
    }
    
    # File size limits (in bytes)
    DEFAULT_MAX_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self, max_file_size: Optional[int] = None):
        self.max_file_size = max_file_size or settings.max_file_size or self.DEFAULT_MAX_SIZE
        self.allowed_types = settings.allowed_file_types or ['csv', 'json', 'xlsx', 'xls', 'xml']
    
    def validate_file(self, file_content: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """
        Comprehensive file validation.
        
        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            file_type: Detected or provided file type
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {
                'filename': filename,
                'file_type': file_type,
                'file_size': len(file_content),
                'mime_type': None
            }
        }
        
        try:
            # 1. File size validation
            self._validate_file_size(file_content, validation_result)
            
            # 2. File type validation
            self._validate_file_type(file_type, validation_result)
            
            # 3. Filename validation
            self._validate_filename(filename, validation_result)
            
            # 4. MIME type validation
            self._validate_mime_type(file_content, filename, file_type, validation_result)
            
            # 5. Content validation (basic checks)
            self._validate_content(file_content, file_type, validation_result)
            
            # Set overall validity
            validation_result['valid'] = len(validation_result['errors']) == 0
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _validate_file_size(self, file_content: bytes, result: Dict[str, Any]) -> None:
        """Validate file size."""
        file_size = len(file_content)
        
        if file_size == 0:
            result['errors'].append("File is empty")
        elif file_size > self.max_file_size:
            max_size_mb = self.max_file_size / (1024 * 1024)
            current_size_mb = file_size / (1024 * 1024)
            result['errors'].append(
                f"File size ({current_size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb:.2f}MB)"
            )
        
        # Warning for very large files
        if file_size > (50 * 1024 * 1024):  # 50MB
            result['warnings'].append("Large file detected - processing may take longer")
    
    def _validate_file_type(self, file_type: str, result: Dict[str, Any]) -> None:
        """Validate file type against allowed types."""
        if file_type not in self.allowed_types:
            result['errors'].append(
                f"File type '{file_type}' is not supported. "
                f"Allowed types: {', '.join(self.allowed_types)}"
            )
    
    def _validate_filename(self, filename: str, result: Dict[str, Any]) -> None:
        """Validate filename for security and format."""
        if not filename:
            result['errors'].append("Filename is required")
            return
        
        # Check for dangerous characters
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in filename:
                result['errors'].append(f"Filename contains dangerous character: {char}")
                break
        
        # Check filename length
        if len(filename) > 255:
            result['errors'].append("Filename is too long (max 255 characters)")
        
        # Check for extension
        if '.' not in filename:
            result['warnings'].append("Filename has no extension")
    
    def _validate_mime_type(self, file_content: bytes, filename: str, file_type: str, 
                          result: Dict[str, Any]) -> None:
        """Validate MIME type."""
        try:
            # Get MIME type from file content
            detected_mime = magic.from_buffer(file_content, mime=True)
            result['file_info']['mime_type'] = detected_mime
            
            # Check if detected MIME type matches expected type
            expected_mimes = self.SUPPORTED_MIME_TYPES.get(file_type, [])
            
            if detected_mime not in expected_mimes:
                # Some files might have generic MIME types, so add warning instead of error
                result['warnings'].append(
                    f"MIME type '{detected_mime}' doesn't match expected type for {file_type}. "
                    f"Expected: {', '.join(expected_mimes)}"
                )
            
        except Exception as e:
            # If python-magic is not available or fails, use mimetypes as fallback
            try:
                guessed_mime, _ = mimetypes.guess_type(filename)
                result['file_info']['mime_type'] = guessed_mime
                
                if guessed_mime:
                    expected_mimes = self.SUPPORTED_MIME_TYPES.get(file_type, [])
                    if guessed_mime not in expected_mimes:
                        result['warnings'].append(
                            f"Guessed MIME type '{guessed_mime}' doesn't match expected type for {file_type}"
                        )
                else:
                    result['warnings'].append("Could not determine MIME type")
                    
            except Exception:
                result['warnings'].append(f"MIME type detection failed: {str(e)}")
    
    def _validate_content(self, file_content: bytes, file_type: str, result: Dict[str, Any]) -> None:
        """Basic content validation."""
        if file_type == 'json':
            self._validate_json_content(file_content, result)
        elif file_type == 'csv':
            self._validate_csv_content(file_content, result)
        elif file_type == 'xml':
            self._validate_xml_content(file_content, result)
        elif file_type in ['xlsx', 'xls']:
            self._validate_excel_content(file_content, result)
    
    def _validate_json_content(self, file_content: bytes, result: Dict[str, Any]) -> None:
        """Basic JSON content validation."""
        try:
            import json
            content = file_content.decode('utf-8')
            json.loads(content)
        except UnicodeDecodeError:
            result['errors'].append("JSON file has invalid encoding (expected UTF-8)")
        except json.JSONDecodeError as e:
            result['errors'].append(f"Invalid JSON format: {str(e)}")
    
    def _validate_csv_content(self, file_content: bytes, result: Dict[str, Any]) -> None:
        """Basic CSV content validation."""
        try:
            import csv
            import io
            
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    content = file_content.decode(encoding)
                    csv_reader = csv.reader(io.StringIO(content))
                    # Try to read first row
                    next(csv_reader)
                    break
                except UnicodeDecodeError:
                    continue
                except StopIteration:
                    result['warnings'].append("CSV file appears to be empty")
                    break
                except csv.Error as e:
                    result['errors'].append(f"CSV format error: {str(e)}")
                    break
            else:
                result['errors'].append("Could not decode CSV file with any supported encoding")
                
        except Exception as e:
            result['warnings'].append(f"CSV validation error: {str(e)}")
    
    def _validate_xml_content(self, file_content: bytes, result: Dict[str, Any]) -> None:
        """Basic XML content validation."""
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(file_content.decode('utf-8'))
        except UnicodeDecodeError:
            result['errors'].append("XML file has invalid encoding (expected UTF-8)")
        except ET.ParseError as e:
            result['errors'].append(f"Invalid XML format: {str(e)}")
    
    def _validate_excel_content(self, file_content: bytes, result: Dict[str, Any]) -> None:
        """Basic Excel content validation."""
        try:
            import pandas as pd
            import io
            
            # Try to read the Excel file
            pd.read_excel(io.BytesIO(file_content), nrows=1)
            
        except Exception as e:
            result['errors'].append(f"Excel file validation error: {str(e)}")
    
    def get_file_type_from_filename(self, filename: str) -> Optional[str]:
        """Extract file type from filename extension."""
        if not filename:
            return None
        
        extension = Path(filename).suffix.lower().lstrip('.')
        
        # Map extensions to our internal file types
        extension_mapping = {
            'csv': 'csv',
            'json': 'json',
            'xlsx': 'xlsx',
            'xls': 'xls',
            'xml': 'xml',
            'sie4': 'sie4',
            'sie': 'sie4'  # Alternative extension for SIE4
        }
        
        return extension_mapping.get(extension)
    
    def is_file_type_supported(self, file_type: str) -> bool:
        """Check if file type is supported."""
        return file_type in self.allowed_types
    
    def get_max_file_size_mb(self) -> float:
        """Get maximum file size in megabytes."""
        return self.max_file_size / (1024 * 1024)
    
    def validate_required_columns(self, columns: List[str], file_type: str) -> Dict[str, Any]:
        """Validate that required columns are present."""
        required_columns = {
            'csv': ['amount', 'timestamp', 'account_id'],
            'json': [],  # JSON can have flexible structure
            'xlsx': ['amount', 'timestamp', 'account_id'],
            'xls': ['amount', 'timestamp', 'account_id'],
            'xml': [],  # XML can have flexible structure
            'sie4': []  # SIE4 has its own format
        }
        
        required = required_columns.get(file_type, [])
        missing = [col for col in required if col not in [c.lower() for c in columns]]
        
        result = {
            'valid': len(missing) == 0,
            'required_columns': required,
            'missing_columns': missing,
            'present_columns': columns
        }
        
        if missing:
            result['message'] = f"Missing required columns: {', '.join(missing)}"
        
        return result 