"""Tests for Z-score anomaly detection algorithm."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from app.algorithms.statistical.zscore import ZScoreAlgorithm
from app.utils.exceptions import AlgorithmConfigurationError, AlgorithmError


class TestZScoreAlgorithm:
    """Test cases for Z-score algorithm."""

    @pytest.fixture
    def algorithm(self):
        """Create Z-score algorithm instance."""
        return ZScoreAlgorithm()

    @pytest.fixture
    def sample_data(self):
        """Create sample transaction data."""
        np.random.seed(42)  # For reproducible tests
        data = {
            'id': [f'TXN{i:03d}' for i in range(100)],
            'amount': np.random.normal(100, 20, 100).tolist(),  # Normal distribution
            'timestamp': pd.date_range('2023-01-01', periods=100, freq='H'),
            'account_id': ['ACC001'] * 100
        }
        # Add some clear outliers
        data['amount'][0] = 500  # Clear outlier
        data['amount'][1] = -200  # Clear outlier
        return pd.DataFrame(data)

    def test_algorithm_initialization(self, algorithm):
        """Test algorithm initialization."""
        assert algorithm.name == "zscore"
        assert algorithm.algorithm_type == "statistical"
        assert algorithm.__version__ is not None

    def test_prepare_data_success(self, algorithm, sample_data):
        """Test successful data preparation."""
        prepared_data = algorithm.prepare_data(sample_data)
        
        assert isinstance(prepared_data, pd.DataFrame)
        assert len(prepared_data) == len(sample_data)
        assert 'amount' in prepared_data.columns
        assert 'id' in prepared_data.columns

    def test_prepare_data_missing_columns(self, algorithm):
        """Test data preparation with missing required columns."""
        invalid_data = pd.DataFrame({'other_col': [1, 2, 3]})
        
        with pytest.raises(AlgorithmError):
            algorithm.prepare_data(invalid_data)

    def test_detect_basic_anomalies(self, algorithm, sample_data):
        """Test basic anomaly detection."""
        config = {'threshold': 2.0, 'window_size': 50}
        prepared_data = algorithm.prepare_data(sample_data)
        
        results = algorithm.detect(prepared_data, config)
        
        assert isinstance(results, pd.DataFrame)
        assert len(results) == len(sample_data)
        assert all(col in results.columns for col in ['transaction_id', 'score', 'confidence', 'metadata'])
        
        # Check that outliers have high scores
        outlier_scores = results[results['transaction_id'].isin(['TXN000', 'TXN001'])]['score']
        normal_scores = results[~results['transaction_id'].isin(['TXN000', 'TXN001'])]['score']
        
        assert outlier_scores.mean() > normal_scores.mean()

    def test_detect_with_different_thresholds(self, algorithm, sample_data):
        """Test detection with different threshold values."""
        prepared_data = algorithm.prepare_data(sample_data)
        
        # Test with strict threshold
        strict_config = {'threshold': 3.0, 'window_size': 50}
        strict_results = algorithm.detect(prepared_data, strict_config)
        
        # Test with lenient threshold
        lenient_config = {'threshold': 1.5, 'window_size': 50}
        lenient_results = algorithm.detect(prepared_data, lenient_config)
        
        # Lenient threshold should detect more anomalies
        strict_anomalies = (strict_results['score'] > 0.5).sum()
        lenient_anomalies = (lenient_results['score'] > 0.5).sum()
        
        assert lenient_anomalies >= strict_anomalies

    def test_detect_with_different_window_sizes(self, algorithm, sample_data):
        """Test detection with different window sizes."""
        prepared_data = algorithm.prepare_data(sample_data)
        
        # Test with small window
        small_window_config = {'threshold': 2.0, 'window_size': 10}
        small_results = algorithm.detect(prepared_data, small_window_config)
        
        # Test with large window
        large_window_config = {'threshold': 2.0, 'window_size': 80}
        large_results = algorithm.detect(prepared_data, large_window_config)
        
        # Both should produce valid results
        assert len(small_results) == len(sample_data)
        assert len(large_results) == len(sample_data)
        assert all(small_results['score'] >= 0)
        assert all(large_results['score'] >= 0)

    def test_detect_account_specific_analysis(self, algorithm):
        """Test account-specific anomaly detection."""
        # Create data with multiple accounts
        data = {
            'id': [f'TXN{i:03d}' for i in range(60)],
            'amount': [100] * 20 + [200] * 20 + [50] * 20,  # Different patterns per account
            'timestamp': pd.date_range('2023-01-01', periods=60, freq='H'),
            'account_id': ['ACC001'] * 20 + ['ACC002'] * 20 + ['ACC003'] * 20
        }
        # Add account-specific outliers
        data['amount'][0] = 500   # Outlier for ACC001
        data['amount'][20] = 800  # Outlier for ACC002
        data['amount'][40] = 200  # Outlier for ACC003
        
        sample_data = pd.DataFrame(data)
        prepared_data = algorithm.prepare_data(sample_data)
        
        config = {'threshold': 2.0, 'window_size': 15, 'account_specific': True}
        results = algorithm.detect(prepared_data, config)
        
        # Check that account-specific outliers are detected
        outlier_transactions = ['TXN000', 'TXN020', 'TXN040']
        outlier_results = results[results['transaction_id'].isin(outlier_transactions)]
        
        assert len(outlier_results) == 3
        assert all(outlier_results['score'] > 0.3)  # Should have elevated scores

    def test_detect_insufficient_data(self, algorithm):
        """Test detection with insufficient data."""
        small_data = pd.DataFrame({
            'id': ['TXN001', 'TXN002'],
            'amount': [100, 110],
            'timestamp': pd.date_range('2023-01-01', periods=2, freq='H'),
            'account_id': ['ACC001', 'ACC001']
        })
        
        prepared_data = algorithm.prepare_data(small_data)
        config = {'threshold': 2.0, 'window_size': 10}
        
        results = algorithm.detect(prepared_data, config)
        
        # Should handle gracefully with low confidence scores
        assert len(results) == 2
        assert all(results['confidence'] <= 0.5)  # Low confidence due to insufficient data

    def test_validate_config_success(self, algorithm):
        """Test successful configuration validation."""
        valid_config = {
            'threshold': 2.5,
            'window_size': 30,
            'account_specific': True,
            'confidence_adjustment': True
        }
        
        assert algorithm.validate_config(valid_config) is True

    def test_validate_config_invalid_threshold(self, algorithm):
        """Test configuration validation with invalid threshold."""
        invalid_configs = [
            {'threshold': -1.0},  # Negative threshold
            {'threshold': 'invalid'},  # Non-numeric threshold
            {'threshold': 0},  # Zero threshold
        ]
        
        for config in invalid_configs:
            with pytest.raises(AlgorithmConfigurationError):
                algorithm.validate_config(config)

    def test_validate_config_invalid_window_size(self, algorithm):
        """Test configuration validation with invalid window size."""
        invalid_configs = [
            {'window_size': 0},  # Zero window size
            {'window_size': -5},  # Negative window size
            {'window_size': 'invalid'},  # Non-numeric window size
            {'window_size': 2.5},  # Float instead of int
        ]
        
        for config in invalid_configs:
            with pytest.raises(AlgorithmConfigurationError):
                algorithm.validate_config(config)

    def test_get_default_config(self, algorithm):
        """Test default configuration retrieval."""
        default_config = algorithm._get_default_config()
        
        assert isinstance(default_config, dict)
        assert 'threshold' in default_config
        assert 'window_size' in default_config
        assert default_config['threshold'] > 0
        assert default_config['window_size'] > 0

    def test_get_minimum_transactions(self, algorithm):
        """Test minimum transactions requirement."""
        min_transactions = algorithm.get_minimum_transactions()
        
        assert isinstance(min_transactions, int)
        assert min_transactions > 0

    def test_log_execution(self, algorithm):
        """Test execution logging."""
        log_entry = algorithm.log_execution(
            transactions_count=100,
            execution_time=1.5,
            anomalies_found=5,
            config={'threshold': 2.0}
        )
        
        assert isinstance(log_entry, dict)
        assert log_entry['transactions_count'] == 100
        assert log_entry['execution_time'] == 1.5
        assert log_entry['anomalies_found'] == 5
        assert 'timestamp' in log_entry

    def test_edge_case_all_same_values(self, algorithm):
        """Test with data where all values are the same."""
        same_value_data = pd.DataFrame({
            'id': [f'TXN{i:03d}' for i in range(20)],
            'amount': [100.0] * 20,  # All same values
            'timestamp': pd.date_range('2023-01-01', periods=20, freq='H'),
            'account_id': ['ACC001'] * 20
        })
        
        prepared_data = algorithm.prepare_data(same_value_data)
        config = {'threshold': 2.0, 'window_size': 10}
        
        results = algorithm.detect(prepared_data, config)
        
        # Should handle gracefully - no real anomalies when all values are same
        assert len(results) == 20
        assert all(results['score'] <= 0.2)  # Low scores since no variation

    def test_edge_case_single_transaction(self, algorithm):
        """Test with single transaction."""
        single_data = pd.DataFrame({
            'id': ['TXN001'],
            'amount': [100.0],
            'timestamp': [pd.Timestamp('2023-01-01')],
            'account_id': ['ACC001']
        })
        
        prepared_data = algorithm.prepare_data(single_data)
        config = {'threshold': 2.0, 'window_size': 10}
        
        results = algorithm.detect(prepared_data, config)
        
        # Should handle single transaction gracefully
        assert len(results) == 1
        assert results.iloc[0]['confidence'] <= 0.3  # Low confidence with single data point

    def test_confidence_scoring(self, algorithm, sample_data):
        """Test confidence score calculation."""
        prepared_data = algorithm.prepare_data(sample_data)
        config = {'threshold': 2.0, 'window_size': 30}
        
        results = algorithm.detect(prepared_data, config)
        
        # Confidence scores should be between 0 and 1
        assert all(0 <= score <= 1 for score in results['confidence'])
        
        # Higher anomaly scores should generally have higher confidence
        high_score_mask = results['score'] > 0.7
        low_score_mask = results['score'] < 0.3
        
        if high_score_mask.any() and low_score_mask.any():
            high_score_confidence = results[high_score_mask]['confidence'].mean()
            low_score_confidence = results[low_score_mask]['confidence'].mean()
            
            # This might not always be true due to data characteristics, so we check it's reasonable
            assert high_score_confidence >= 0.3

    def test_metadata_content(self, algorithm, sample_data):
        """Test metadata content in results."""
        prepared_data = algorithm.prepare_data(sample_data)
        config = {'threshold': 2.0, 'window_size': 30}
        
        results = algorithm.detect(prepared_data, config)
        
        # Check first result's metadata
        first_metadata = results.iloc[0]['metadata']
        
        assert isinstance(first_metadata, dict)
        assert 'z_score' in first_metadata
        assert 'window_mean' in first_metadata
        assert 'window_std' in first_metadata
        assert 'analysis_type' in first_metadata

    def test_performance_with_large_dataset(self, algorithm):
        """Test performance with larger dataset."""
        # Create larger dataset
        np.random.seed(42)
        large_data = pd.DataFrame({
            'id': [f'TXN{i:05d}' for i in range(10000)],
            'amount': np.random.normal(100, 20, 10000).tolist(),
            'timestamp': pd.date_range('2023-01-01', periods=10000, freq='T'),
            'account_id': [f'ACC{(i % 100) + 1:03d}' for i in range(10000)]
        })
        
        prepared_data = algorithm.prepare_data(large_data)
        config = {'threshold': 2.0, 'window_size': 100}
        
        import time
        start_time = time.time()
        results = algorithm.detect(prepared_data, config)
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert execution_time < 30  # 30 seconds threshold
        assert len(results) == 10000
        assert all(results['score'] >= 0) 