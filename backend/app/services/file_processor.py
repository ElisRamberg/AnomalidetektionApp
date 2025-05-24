"""File processing service for parsing and validating uploaded files."""

import io
import json
import csv
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Iterator
from pathlib import Path
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime

from ..utils.exceptions import FileProcessingError, UnsupportedFileTypeError
from ..utils.file_validators import FileValidator
from ..config import get_settings

settings = get_settings()


class FileParser(ABC):
    """Abstract base class for file parsers."""
    
    @abstractmethod
    def parse(self, file_content: bytes, filename: str) -> Iterator[Dict[str, Any]]:
        """
        Parse file content and yield transaction dictionaries.
        
        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            
        Yields:
            Transaction dictionaries
        """
        pass
    
    @abstractmethod
    def validate_structure(self, file_content: bytes) -> Dict[str, Any]:
        """
        Validate file structure and return metadata.
        
        Args:
            file_content: Raw file content as bytes
            
        Returns:
            Validation results and metadata
        """
        pass


class CSVParser(FileParser):
    """Parser for CSV files."""
    
    def __init__(self, delimiter: str = ',', encoding: str = 'utf-8'):
        self.delimiter = delimiter
        self.encoding = encoding
    
    def parse(self, file_content: bytes, filename: str) -> Iterator[Dict[str, Any]]:
        """Parse CSV file content."""
        try:
            content = file_content.decode(self.encoding)
            csv_reader = csv.DictReader(io.StringIO(content), delimiter=self.delimiter)
            
            for row_num, row in enumerate(csv_reader, start=1):
                # Clean empty values and add row metadata
                cleaned_row = {k: v.strip() if v else None for k, v in row.items()}
                cleaned_row['_row_number'] = row_num
                cleaned_row['_source_file'] = filename
                yield cleaned_row
                
        except UnicodeDecodeError as e:
            raise FileProcessingError(f"Encoding error in CSV file: {str(e)}")
        except csv.Error as e:
            raise FileProcessingError(f"CSV parsing error: {str(e)}")
    
    def validate_structure(self, file_content: bytes) -> Dict[str, Any]:
        """Validate CSV structure."""
        try:
            content = file_content.decode(self.encoding)
            csv_reader = csv.DictReader(io.StringIO(content), delimiter=self.delimiter)
            
            # Read first few rows to analyze structure
            sample_rows = []
            fieldnames = csv_reader.fieldnames or []
            
            for i, row in enumerate(csv_reader):
                if i >= 5:  # Sample first 5 rows
                    break
                sample_rows.append(row)
            
            return {
                'valid': True,
                'columns': fieldnames,
                'sample_rows': sample_rows,
                'estimated_rows': None,  # Could implement row counting
                'encoding': self.encoding,
                'delimiter': self.delimiter
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'columns': [],
                'sample_rows': []
            }


class JSONParser(FileParser):
    """Parser for JSON files."""
    
    def parse(self, file_content: bytes, filename: str) -> Iterator[Dict[str, Any]]:
        """Parse JSON file content."""
        try:
            content = file_content.decode('utf-8')
            data = json.loads(content)
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Array of transactions
                for i, transaction in enumerate(data):
                    if isinstance(transaction, dict):
                        transaction['_row_number'] = i + 1
                        transaction['_source_file'] = filename
                        yield transaction
            elif isinstance(data, dict):
                # Single object or structured data
                if 'transactions' in data:
                    # Structured format with transactions array
                    for i, transaction in enumerate(data['transactions']):
                        if isinstance(transaction, dict):
                            transaction['_row_number'] = i + 1
                            transaction['_source_file'] = filename
                            yield transaction
                else:
                    # Single transaction
                    data['_row_number'] = 1
                    data['_source_file'] = filename
                    yield data
            else:
                raise FileProcessingError("Invalid JSON structure: expected object or array")
                
        except json.JSONDecodeError as e:
            raise FileProcessingError(f"JSON parsing error: {str(e)}")
        except UnicodeDecodeError as e:
            raise FileProcessingError(f"Encoding error in JSON file: {str(e)}")
    
    def validate_structure(self, file_content: bytes) -> Dict[str, Any]:
        """Validate JSON structure."""
        try:
            content = file_content.decode('utf-8')
            data = json.loads(content)
            
            transaction_count = 0
            sample_transactions = []
            
            if isinstance(data, list):
                transaction_count = len(data)
                sample_transactions = data[:3]  # First 3 transactions
            elif isinstance(data, dict):
                if 'transactions' in data:
                    transaction_count = len(data['transactions'])
                    sample_transactions = data['transactions'][:3]
                else:
                    transaction_count = 1
                    sample_transactions = [data]
            
            return {
                'valid': True,
                'transaction_count': transaction_count,
                'sample_transactions': sample_transactions,
                'structure_type': 'array' if isinstance(data, list) else 'object'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'transaction_count': 0,
                'sample_transactions': []
            }


class ExcelParser(FileParser):
    """Parser for Excel files (.xlsx, .xls)."""
    
    def __init__(self, sheet_name: Optional[str] = None):
        self.sheet_name = sheet_name or 0  # Default to first sheet
    
    def parse(self, file_content: bytes, filename: str) -> Iterator[Dict[str, Any]]:
        """Parse Excel file content."""
        try:
            # Use pandas to read Excel file
            df = pd.read_excel(io.BytesIO(file_content), sheet_name=self.sheet_name)
            
            # Convert to dictionaries
            for i, row in df.iterrows():
                transaction = row.to_dict()
                # Clean NaN values
                transaction = {k: None if pd.isna(v) else v for k, v in transaction.items()}
                transaction['_row_number'] = i + 2  # +2 because of header and 0-based index
                transaction['_source_file'] = filename
                yield transaction
                
        except Exception as e:
            raise FileProcessingError(f"Excel parsing error: {str(e)}")
    
    def validate_structure(self, file_content: bytes) -> Dict[str, Any]:
        """Validate Excel structure."""
        try:
            df = pd.read_excel(io.BytesIO(file_content), sheet_name=self.sheet_name, nrows=5)
            
            return {
                'valid': True,
                'columns': df.columns.tolist(),
                'row_count': len(df),
                'sample_data': df.head().to_dict('records'),
                'sheet_name': self.sheet_name
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'columns': [],
                'row_count': 0,
                'sample_data': []
            }


class XMLParser(FileParser):
    """Parser for XML files."""
    
    def __init__(self, transaction_element: str = 'transaction'):
        self.transaction_element = transaction_element
    
    def parse(self, file_content: bytes, filename: str) -> Iterator[Dict[str, Any]]:
        """Parse XML file content."""
        try:
            root = ET.fromstring(file_content.decode('utf-8'))
            
            # Find all transaction elements
            transactions = root.findall(f'.//{self.transaction_element}')
            
            for i, transaction_elem in enumerate(transactions):
                transaction = self._element_to_dict(transaction_elem)
                transaction['_row_number'] = i + 1
                transaction['_source_file'] = filename
                yield transaction
                
        except ET.ParseError as e:
            raise FileProcessingError(f"XML parsing error: {str(e)}")
        except UnicodeDecodeError as e:
            raise FileProcessingError(f"Encoding error in XML file: {str(e)}")
    
    def _element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary."""
        result = {}
        
        # Add attributes
        result.update(element.attrib)
        
        # Add text content if no children
        if not list(element):
            if element.text:
                result['_text'] = element.text.strip()
        else:
            # Process child elements
            for child in element:
                child_data = self._element_to_dict(child)
                if child.tag in result:
                    # Handle multiple elements with same tag
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
        
        return result
    
    def validate_structure(self, file_content: bytes) -> Dict[str, Any]:
        """Validate XML structure."""
        try:
            root = ET.fromstring(file_content.decode('utf-8'))
            transactions = root.findall(f'.//{self.transaction_element}')
            
            sample_transactions = []
            for i, transaction in enumerate(transactions[:3]):
                sample_transactions.append(self._element_to_dict(transaction))
            
            return {
                'valid': True,
                'root_element': root.tag,
                'transaction_count': len(transactions),
                'sample_transactions': sample_transactions,
                'transaction_element': self.transaction_element
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'transaction_count': 0,
                'sample_transactions': []
            }


class SIE4Parser(FileParser):
    """Parser for SIE4 (Swedish accounting standard) files."""
    
    def parse(self, file_content: bytes, filename: str) -> Iterator[Dict[str, Any]]:
        """Parse SIE4 file content."""
        # TODO: Implement SIE4 parsing
        # This is a placeholder for Swedish accounting standard
        raise NotImplementedError("SIE4 parser not yet implemented")
    
    def validate_structure(self, file_content: bytes) -> Dict[str, Any]:
        """Validate SIE4 structure."""
        # TODO: Implement SIE4 validation
        return {
            'valid': False,
            'error': "SIE4 parser not yet implemented",
            'transaction_count': 0
        }


class FileProcessorService:
    """Main service for processing uploaded files."""
    
    def __init__(self):
        self.parsers: Dict[str, FileParser] = {
            'csv': CSVParser(),
            'json': JSONParser(),
            'xlsx': ExcelParser(),
            'xls': ExcelParser(),
            'xml': XMLParser(),
            'sie4': SIE4Parser()
        }
        self.validator = FileValidator()
    
    def get_parser(self, file_type: str) -> FileParser:
        """Get appropriate parser for file type."""
        if file_type not in self.parsers:
            raise UnsupportedFileTypeError(f"Unsupported file type: {file_type}")
        return self.parsers[file_type]
    
    def validate_file(self, file_content: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """Validate file before processing."""
        # Basic validation
        validation_result = self.validator.validate_file(file_content, filename, file_type)
        
        if not validation_result['valid']:
            return validation_result
        
        # Structure validation
        parser = self.get_parser(file_type)
        structure_validation = parser.validate_structure(file_content)
        
        # Combine results
        validation_result.update({
            'structure': structure_validation
        })
        
        return validation_result
    
    def process_file(self, file_content: bytes, filename: str, file_type: str) -> Iterator[Dict[str, Any]]:
        """Process file and yield transaction data."""
        # Validate first
        validation = self.validate_file(file_content, filename, file_type)
        if not validation['valid']:
            raise FileProcessingError(f"File validation failed: {validation.get('error', 'Unknown error')}")
        
        # Parse file
        parser = self.get_parser(file_type)
        yield from parser.parse(file_content, filename)
    
    def get_file_info(self, file_content: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """Get detailed information about the file."""
        validation = self.validate_file(file_content, filename, file_type)
        
        return {
            'filename': filename,
            'file_type': file_type,
            'file_size': len(file_content),
            'validation': validation,
            'processing_timestamp': datetime.utcnow().isoformat()
        } 