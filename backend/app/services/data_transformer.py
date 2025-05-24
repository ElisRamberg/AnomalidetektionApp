"""Data transformation service for preprocessing transaction data."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid
import re

from ..utils.exceptions import DataTransformationError
from ..utils.data_validators import DataValidator
from ..config import get_settings

settings = get_settings()


class DataTransformerService:
    """Service for transforming and enriching transaction data."""
    
    def __init__(self):
        self.data_validator = DataValidator()
    
    def transform_transactions(self, raw_transactions: List[Dict[str, Any]], 
                             upload_id: str) -> pd.DataFrame:
        """
        Transform raw transaction dictionaries into standardized DataFrame.
        
        Args:
            raw_transactions: List of raw transaction dictionaries
            upload_id: ID of the upload these transactions belong to
            
        Returns:
            Standardized and enriched transaction DataFrame
            
        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(raw_transactions)
            
            if df.empty:
                raise DataTransformationError("No transactions to transform")
            
            # Step 1: Generate transaction IDs if missing
            df = self._ensure_transaction_ids(df)
            
            # Step 2: Standardize column names
            df = self._standardize_columns(df)
            
            # Step 3: Validate and clean required fields
            df = self._validate_required_fields(df)
            
            # Step 4: Parse and standardize timestamps
            df = self._standardize_timestamps(df)
            
            # Step 5: Clean and validate amounts
            df = self._clean_amounts(df)
            
            # Step 6: Standardize account IDs
            df = self._standardize_account_ids(df)
            
            # Step 7: Add derived fields
            df = self._add_derived_fields(df)
            
            # Step 8: Add metadata
            df = self._add_metadata(df, upload_id)
            
            # Step 9: Final validation
            df = self._final_validation(df)
            
            return df
            
        except Exception as e:
            raise DataTransformationError(f"Data transformation failed: {str(e)}")
    
    def _ensure_transaction_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all transactions have unique IDs."""
        if 'id' not in df.columns or df['id'].isnull().any():
            # Generate UUIDs for missing IDs
            df['id'] = df.apply(
                lambda row: str(uuid.uuid4()) if pd.isnull(row.get('id')) else row.get('id'),
                axis=1
            )
        
        # Ensure IDs are unique
        if df['id'].duplicated().any():
            duplicate_count = df['id'].duplicated().sum()
            # Generate new IDs for duplicates
            mask = df['id'].duplicated(keep='first')
            df.loc[mask, 'id'] = [str(uuid.uuid4()) for _ in range(mask.sum())]
        
        return df
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names to expected format."""
        # Common column name mappings
        column_mappings = {
            # Amount variations
            'amount': 'amount',
            'value': 'amount',
            'sum': 'amount',
            'transaction_amount': 'amount',
            'belopp': 'amount',  # Swedish
            
            # Timestamp variations
            'timestamp': 'timestamp',
            'date': 'timestamp',
            'transaction_date': 'timestamp',
            'datum': 'timestamp',  # Swedish
            'time': 'timestamp',
            'created_at': 'timestamp',
            
            # Account ID variations
            'account_id': 'account_id',
            'account': 'account_id',
            'konto': 'account_id',  # Swedish
            'account_number': 'account_id',
            'kontonummer': 'account_id',  # Swedish
            
            # External transaction ID variations
            'external_transaction_id': 'external_transaction_id',
            'external_id': 'external_transaction_id',
            'transaction_id': 'external_transaction_id',
            'reference': 'external_transaction_id',
            'referens': 'external_transaction_id',  # Swedish
        }
        
        # Apply case-insensitive mapping
        df_columns_lower = {col.lower(): col for col in df.columns}
        rename_dict = {}
        
        for mapping_key, standard_name in column_mappings.items():
            if mapping_key.lower() in df_columns_lower:
                original_col = df_columns_lower[mapping_key.lower()]
                if original_col != standard_name:
                    rename_dict[original_col] = standard_name
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        return df
    
    def _validate_required_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean required fields."""
        required_fields = ['amount', 'timestamp', 'account_id']
        
        # Check for required fields
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            raise DataTransformationError(f"Missing required fields: {missing_fields}")
        
        # Remove rows with null values in required fields
        initial_count = len(df)
        df = df.dropna(subset=required_fields)
        dropped_count = initial_count - len(df)
        
        if dropped_count > 0:
            print(f"Dropped {dropped_count} rows with missing required fields")
        
        if df.empty:
            raise DataTransformationError("No valid transactions after cleaning required fields")
        
        return df
    
    def _standardize_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse and standardize timestamp values."""
        try:
            # Try to parse timestamps with various formats
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', infer_datetime_format=True)
            
            # Handle any remaining unparseable timestamps
            null_timestamps = df['timestamp'].isnull()
            if null_timestamps.any():
                print(f"Warning: {null_timestamps.sum()} timestamps could not be parsed")
                # For now, drop these rows - could be enhanced to use row number or file timestamp
                df = df[~null_timestamps]
            
            # Ensure timezone awareness (assume UTC if naive)
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            else:
                df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')
            
            return df
            
        except Exception as e:
            raise DataTransformationError(f"Timestamp standardization failed: {str(e)}")
    
    def _clean_amounts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate transaction amounts."""
        try:
            # Handle string amounts (remove currency symbols, commas, etc.)
            if df['amount'].dtype == 'object':
                # Remove common currency symbols and formatting
                df['amount'] = df['amount'].astype(str).str.replace(r'[€$£¥₹,\s]', '', regex=True)
                # Handle comma as decimal separator (common in Europe)
                df['amount'] = df['amount'].str.replace(',', '.')
            
            # Convert to numeric
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            # Remove rows with invalid amounts
            null_amounts = df['amount'].isnull()
            if null_amounts.any():
                print(f"Warning: {null_amounts.sum()} invalid amounts found and will be dropped")
                df = df[~null_amounts]
            
            # Validate amount ranges (optional - could be configurable)
            if settings.max_transaction_amount:
                large_amounts = df['amount'].abs() > settings.max_transaction_amount
                if large_amounts.any():
                    print(f"Warning: {large_amounts.sum()} transactions exceed maximum amount threshold")
            
            return df
            
        except Exception as e:
            raise DataTransformationError(f"Amount cleaning failed: {str(e)}")
    
    def _standardize_account_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize account ID format."""
        try:
            # Convert to string and clean
            df['account_id'] = df['account_id'].astype(str).str.strip()
            
            # Remove any leading/trailing whitespace and normalize
            df['account_id'] = df['account_id'].str.upper()
            
            # Validate account ID format (basic validation)
            invalid_accounts = df['account_id'].isin(['', 'NAN', 'NONE', 'NULL'])
            if invalid_accounts.any():
                print(f"Warning: {invalid_accounts.sum()} invalid account IDs found")
                df = df[~invalid_accounts]
            
            return df
            
        except Exception as e:
            raise DataTransformationError(f"Account ID standardization failed: {str(e)}")
    
    def _add_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived fields for analysis."""
        try:
            # Time-based features
            df['year'] = df['timestamp'].dt.year
            df['month'] = df['timestamp'].dt.month
            df['day'] = df['timestamp'].dt.day
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
            df['is_weekend'] = df['day_of_week'].isin([5, 6])
            df['is_business_hours'] = df['hour'].between(9, 17)
            
            # Amount-based features
            df['amount_abs'] = df['amount'].abs()
            df['is_debit'] = df['amount'] < 0
            df['is_credit'] = df['amount'] > 0
            
            # Add amount categories for analysis
            df['amount_category'] = pd.cut(
                df['amount_abs'],
                bins=[0, 100, 1000, 10000, 100000, float('inf')],
                labels=['micro', 'small', 'medium', 'large', 'huge'],
                include_lowest=True
            )
            
            # Transaction sequence features (per account)
            df = df.sort_values(['account_id', 'timestamp'])
            df['transaction_sequence'] = df.groupby('account_id').cumcount() + 1
            
            # Time differences between transactions (per account)
            df['time_since_prev'] = df.groupby('account_id')['timestamp'].diff()
            df['time_since_prev_hours'] = df['time_since_prev'].dt.total_seconds() / 3600
            
            return df
            
        except Exception as e:
            raise DataTransformationError(f"Derived field creation failed: {str(e)}")
    
    def _add_metadata(self, df: pd.DataFrame, upload_id: str) -> pd.DataFrame:
        """Add metadata fields."""
        try:
            df['upload_id'] = upload_id
            df['processed_at'] = datetime.utcnow()
            
            # Store original raw data as JSON for reference
            if '_source_file' in df.columns:
                df['raw_data'] = df.apply(
                    lambda row: {
                        'source_file': row.get('_source_file'),
                        'row_number': row.get('_row_number'),
                        'original_data': {k: v for k, v in row.items() 
                                        if not k.startswith('_') and k not in ['raw_data']}
                    },
                    axis=1
                )
            else:
                df['raw_data'] = df.apply(
                    lambda row: {
                        'original_data': {k: v for k, v in row.items() 
                                        if k not in ['raw_data']}
                    },
                    axis=1
                )
            
            return df
            
        except Exception as e:
            raise DataTransformationError(f"Metadata addition failed: {str(e)}")
    
    def _final_validation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Perform final validation on transformed data."""
        try:
            # Ensure required columns are present
            required_columns = [
                'id', 'amount', 'timestamp', 'account_id', 'upload_id', 'raw_data'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise DataTransformationError(f"Missing required columns after transformation: {missing_columns}")
            
            # Validate data types
            if not pd.api.types.is_numeric_dtype(df['amount']):
                raise DataTransformationError("Amount column is not numeric")
            
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                raise DataTransformationError("Timestamp column is not datetime")
            
            # Check for duplicates
            if df['id'].duplicated().any():
                raise DataTransformationError("Duplicate transaction IDs found")
            
            # Sort by timestamp for consistency
            df = df.sort_values('timestamp')
            
            return df
            
        except Exception as e:
            raise DataTransformationError(f"Final validation failed: {str(e)}")
    
    def get_transformation_stats(self, original_count: int, final_df: pd.DataFrame) -> Dict[str, Any]:
        """Get statistics about the transformation process."""
        return {
            'original_count': original_count,
            'final_count': len(final_df),
            'dropped_count': original_count - len(final_df),
            'drop_rate': (original_count - len(final_df)) / original_count if original_count > 0 else 0,
            'date_range': {
                'start': final_df['timestamp'].min().isoformat() if not final_df.empty else None,
                'end': final_df['timestamp'].max().isoformat() if not final_df.empty else None
            },
            'amount_stats': {
                'min': float(final_df['amount'].min()) if not final_df.empty else None,
                'max': float(final_df['amount'].max()) if not final_df.empty else None,
                'mean': float(final_df['amount'].mean()) if not final_df.empty else None,
                'total': float(final_df['amount'].sum()) if not final_df.empty else None
            },
            'account_count': final_df['account_id'].nunique() if not final_df.empty else 0,
            'features_added': [
                'year', 'month', 'day', 'hour', 'day_of_week', 'is_weekend',
                'is_business_hours', 'amount_abs', 'is_debit', 'is_credit',
                'amount_category', 'transaction_sequence', 'time_since_prev_hours'
            ]
        } 