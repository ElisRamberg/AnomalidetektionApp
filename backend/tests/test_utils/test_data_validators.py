"""Tests for data validator utilities."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

from app.utils.data_validators import (
    DataQualityValidator, 
    TransactionValidator, 
    SchemaValidator,
    DataStatisticsCalculator
)
from app.utils.exceptions import DataValidationError


class TestDataQualityValidator:
    """Test cases for DataQualityValidator utility."""

    @pytest.fixture
    def validator(self):
        """Create DataQualityValidator instance."""
        return DataQualityValidator()

    @pytest.fixture
    def sample_data(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            'amount': [100.50, -25.00, 200.00, np.nan, 0.0],
            'timestamp': [
                '2023-01-01T10:00:00Z',
                '2023-01-01T11:00:00Z', 
                '2023-01-01T12:00:00Z',
                '2023-01-01T13:00:00Z',
                '2023-01-01T14:00:00Z'
            ],
            'account_id': ['ACC001', 'ACC002', 'ACC003', '', 'ACC005'],
            'external_transaction_id': ['TXN001', 'TXN002', 'TXN003', 'TXN004', None]
        })

    def test_check_missing_values(self, validator, sample_data):
        """Test missing values detection."""
        result = validator.check_missing_values(sample_data)
        
        assert isinstance(result, dict)
        assert 'missing_counts' in result
        assert 'missing_percentages' in result
        assert 'columns_with_missing' in result
        
        # Should detect missing values in amount and external_transaction_id
        assert result['missing_counts']['amount'] == 1
        assert result['missing_counts']['external_transaction_id'] == 1
        assert 'amount' in result['columns_with_missing']

    def test_check_duplicate_records(self, validator):
        """Test duplicate records detection."""
        # Create data with duplicates
        data_with_duplicates = pd.DataFrame({
            'amount': [100.0, 100.0, 200.0],
            'timestamp': ['2023-01-01T10:00:00Z'] * 3,
            'account_id': ['ACC001', 'ACC001', 'ACC002']
        })
        
        result = validator.check_duplicate_records(data_with_duplicates)
        
        assert 'duplicate_count' in result
        assert 'duplicate_percentage' in result
        assert 'duplicate_rows' in result
        assert result['duplicate_count'] > 0

    def test_validate_data_types(self, validator, sample_data):
        """Test data type validation."""
        expected_types = {
            'amount': 'numeric',
            'timestamp': 'datetime',
            'account_id': 'string',
            'external_transaction_id': 'string'
        }
        
        result = validator.validate_data_types(sample_data, expected_types)
        
        assert 'type_compliance' in result
        assert 'type_issues' in result
        # Should have some issues due to missing values

    def test_check_outliers_numeric(self, validator):
        """Test outlier detection for numeric columns."""
        # Create data with clear outliers
        data = pd.DataFrame({
            'amount': [100, 110, 105, 95, 98, 1000]  # 1000 is clearly an outlier
        })
        
        result = validator.check_outliers_numeric(data, ['amount'])
        
        assert 'outliers_found' in result
        assert 'outlier_indices' in result
        assert len(result['outlier_indices']['amount']) > 0

    def test_validate_value_ranges(self, validator):
        """Test value range validation."""
        data = pd.DataFrame({
            'amount': [100, -50, 200, -1000],
            'score': [0.5, 1.2, 0.8, -0.1]  # 1.2 and -0.1 are out of range [0,1]
        })
        
        range_constraints = {
            'amount': {'min': -500, 'max': 1000},
            'score': {'min': 0, 'max': 1}
        }
        
        result = validator.validate_value_ranges(data, range_constraints)
        
        assert 'range_violations' in result
        assert 'violations_count' in result
        assert len(result['range_violations']['score']) == 2  # Two violations

    def test_check_data_consistency(self, validator):
        """Test data consistency validation."""
        # Create data with consistency issues
        data = pd.DataFrame({
            'debit_amount': [100, 0, 50],
            'credit_amount': [0, 200, 0],
            'transaction_type': ['debit', 'credit', 'debit']
        })
        
        consistency_rules = [
            {
                'name': 'debit_amount_consistency',
                'condition': lambda df: (df['transaction_type'] == 'debit') & (df['debit_amount'] > 0),
                'description': 'Debit transactions should have positive debit amounts'
            }
        ]
        
        result = validator.check_data_consistency(data, consistency_rules)
        
        assert 'consistency_issues' in result
        assert 'rules_passed' in result

    def test_validate_temporal_consistency(self, validator):
        """Test temporal consistency validation."""
        # Create data with temporal issues
        data = pd.DataFrame({
            'created_at': [
                datetime(2023, 1, 1, 10, 0),
                datetime(2023, 1, 1, 9, 0),   # Earlier than previous (issue)
                datetime(2023, 1, 1, 11, 0)
            ],
            'processed_at': [
                datetime(2023, 1, 1, 10, 5),
                datetime(2023, 1, 1, 9, 5),
                datetime(2023, 1, 1, 10, 5)   # Earlier than created_at (issue)
            ]
        })
        
        result = validator.validate_temporal_consistency(data)
        
        assert 'temporal_issues' in result
        assert 'inconsistent_sequences' in result

    def test_generate_quality_report(self, validator, sample_data):
        """Test comprehensive quality report generation."""
        report = validator.generate_quality_report(sample_data)
        
        assert isinstance(report, dict)
        assert 'summary' in report
        assert 'detailed_analysis' in report
        assert 'recommendations' in report
        assert 'quality_score' in report
        
        # Quality score should be between 0 and 1
        assert 0 <= report['quality_score'] <= 1

    def test_suggest_data_cleaning(self, validator, sample_data):
        """Test data cleaning suggestions."""
        suggestions = validator.suggest_data_cleaning(sample_data)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Should suggest cleaning for missing values
        missing_suggestions = [s for s in suggestions if 'missing' in s['issue'].lower()]
        assert len(missing_suggestions) > 0


class TestTransactionValidator:
    """Test cases for TransactionValidator utility."""

    @pytest.fixture
    def validator(self):
        """Create TransactionValidator instance."""
        return TransactionValidator()

    @pytest.fixture
    def sample_transactions(self):
        """Create sample transaction data."""
        return pd.DataFrame({
            'id': ['TXN001', 'TXN002', 'TXN003'],
            'amount': [100.50, -25.00, 0.0],
            'timestamp': [
                datetime(2023, 1, 1, 10, 0),
                datetime(2023, 1, 1, 11, 0),
                datetime(2023, 1, 1, 12, 0)
            ],
            'account_id': ['ACC001', 'ACC002', 'ACC003'],
            'external_transaction_id': ['EXT001', 'EXT002', 'EXT003']
        })

    def test_validate_transaction_ids(self, validator, sample_transactions):
        """Test transaction ID validation."""
        result = validator.validate_transaction_ids(sample_transactions)
        
        assert 'unique_ids' in result
        assert 'duplicate_ids' in result
        assert 'id_format_issues' in result
        assert result['unique_ids'] is True  # All IDs should be unique

    def test_validate_amounts(self, validator, sample_transactions):
        """Test amount validation."""
        result = validator.validate_amounts(sample_transactions)
        
        assert 'valid_amounts' in result
        assert 'zero_amounts' in result
        assert 'extreme_amounts' in result
        assert 'amount_distribution' in result

    def test_validate_timestamps(self, validator, sample_transactions):
        """Test timestamp validation."""
        result = validator.validate_timestamps(sample_transactions)
        
        assert 'valid_timestamps' in result
        assert 'chronological_order' in result
        assert 'timestamp_gaps' in result
        assert 'future_timestamps' in result

    def test_validate_account_ids(self, validator, sample_transactions):
        """Test account ID validation."""
        result = validator.validate_account_ids(sample_transactions)
        
        assert 'valid_format' in result
        assert 'unique_accounts' in result
        assert 'account_distribution' in result

    def test_detect_suspicious_patterns(self, validator):
        """Test suspicious pattern detection."""
        # Create suspicious patterns
        suspicious_data = pd.DataFrame({
            'id': [f'TXN{i:03d}' for i in range(10)],
            'amount': [100.0] * 10,  # All same amounts (suspicious)
            'timestamp': [datetime(2023, 1, 1, 10, i) for i in range(10)],
            'account_id': ['ACC001'] * 10  # All same account
        })
        
        result = validator.detect_suspicious_patterns(suspicious_data)
        
        assert 'suspicious_patterns' in result
        assert 'pattern_details' in result

    def test_validate_business_rules(self, validator, sample_transactions):
        """Test business rule validation."""
        business_rules = [
            {
                'name': 'positive_credit_amounts',
                'rule': lambda df: df['amount'] > 0,
                'severity': 'warning'
            }
        ]
        
        result = validator.validate_business_rules(sample_transactions, business_rules)
        
        assert 'rule_violations' in result
        assert 'compliance_score' in result

    def test_validate_transaction_completeness(self, validator):
        """Test transaction completeness validation."""
        # Create incomplete data
        incomplete_data = pd.DataFrame({
            'id': ['TXN001', 'TXN002'],
            'amount': [100.0, None],  # Missing amount
            'timestamp': [datetime(2023, 1, 1), datetime(2023, 1, 1)],
            'account_id': ['ACC001', '']  # Missing account ID
        })
        
        result = validator.validate_transaction_completeness(incomplete_data)
        
        assert 'completeness_score' in result
        assert 'missing_critical_fields' in result
        assert len(result['missing_critical_fields']) > 0

    def test_validate_cross_field_consistency(self, validator):
        """Test cross-field consistency validation."""
        # Create inconsistent data
        data = pd.DataFrame({
            'amount': [100, -50, 200],
            'transaction_type': ['credit', 'debit', 'credit'],
            'debit_flag': [False, True, False]
        })
        
        result = validator.validate_cross_field_consistency(data)
        
        assert 'consistency_issues' in result
        assert 'field_relationships' in result


class TestSchemaValidator:
    """Test cases for SchemaValidator utility."""

    @pytest.fixture
    def validator(self):
        """Create SchemaValidator instance."""
        return SchemaValidator()

    @pytest.fixture
    def sample_schema(self):
        """Create sample schema definition."""
        return {
            'required_fields': ['id', 'amount', 'timestamp', 'account_id'],
            'field_types': {
                'id': 'string',
                'amount': 'numeric',
                'timestamp': 'datetime',
                'account_id': 'string'
            },
            'field_constraints': {
                'amount': {'min': -1000000, 'max': 1000000},
                'account_id': {'pattern': r'^ACC\d{3}$'}
            },
            'optional_fields': ['external_transaction_id', 'description']
        }

    def test_validate_schema_compliance(self, validator, sample_schema):
        """Test schema compliance validation."""
        # Valid data
        valid_data = pd.DataFrame({
            'id': ['TXN001'],
            'amount': [100.50],
            'timestamp': [datetime(2023, 1, 1)],
            'account_id': ['ACC001']
        })
        
        result = validator.validate_schema_compliance(valid_data, sample_schema)
        
        assert 'compliant' in result
        assert 'violations' in result
        assert result['compliant'] is True

    def test_validate_required_fields(self, validator, sample_schema):
        """Test required fields validation."""
        # Missing required field
        incomplete_data = pd.DataFrame({
            'id': ['TXN001'],
            'amount': [100.50],
            'timestamp': [datetime(2023, 1, 1)]
            # Missing account_id
        })
        
        result = validator.validate_required_fields(incomplete_data, sample_schema)
        
        assert 'missing_required' in result
        assert 'account_id' in result['missing_required']

    def test_validate_field_types(self, validator, sample_schema):
        """Test field type validation."""
        # Wrong data types
        invalid_data = pd.DataFrame({
            'id': ['TXN001'],
            'amount': ['not_a_number'],  # Should be numeric
            'timestamp': [datetime(2023, 1, 1)],
            'account_id': ['ACC001']
        })
        
        result = validator.validate_field_types(invalid_data, sample_schema)
        
        assert 'type_violations' in result
        assert 'amount' in result['type_violations']

    def test_validate_field_constraints(self, validator, sample_schema):
        """Test field constraint validation."""
        # Violate constraints
        invalid_data = pd.DataFrame({
            'id': ['TXN001'],
            'amount': [2000000],  # Exceeds max constraint
            'timestamp': [datetime(2023, 1, 1)],
            'account_id': ['INVALID_FORMAT']  # Doesn't match pattern
        })
        
        result = validator.validate_field_constraints(invalid_data, sample_schema)
        
        assert 'constraint_violations' in result
        assert len(result['constraint_violations']) > 0

    def test_suggest_schema_improvements(self, validator, sample_schema):
        """Test schema improvement suggestions."""
        # Data that might suggest schema improvements
        data = pd.DataFrame({
            'id': ['TXN001', 'TXN002'],
            'amount': [100.50, -25.00],
            'timestamp': [datetime(2023, 1, 1), datetime(2023, 1, 2)],
            'account_id': ['ACC001', 'ACC002'],
            'new_field': ['value1', 'value2']  # Field not in schema
        })
        
        suggestions = validator.suggest_schema_improvements(data, sample_schema)
        
        assert isinstance(suggestions, list)
        # Should suggest adding new_field to schema

    def test_validate_schema_evolution(self, validator):
        """Test schema evolution validation."""
        old_schema = {
            'required_fields': ['id', 'amount'],
            'field_types': {'id': 'string', 'amount': 'numeric'}
        }
        
        new_schema = {
            'required_fields': ['id', 'amount', 'timestamp'],  # Added field
            'field_types': {
                'id': 'string', 
                'amount': 'numeric', 
                'timestamp': 'datetime'
            }
        }
        
        result = validator.validate_schema_evolution(old_schema, new_schema)
        
        assert 'evolution_type' in result
        assert 'compatibility' in result
        assert 'breaking_changes' in result


class TestDataStatisticsCalculator:
    """Test cases for DataStatisticsCalculator utility."""

    @pytest.fixture
    def calculator(self):
        """Create DataStatisticsCalculator instance."""
        return DataStatisticsCalculator()

    @pytest.fixture
    def sample_data(self):
        """Create sample data for statistics."""
        np.random.seed(42)
        return pd.DataFrame({
            'amount': np.random.normal(100, 20, 1000),
            'timestamp': pd.date_range('2023-01-01', periods=1000, freq='H'),
            'account_id': np.random.choice(['ACC001', 'ACC002', 'ACC003'], 1000),
            'category': np.random.choice(['A', 'B', 'C'], 1000)
        })

    def test_calculate_basic_statistics(self, calculator, sample_data):
        """Test basic statistics calculation."""
        stats = calculator.calculate_basic_statistics(sample_data)
        
        assert 'numeric_stats' in stats
        assert 'categorical_stats' in stats
        assert 'temporal_stats' in stats
        
        # Check numeric statistics
        assert 'amount' in stats['numeric_stats']
        amount_stats = stats['numeric_stats']['amount']
        assert all(key in amount_stats for key in ['mean', 'std', 'min', 'max', 'median'])

    def test_calculate_distribution_statistics(self, calculator, sample_data):
        """Test distribution statistics calculation."""
        stats = calculator.calculate_distribution_statistics(sample_data, ['amount'])
        
        assert 'distributions' in stats
        assert 'amount' in stats['distributions']
        
        amount_dist = stats['distributions']['amount']
        assert 'histogram' in amount_dist
        assert 'percentiles' in amount_dist
        assert 'skewness' in amount_dist
        assert 'kurtosis' in amount_dist

    def test_calculate_correlation_matrix(self, calculator, sample_data):
        """Test correlation matrix calculation."""
        # Add another numeric column for correlation
        sample_data['amount_squared'] = sample_data['amount'] ** 2
        
        corr_matrix = calculator.calculate_correlation_matrix(sample_data)
        
        assert isinstance(corr_matrix, pd.DataFrame)
        assert 'amount' in corr_matrix.columns
        assert 'amount_squared' in corr_matrix.columns

    def test_calculate_temporal_patterns(self, calculator, sample_data):
        """Test temporal pattern analysis."""
        patterns = calculator.calculate_temporal_patterns(sample_data, 'timestamp')
        
        assert 'hourly_patterns' in patterns
        assert 'daily_patterns' in patterns
        assert 'weekly_patterns' in patterns
        assert 'monthly_patterns' in patterns

    def test_calculate_categorical_distributions(self, calculator, sample_data):
        """Test categorical distribution analysis."""
        distributions = calculator.calculate_categorical_distributions(
            sample_data, ['account_id', 'category']
        )
        
        assert 'account_id' in distributions
        assert 'category' in distributions
        
        account_dist = distributions['account_id']
        assert 'value_counts' in account_dist
        assert 'percentages' in account_dist
        assert 'unique_count' in account_dist

    def test_detect_anomalies_statistical(self, calculator):
        """Test statistical anomaly detection."""
        # Create data with clear anomalies
        data = pd.DataFrame({
            'amount': [100] * 95 + [1000] * 5  # 5 clear outliers
        })
        
        anomalies = calculator.detect_anomalies_statistical(data, ['amount'])
        
        assert 'anomalies_found' in anomalies
        assert 'anomaly_indices' in anomalies
        assert len(anomalies['anomaly_indices']['amount']) > 0

    def test_calculate_data_quality_metrics(self, calculator, sample_data):
        """Test data quality metrics calculation."""
        # Introduce some quality issues
        sample_data.loc[0:10, 'amount'] = np.nan  # Missing values
        sample_data.loc[11:15, 'amount'] = sample_data.loc[11:15, 'amount']  # Duplicates
        
        metrics = calculator.calculate_data_quality_metrics(sample_data)
        
        assert 'completeness' in metrics
        assert 'uniqueness' in metrics
        assert 'validity' in metrics
        assert 'consistency' in metrics

    def test_generate_summary_report(self, calculator, sample_data):
        """Test summary report generation."""
        report = calculator.generate_summary_report(sample_data)
        
        assert 'dataset_overview' in report
        assert 'column_analysis' in report
        assert 'quality_assessment' in report
        assert 'recommendations' in report

    def test_compare_datasets(self, calculator, sample_data):
        """Test dataset comparison."""
        # Create a modified version of the data
        modified_data = sample_data.copy()
        modified_data['amount'] = modified_data['amount'] * 1.1  # Scale amounts
        
        comparison = calculator.compare_datasets(sample_data, modified_data)
        
        assert 'differences' in comparison
        assert 'statistical_differences' in comparison
        assert 'schema_differences' in comparison

    def test_performance_with_large_dataset(self, calculator):
        """Test performance with larger dataset."""
        # Create larger dataset
        large_data = pd.DataFrame({
            'amount': np.random.normal(100, 20, 50000),
            'timestamp': pd.date_range('2023-01-01', periods=50000, freq='T'),
            'account_id': np.random.choice([f'ACC{i:03d}' for i in range(100)], 50000)
        })
        
        import time
        start_time = time.time()
        stats = calculator.calculate_basic_statistics(large_data)
        calculation_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert calculation_time < 10.0  # 10 seconds threshold
        assert 'numeric_stats' in stats

    def test_memory_efficient_calculation(self, calculator):
        """Test memory-efficient calculation for large datasets."""
        # Create data that might stress memory
        large_data = pd.DataFrame({
            'amount': np.random.normal(100, 20, 100000),
            'category': np.random.choice(['A', 'B', 'C'], 100000)
        })
        
        # Should handle without memory errors
        stats = calculator.calculate_basic_statistics(large_data, memory_efficient=True)
        
        assert 'numeric_stats' in stats
        assert 'categorical_stats' in stats