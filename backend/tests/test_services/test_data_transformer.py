"""Tests for data transformer service."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch

from app.services.data_transformer import DataTransformerService
from app.utils.exceptions import DataTransformationError


class TestDataTransformerService:
    """Test cases for data transformer service."""

    @pytest.fixture
    def service(self):
        """Create data transformer service instance."""
        return DataTransformerService()

    @pytest.fixture
    def sample_raw_transactions(self):
        """Sample raw transaction data."""
        return [
            {
                "amount": "100.50",
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001",
                "external_transaction_id": "TXN001"
            },
            {
                "belopp": "-25.00",  # Swedish amount field
                "datum": "2023-01-01T11:00:00Z",  # Swedish date field
                "konto": "ACC001",  # Swedish account field
                "referens": "TXN002"  # Swedish reference field
            },
            {
                "value": 200.00,  # Alternative amount field
                "date": "2023-01-01T12:00:00Z",  # Alternative date field
                "account": "ACC002",  # Alternative account field
                "transaction_id": "TXN003"
            }
        ]

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.data_validator is not None

    def test_transform_transactions_success(self, service, sample_raw_transactions):
        """Test successful transaction transformation."""
        upload_id = "test-upload-123"
        
        result_df = service.transform_transactions(sample_raw_transactions, upload_id)
        
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 3
        
        # Check required columns exist
        required_columns = ['id', 'amount', 'timestamp', 'account_id', 'upload_id', 'raw_data']
        for col in required_columns:
            assert col in result_df.columns
        
        # Check upload_id is set correctly
        assert all(result_df['upload_id'] == upload_id)
        
        # Check data types
        assert pd.api.types.is_numeric_dtype(result_df['amount'])
        assert pd.api.types.is_datetime64_any_dtype(result_df['timestamp'])

    def test_transform_empty_transactions(self, service):
        """Test transformation with empty transaction list."""
        with pytest.raises(DataTransformationError, match="No transactions to transform"):
            service.transform_transactions([], "test-upload")

    def test_column_standardization(self, service):
        """Test column name standardization."""
        raw_data = [
            {
                "belopp": 100.0,  # Swedish amount
                "datum": "2023-01-01T10:00:00Z",  # Swedish date
                "konto": "ACC001",  # Swedish account
                "referens": "TXN001"  # Swedish reference
            }
        ]
        
        result_df = service.transform_transactions(raw_data, "test-upload")
        
        # Should have standardized column names
        assert 'amount' in result_df.columns
        assert 'timestamp' in result_df.columns
        assert 'account_id' in result_df.columns
        assert 'external_transaction_id' in result_df.columns

    def test_transaction_id_generation(self, service, sample_raw_transactions):
        """Test transaction ID generation."""
        # Remove IDs from sample data
        data_without_ids = [
            {
                "amount": 100.0,
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
            },
            {
                "amount": 200.0,
                "timestamp": "2023-01-01T11:00:00Z",
                "account_id": "ACC002"
            }
        ]
        
        result_df = service.transform_transactions(data_without_ids, "test-upload")
        
        # Should have generated unique IDs
        assert len(result_df['id'].unique()) == len(result_df)
        assert all(result_df['id'].notna())

    def test_duplicate_id_handling(self, service):
        """Test handling of duplicate transaction IDs."""
        data_with_duplicates = [
            {
                "id": "TXN001",
                "amount": 100.0,
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
            },
            {
                "id": "TXN001",  # Duplicate ID
                "amount": 200.0,
                "timestamp": "2023-01-01T11:00:00Z",
                "account_id": "ACC002"
            }
        ]
        
        result_df = service.transform_transactions(data_with_duplicates, "test-upload")
        
        # Should have unique IDs
        assert len(result_df['id'].unique()) == len(result_df)

    def test_timestamp_parsing(self, service):
        """Test timestamp parsing with various formats."""
        data_with_timestamps = [
            {
                "amount": 100.0,
                "timestamp": "2023-01-01T10:00:00Z",  # ISO format
                "account_id": "ACC001"
            },
            {
                "amount": 200.0,
                "timestamp": "2023-01-01 11:00:00",  # SQL format
                "account_id": "ACC002"
            },
            {
                "amount": 300.0,
                "timestamp": "01/01/2023 12:00",  # US format
                "account_id": "ACC003"
            }
        ]
        
        result_df = service.transform_transactions(data_with_timestamps, "test-upload")
        
        # All timestamps should be parsed successfully
        assert all(result_df['timestamp'].notna())
        assert pd.api.types.is_datetime64_any_dtype(result_df['timestamp'])

    def test_amount_cleaning(self, service):
        """Test amount field cleaning and parsing."""
        data_with_amounts = [
            {
                "amount": "€100.50",  # With currency symbol
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
            },
            {
                "amount": "$2,500.75",  # With currency and comma
                "timestamp": "2023-01-01T11:00:00Z",
                "account_id": "ACC002"
            },
            {
                "amount": "1.234,56",  # European decimal format
                "timestamp": "2023-01-01T12:00:00Z",
                "account_id": "ACC003"
            },
            {
                "amount": -150.25,  # Negative number
                "timestamp": "2023-01-01T13:00:00Z",
                "account_id": "ACC004"
            }
        ]
        
        result_df = service.transform_transactions(data_with_amounts, "test-upload")
        
        # All amounts should be numeric
        assert pd.api.types.is_numeric_dtype(result_df['amount'])
        assert all(result_df['amount'].notna())
        
        # Check specific values
        assert result_df.iloc[0]['amount'] == 100.50
        assert result_df.iloc[1]['amount'] == 2500.75
        assert result_df.iloc[2]['amount'] == 1234.56
        assert result_df.iloc[3]['amount'] == -150.25

    def test_account_id_standardization(self, service):
        """Test account ID standardization."""
        data_with_accounts = [
            {
                "amount": 100.0,
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "  acc001  "  # With spaces
            },
            {
                "amount": 200.0,
                "timestamp": "2023-01-01T11:00:00Z",
                "account_id": "acc002"  # Lowercase
            }
        ]
        
        result_df = service.transform_transactions(data_with_accounts, "test-upload")
        
        # Account IDs should be standardized
        assert result_df.iloc[0]['account_id'] == "ACC001"
        assert result_df.iloc[1]['account_id'] == "ACC002"

    def test_derived_fields_creation(self, service):
        """Test creation of derived time-based and amount-based fields."""
        data = [
            {
                "amount": 150.75,
                "timestamp": "2023-01-07T14:30:00Z",  # Saturday afternoon
                "account_id": "ACC001"
            },
            {
                "amount": -50.25,
                "timestamp": "2023-01-09T09:15:00Z",  # Monday morning
                "account_id": "ACC002"
            }
        ]
        
        result_df = service.transform_transactions(data, "test-upload")
        
        # Check time-based derived fields
        time_fields = ['year', 'month', 'day', 'hour', 'day_of_week', 'is_weekend', 'is_business_hours']
        for field in time_fields:
            assert field in result_df.columns
        
        # Check amount-based derived fields
        amount_fields = ['amount_abs', 'is_debit', 'is_credit', 'amount_category']
        for field in amount_fields:
            assert field in result_df.columns
        
        # Check specific derived values
        assert result_df.iloc[0]['is_weekend'] == True  # Saturday
        assert result_df.iloc[1]['is_weekend'] == False  # Monday
        
        assert result_df.iloc[0]['is_business_hours'] == True  # 14:30
        assert result_df.iloc[1]['is_business_hours'] == True  # 09:15
        
        assert result_df.iloc[0]['is_credit'] == True   # Positive amount
        assert result_df.iloc[1]['is_debit'] == True    # Negative amount

    def test_transaction_sequence_calculation(self, service):
        """Test transaction sequence numbering per account."""
        data = [
            {
                "amount": 100.0,
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
            },
            {
                "amount": 200.0,
                "timestamp": "2023-01-01T11:00:00Z",
                "account_id": "ACC002"
            },
            {
                "amount": 300.0,
                "timestamp": "2023-01-01T12:00:00Z",
                "account_id": "ACC001"  # Second transaction for ACC001
            }
        ]
        
        result_df = service.transform_transactions(data, "test-upload")
        
        # Check transaction sequences
        acc001_transactions = result_df[result_df['account_id'] == 'ACC001'].sort_values('timestamp')
        acc002_transactions = result_df[result_df['account_id'] == 'ACC002']
        
        assert list(acc001_transactions['transaction_sequence']) == [1, 2]
        assert list(acc002_transactions['transaction_sequence']) == [1]

    def test_time_difference_calculation(self, service):
        """Test time difference calculation between consecutive transactions."""
        data = [
            {
                "amount": 100.0,
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
            },
            {
                "amount": 200.0,
                "timestamp": "2023-01-01T12:00:00Z",  # 2 hours later
                "account_id": "ACC001"
            }
        ]
        
        result_df = service.transform_transactions(data, "test-upload")
        
        # First transaction should have NaN time difference
        assert pd.isna(result_df.iloc[0]['time_since_prev_hours'])
        
        # Second transaction should have 2 hours difference
        assert result_df.iloc[1]['time_since_prev_hours'] == 2.0

    def test_metadata_addition(self, service, sample_raw_transactions):
        """Test addition of metadata fields."""
        result_df = service.transform_transactions(sample_raw_transactions, "test-upload")
        
        # Check metadata fields
        assert 'upload_id' in result_df.columns
        assert 'processed_at' in result_df.columns
        assert 'raw_data' in result_df.columns
        
        # Check raw_data contains original information
        assert all(isinstance(raw_data, dict) for raw_data in result_df['raw_data'])

    def test_missing_required_fields(self, service):
        """Test handling of missing required fields."""
        data_missing_amount = [
            {
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
                # Missing amount
            }
        ]
        
        # Should handle gracefully by dropping invalid rows
        result_df = service.transform_transactions(data_missing_amount, "test-upload")
        
        # Should result in empty DataFrame after cleaning
        assert len(result_df) == 0

    def test_invalid_timestamps(self, service):
        """Test handling of invalid timestamps."""
        data_invalid_timestamps = [
            {
                "amount": 100.0,
                "timestamp": "invalid-timestamp",
                "account_id": "ACC001"
            },
            {
                "amount": 200.0,
                "timestamp": "2023-01-01T10:00:00Z",  # Valid timestamp
                "account_id": "ACC002"
            }
        ]
        
        result_df = service.transform_transactions(data_invalid_timestamps, "test-upload")
        
        # Should drop row with invalid timestamp
        assert len(result_df) == 1
        assert result_df.iloc[0]['account_id'] == 'ACC002'

    def test_invalid_amounts(self, service):
        """Test handling of invalid amounts."""
        data_invalid_amounts = [
            {
                "amount": "not-a-number",
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
            },
            {
                "amount": 200.0,  # Valid amount
                "timestamp": "2023-01-01T11:00:00Z",
                "account_id": "ACC002"
            }
        ]
        
        result_df = service.transform_transactions(data_invalid_amounts, "test-upload")
        
        # Should drop row with invalid amount
        assert len(result_df) == 1
        assert result_df.iloc[0]['account_id'] == 'ACC002'

    def test_amount_category_classification(self, service):
        """Test amount category classification."""
        data_various_amounts = [
            {"amount": 50.0, "timestamp": "2023-01-01T10:00:00Z", "account_id": "ACC001"},     # micro
            {"amount": 500.0, "timestamp": "2023-01-01T10:00:00Z", "account_id": "ACC001"},    # small  
            {"amount": 5000.0, "timestamp": "2023-01-01T10:00:00Z", "account_id": "ACC001"},   # medium
            {"amount": 50000.0, "timestamp": "2023-01-01T10:00:00Z", "account_id": "ACC001"},  # large
            {"amount": 500000.0, "timestamp": "2023-01-01T10:00:00Z", "account_id": "ACC001"}, # huge
        ]
        
        result_df = service.transform_transactions(data_various_amounts, "test-upload")
        
        categories = result_df['amount_category'].tolist()
        expected_categories = ['micro', 'small', 'medium', 'large', 'huge']
        
        assert categories == expected_categories

    def test_get_transformation_stats(self, service, sample_raw_transactions):
        """Test transformation statistics calculation."""
        result_df = service.transform_transactions(sample_raw_transactions, "test-upload")
        
        stats = service.get_transformation_stats(len(sample_raw_transactions), result_df)
        
        assert isinstance(stats, dict)
        assert 'original_count' in stats
        assert 'final_count' in stats
        assert 'dropped_count' in stats
        assert 'drop_rate' in stats
        assert 'date_range' in stats
        assert 'amount_stats' in stats
        assert 'account_count' in stats
        assert 'features_added' in stats
        
        assert stats['original_count'] == 3
        assert stats['final_count'] == len(result_df)
        assert stats['dropped_count'] == 3 - len(result_df)

    def test_large_dataset_performance(self, service):
        """Test performance with larger dataset."""
        # Create larger dataset
        large_data = []
        for i in range(5000):
            large_data.append({
                "amount": 100.0 + i,
                "timestamp": f"2023-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00Z",
                "account_id": f"ACC{(i % 100) + 1:03d}"
            })
        
        import time
        start_time = time.time()
        result_df = service.transform_transactions(large_data, "test-upload")
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert execution_time < 30  # 30 seconds threshold
        assert len(result_df) == 5000

    def test_error_handling_with_mixed_data(self, service):
        """Test error handling with mixed valid/invalid data."""
        mixed_data = [
            {
                "amount": 100.0,
                "timestamp": "2023-01-01T10:00:00Z",
                "account_id": "ACC001"
            },
            {
                "amount": "invalid",  # Invalid amount
                "timestamp": "2023-01-01T11:00:00Z",
                "account_id": "ACC002"
            },
            {
                "amount": 300.0,
                "timestamp": "invalid-date",  # Invalid timestamp
                "account_id": "ACC003"
            },
            {
                "amount": 400.0,
                "timestamp": "2023-01-01T13:00:00Z",
                "account_id": "ACC004"
            }
        ]
        
        result_df = service.transform_transactions(mixed_data, "test-upload")
        
        # Should keep only valid rows
        assert len(result_df) == 2
        valid_accounts = result_df['account_id'].tolist()
        assert 'ACC001' in valid_accounts
        assert 'ACC004' in valid_accounts 