"""Correlation analysis algorithm for detecting anomalous transaction relationships."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from scipy import stats
from ..base import StatisticalAlgorithm
from ...utils.exceptions import AlgorithmError, AlgorithmConfigurationError


class CorrelationAnalysisAlgorithm(StatisticalAlgorithm):
    """
    Detects anomalies based on correlations between transaction features.
    
    This algorithm identifies transactions that deviate from normal correlation
    patterns, such as unusual amount-time relationships or account behavior patterns.
    """
    
    __version__ = "1.0.0"
    
    def __init__(self):
        super().__init__("correlation")
    
    def detect(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Detect anomalies based on correlation analysis.
        
        Args:
            transactions: Prepared transaction DataFrame
            config: Algorithm configuration
            
        Returns:
            DataFrame with transaction_id, score, confidence, metadata
        """
        # Extract configuration parameters
        correlation_threshold = config.get('correlation_threshold', 0.3)
        window_size = config.get('window_size', 100)
        features = config.get('features', ['amount', 'hour', 'day_of_week'])
        correlation_type = config.get('correlation_type', 'pearson')
        
        results = []
        
        # Ensure required features exist
        available_features = [f for f in features if f in transactions.columns]
        if len(available_features) < 2:
            raise AlgorithmError(f"Insufficient features for correlation analysis. Available: {available_features}")
        
        # Group by account for account-specific correlation analysis
        for account_id in transactions['account_id'].unique():
            account_transactions = transactions[transactions['account_id'] == account_id].copy()
            
            if len(account_transactions) < window_size // 2:
                # For accounts with insufficient data, assign low anomaly scores
                for _, transaction in account_transactions.iterrows():
                    results.append({
                        'transaction_id': transaction['id'],
                        'score': 0.1,
                        'confidence': 0.3,
                        'metadata': {
                            'reason': 'insufficient_data_for_correlation',
                            'transaction_count': len(account_transactions)
                        }
                    })
                continue
            
            # Calculate correlation-based anomaly scores
            account_results = self._analyze_account_correlations(
                account_transactions, available_features, config
            )
            results.extend(account_results)
        
        return self.create_result_dataframe(
            [r['transaction_id'] for r in results],
            [r['score'] for r in results],
            [r['confidence'] for r in results],
            [r['metadata'] for r in results]
        )
    
    def _analyze_account_correlations(self, transactions: pd.DataFrame, 
                                    features: List[str], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze correlations for a specific account."""
        correlation_threshold = config.get('correlation_threshold', 0.3)
        window_size = config.get('window_size', 100)
        correlation_type = config.get('correlation_type', 'pearson')
        
        results = []
        
        # Sort by timestamp
        transactions = transactions.sort_values('timestamp').reset_index(drop=True)
        
        # Calculate rolling correlation matrix
        for i, transaction in transactions.iterrows():
            # Define window around current transaction
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(transactions), i + window_size // 2 + 1)
            window_data = transactions.iloc[start_idx:end_idx]
            
            if len(window_data) < 10:  # Minimum window size
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.2,
                    'metadata': {
                        'reason': 'insufficient_window_data',
                        'window_size': len(window_data)
                    }
                })
                continue
            
            # Calculate anomaly score based on correlation deviations
            score, confidence, metadata = self._calculate_correlation_score(
                transaction, window_data, features, config
            )
            
            results.append({
                'transaction_id': transaction['id'],
                'score': score,
                'confidence': confidence,
                'metadata': metadata
            })
        
        return results
    
    def _calculate_correlation_score(self, transaction: pd.Series, window_data: pd.DataFrame,
                                   features: List[str], config: Dict[str, Any]) -> tuple:
        """Calculate correlation-based anomaly score for a transaction."""
        correlation_type = config.get('correlation_type', 'pearson')
        correlation_threshold = config.get('correlation_threshold', 0.3)
        
        try:
            # Extract feature values for the current transaction
            transaction_features = transaction[features].values
            
            # Calculate correlation matrix for the window
            if correlation_type == 'pearson':
                corr_matrix = window_data[features].corr(method='pearson')
            elif correlation_type == 'spearman':
                corr_matrix = window_data[features].corr(method='spearman')
            else:
                corr_matrix = window_data[features].corr(method='kendall')
            
            # Calculate expected vs actual feature relationships
            anomaly_indicators = []
            correlation_details = {}
            
            for i, feature1 in enumerate(features):
                for j, feature2 in enumerate(features):
                    if i >= j:  # Avoid duplicate pairs and self-correlation
                        continue
                    
                    expected_corr = corr_matrix.loc[feature1, feature2]
                    
                    if pd.isna(expected_corr):
                        continue
                    
                    # Calculate actual correlation for this transaction relative to window
                    feature1_values = window_data[feature1].values
                    feature2_values = window_data[feature2].values
                    
                    # Find transaction's position in the correlation space
                    transaction_f1 = transaction[feature1]
                    transaction_f2 = transaction[feature2]
                    
                    # Calculate how well this transaction fits the expected correlation
                    if abs(expected_corr) > correlation_threshold:
                        # For strongly correlated features, check if transaction follows pattern
                        predicted_f2 = self._predict_feature_value(
                            feature1_values, feature2_values, transaction_f1
                        )
                        
                        if predicted_f2 is not None:
                            prediction_error = abs(transaction_f2 - predicted_f2)
                            normalized_error = prediction_error / (np.std(feature2_values) + 1e-6)
                            anomaly_indicators.append(normalized_error)
                            
                            correlation_details[f"{feature1}_{feature2}"] = {
                                'expected_correlation': float(expected_corr),
                                'predicted_value': float(predicted_f2),
                                'actual_value': float(transaction_f2),
                                'prediction_error': float(prediction_error),
                                'normalized_error': float(normalized_error)
                            }
            
            if not anomaly_indicators:
                return 0.1, 0.2, {'reason': 'no_significant_correlations'}
            
            # Aggregate anomaly indicators
            mean_anomaly = np.mean(anomaly_indicators)
            max_anomaly = np.max(anomaly_indicators)
            
            # Convert to anomaly score (0-1 scale)
            score = min(1.0, max(0.0, (mean_anomaly + max_anomaly) / 4))
            
            # Calculate confidence based on correlation strength and data quality
            correlation_strengths = [abs(corr_matrix.loc[f1, f2]) 
                                   for i, f1 in enumerate(features) 
                                   for j, f2 in enumerate(features) 
                                   if i < j and not pd.isna(corr_matrix.loc[f1, f2])]
            
            avg_correlation_strength = np.mean(correlation_strengths) if correlation_strengths else 0
            confidence = min(1.0, avg_correlation_strength + 0.3)
            
            metadata = {
                'correlation_analysis': correlation_details,
                'anomaly_indicators': len(anomaly_indicators),
                'mean_anomaly_score': float(mean_anomaly),
                'max_anomaly_score': float(max_anomaly),
                'average_correlation_strength': float(avg_correlation_strength),
                'features_analyzed': features
            }
            
            return score, confidence, metadata
            
        except Exception as e:
            return 0.0, 0.1, {'error': str(e), 'reason': 'calculation_failed'}
    
    def _predict_feature_value(self, x_values: np.ndarray, y_values: np.ndarray, 
                             x_target: float) -> float:
        """Predict feature value based on linear relationship."""
        try:
            # Simple linear regression prediction
            if len(x_values) < 3:
                return None
            
            # Remove any NaN values
            mask = ~(np.isnan(x_values) | np.isnan(y_values))
            x_clean = x_values[mask]
            y_clean = y_values[mask]
            
            if len(x_clean) < 3:
                return None
            
            # Calculate linear regression coefficients
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)
            
            # Predict target value
            predicted = slope * x_target + intercept
            
            return predicted
            
        except Exception:
            return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate algorithm configuration."""
        required_keys = []  # No required keys for this algorithm
        
        # Check correlation_threshold
        if 'correlation_threshold' in config:
            threshold = config['correlation_threshold']
            if not isinstance(threshold, (int, float)):
                raise AlgorithmConfigurationError("correlation_threshold must be a number")
            if not 0 <= threshold <= 1:
                raise AlgorithmConfigurationError("correlation_threshold must be between 0 and 1")
        
        # Check window_size
        if 'window_size' in config:
            window_size = config['window_size']
            if not isinstance(window_size, int):
                raise AlgorithmConfigurationError("window_size must be an integer")
            if window_size < 10:
                raise AlgorithmConfigurationError("window_size must be at least 10")
        
        # Check correlation_type
        if 'correlation_type' in config:
            corr_type = config['correlation_type']
            valid_types = ['pearson', 'spearman', 'kendall']
            if corr_type not in valid_types:
                raise AlgorithmConfigurationError(f"correlation_type must be one of: {valid_types}")
        
        # Check features
        if 'features' in config:
            features = config['features']
            if not isinstance(features, list):
                raise AlgorithmConfigurationError("features must be a list")
            if len(features) < 2:
                raise AlgorithmConfigurationError("At least 2 features required for correlation analysis")
        
        return True
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'correlation_threshold': 0.3,
            'window_size': 100,
            'features': ['amount', 'hour', 'day_of_week'],
            'correlation_type': 'pearson'
        }
    
    def get_minimum_transactions(self) -> int:
        """Minimum number of transactions required."""
        return 20  # Need enough data for meaningful correlation analysis 