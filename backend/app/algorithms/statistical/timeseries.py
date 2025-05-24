"""Time series anomaly detection algorithm for temporal patterns."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from ..base import StatisticalAlgorithm
from ...utils.exceptions import AlgorithmError, AlgorithmConfigurationError


class TimeSeriesAnomalyAlgorithm(StatisticalAlgorithm):
    """
    Detects anomalies in time series patterns of transactions.
    
    This algorithm identifies unusual temporal patterns such as:
    - Sudden spikes or drops in transaction frequency
    - Unusual transaction amounts for specific time periods
    - Deviations from seasonal patterns
    - Irregular transaction timing
    """
    
    __version__ = "1.0.0"
    
    def __init__(self):
        super().__init__("timeseries")
    
    def detect(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Detect time series anomalies in transaction data.
        
        Args:
            transactions: Prepared transaction DataFrame
            config: Algorithm configuration
            
        Returns:
            DataFrame with transaction_id, score, confidence, metadata
        """
        # Extract configuration parameters
        time_window = config.get('time_window', 'hour')  # hour, day, week
        aggregation_method = config.get('aggregation_method', 'count')  # count, sum, mean
        threshold_method = config.get('threshold_method', 'std')  # std, iqr, percentile
        threshold_multiplier = config.get('threshold_multiplier', 2.0)
        seasonal_adjustment = config.get('seasonal_adjustment', True)
        min_periods = config.get('min_periods', 10)
        
        results = []
        
        # Ensure timestamp column is datetime
        if not pd.api.types.is_datetime64_any_dtype(transactions['timestamp']):
            transactions['timestamp'] = pd.to_datetime(transactions['timestamp'])
        
        # Sort by timestamp
        transactions = transactions.sort_values('timestamp').reset_index(drop=True)
        
        # Create time series features
        transactions = self._add_time_features(transactions)
        
        # Analyze time series patterns for the entire dataset
        global_results = self._analyze_global_patterns(transactions, config)
        
        # Analyze per-account patterns
        account_results = self._analyze_account_patterns(transactions, config)
        
        # Combine results
        results.extend(global_results)
        results.extend(account_results)
        
        # Remove duplicates (transactions may appear in both global and account analysis)
        seen_transactions = set()
        unique_results = []
        
        for result in results:
            transaction_id = result['transaction_id']
            if transaction_id not in seen_transactions:
                seen_transactions.add(transaction_id)
                unique_results.append(result)
            else:
                # Combine scores if transaction appears multiple times
                for existing_result in unique_results:
                    if existing_result['transaction_id'] == transaction_id:
                        # Take maximum score
                        if result['score'] > existing_result['score']:
                            existing_result['score'] = result['score']
                            existing_result['confidence'] = max(
                                existing_result['confidence'], result['confidence']
                            )
                            # Merge metadata
                            existing_result['metadata'].update(result['metadata'])
                        break
        
        return self.create_result_dataframe(
            [r['transaction_id'] for r in unique_results],
            [r['score'] for r in unique_results],
            [r['confidence'] for r in unique_results],
            [r['metadata'] for r in unique_results]
        )
    
    def _add_time_features(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features for analysis."""
        df = transactions.copy()
        
        # Extract time components
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month
        df['day'] = df['timestamp'].dt.day
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['week_of_year'] = df['timestamp'].dt.isocalendar().week
        
        # Create time period identifiers
        df['date'] = df['timestamp'].dt.date
        df['hour_period'] = df['timestamp'].dt.floor('H')
        df['day_period'] = df['timestamp'].dt.floor('D')
        df['week_period'] = df['timestamp'].dt.to_period('W')
        
        return df
    
    def _analyze_global_patterns(self, transactions: pd.DataFrame, 
                               config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze global time series patterns across all transactions."""
        time_window = config.get('time_window', 'hour')
        aggregation_method = config.get('aggregation_method', 'count')
        
        results = []
        
        # Create time series based on configuration
        time_series = self._create_time_series(transactions, time_window, aggregation_method)
        
        if len(time_series) < config.get('min_periods', 10):
            # Insufficient data for time series analysis
            for _, transaction in transactions.iterrows():
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.2,
                    'metadata': {
                        'analysis_type': 'global_timeseries',
                        'reason': 'insufficient_time_periods',
                        'periods_available': len(time_series)
                    }
                })
            return results
        
        # Detect anomalies in the time series
        anomalous_periods = self._detect_anomalous_periods(time_series, config)
        
        # Map anomalous periods back to individual transactions
        for _, transaction in transactions.iterrows():
            period_key = self._get_period_key(transaction, time_window)
            
            if period_key in anomalous_periods:
                anomaly_info = anomalous_periods[period_key]
                score = anomaly_info['score']
                confidence = anomaly_info['confidence']
                
                # Adjust score based on transaction's contribution to the anomaly
                if aggregation_method in ['sum', 'mean'] and 'amount' in transaction:
                    period_total = anomaly_info.get('period_value', 0)
                    transaction_contribution = abs(transaction['amount']) / (period_total + 1e-6)
                    score = score * (0.5 + 0.5 * transaction_contribution)
                
                results.append({
                    'transaction_id': transaction['id'],
                    'score': min(1.0, score),
                    'confidence': confidence,
                    'metadata': {
                        'analysis_type': 'global_timeseries',
                        'anomalous_period': str(period_key),
                        'period_score': anomaly_info['score'],
                        'period_value': anomaly_info.get('period_value'),
                        'expected_value': anomaly_info.get('expected_value'),
                        'deviation': anomaly_info.get('deviation')
                    }
                })
            else:
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.8,
                    'metadata': {
                        'analysis_type': 'global_timeseries',
                        'reason': 'normal_period'
                    }
                })
        
        return results
    
    def _analyze_account_patterns(self, transactions: pd.DataFrame, 
                                config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze time series patterns per account."""
        results = []
        
        for account_id in transactions['account_id'].unique():
            account_transactions = transactions[transactions['account_id'] == account_id].copy()
            
            if len(account_transactions) < 5:  # Minimum transactions per account
                for _, transaction in account_transactions.iterrows():
                    results.append({
                        'transaction_id': transaction['id'],
                        'score': 0.1,
                        'confidence': 0.3,
                        'metadata': {
                            'analysis_type': 'account_timeseries',
                            'account_id': account_id,
                            'reason': 'insufficient_account_data',
                            'transaction_count': len(account_transactions)
                        }
                    })
                continue
            
            # Analyze transaction timing patterns for this account
            account_results = self._analyze_account_timing(account_transactions, config)
            results.extend(account_results)
        
        return results
    
    def _analyze_account_timing(self, account_transactions: pd.DataFrame, 
                              config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze timing patterns for a specific account."""
        results = []
        
        # Sort by timestamp
        account_transactions = account_transactions.sort_values('timestamp').reset_index(drop=True)
        
        # Calculate time differences between consecutive transactions
        account_transactions['time_diff'] = account_transactions['timestamp'].diff()
        account_transactions['time_diff_hours'] = account_transactions['time_diff'].dt.total_seconds() / 3600
        
        # Analyze transaction frequency patterns
        time_diffs = account_transactions['time_diff_hours'].dropna()
        
        if len(time_diffs) > 3:
            # Calculate statistics for normal timing patterns
            median_diff = time_diffs.median()
            std_diff = time_diffs.std()
            q75 = time_diffs.quantile(0.75)
            q25 = time_diffs.quantile(0.25)
            iqr = q75 - q25
            
            # Identify unusual timing patterns
            for i, transaction in account_transactions.iterrows():
                if pd.isna(transaction['time_diff_hours']):
                    # First transaction for account
                    results.append({
                        'transaction_id': transaction['id'],
                        'score': 0.1,
                        'confidence': 0.5,
                        'metadata': {
                            'analysis_type': 'account_timeseries',
                            'account_id': transaction['account_id'],
                            'reason': 'first_transaction'
                        }
                    })
                    continue
                
                time_diff = transaction['time_diff_hours']
                
                # Calculate anomaly score based on timing deviation
                score = 0.1
                confidence = 0.6
                metadata = {
                    'analysis_type': 'account_timeseries',
                    'account_id': transaction['account_id'],
                    'time_diff_hours': float(time_diff),
                    'median_time_diff': float(median_diff),
                    'timing_pattern': 'normal'
                }
                
                # Check for unusually short intervals (rapid transactions)
                if time_diff < median_diff * 0.1 and time_diff < 1:  # Less than 1 hour and much faster than normal
                    score = 0.8
                    confidence = 0.9
                    metadata['timing_pattern'] = 'rapid_transaction'
                    metadata['deviation_type'] = 'too_fast'
                
                # Check for unusually long intervals
                elif time_diff > median_diff * 10 and time_diff > 168:  # More than a week and much slower than normal
                    score = 0.6
                    confidence = 0.7
                    metadata['timing_pattern'] = 'delayed_transaction'
                    metadata['deviation_type'] = 'too_slow'
                
                # Check for unusual timing based on account's normal pattern
                elif std_diff > 0:
                    z_score = abs(time_diff - median_diff) / std_diff
                    if z_score > 3:
                        score = min(0.9, 0.3 + z_score * 0.1)
                        confidence = 0.8
                        metadata['timing_pattern'] = 'unusual_interval'
                        metadata['z_score'] = float(z_score)
                
                results.append({
                    'transaction_id': transaction['id'],
                    'score': score,
                    'confidence': confidence,
                    'metadata': metadata
                })
        else:
            # Too few transactions for timing analysis
            for _, transaction in account_transactions.iterrows():
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.3,
                    'metadata': {
                        'analysis_type': 'account_timeseries',
                        'account_id': transaction['account_id'],
                        'reason': 'insufficient_timing_data'
                    }
                })
        
        return results
    
    def _create_time_series(self, transactions: pd.DataFrame, time_window: str, 
                          aggregation_method: str) -> pd.Series:
        """Create time series based on configuration."""
        if time_window == 'hour':
            grouper = pd.Grouper(key='timestamp', freq='H')
        elif time_window == 'day':
            grouper = pd.Grouper(key='timestamp', freq='D')
        elif time_window == 'week':
            grouper = pd.Grouper(key='timestamp', freq='W')
        else:
            grouper = pd.Grouper(key='timestamp', freq='H')  # Default to hourly
        
        if aggregation_method == 'count':
            time_series = transactions.groupby(grouper).size()
        elif aggregation_method == 'sum':
            time_series = transactions.groupby(grouper)['amount'].sum()
        elif aggregation_method == 'mean':
            time_series = transactions.groupby(grouper)['amount'].mean()
        else:
            time_series = transactions.groupby(grouper).size()  # Default to count
        
        # Fill missing periods with 0
        time_series = time_series.fillna(0)
        
        return time_series
    
    def _detect_anomalous_periods(self, time_series: pd.Series, 
                                config: Dict[str, Any]) -> Dict[Any, Dict[str, Any]]:
        """Detect anomalous periods in the time series."""
        threshold_method = config.get('threshold_method', 'std')
        threshold_multiplier = config.get('threshold_multiplier', 2.0)
        seasonal_adjustment = config.get('seasonal_adjustment', True)
        
        anomalous_periods = {}
        
        if len(time_series) < 3:
            return anomalous_periods
        
        # Apply seasonal adjustment if enabled
        adjusted_series = time_series.copy()
        if seasonal_adjustment and len(time_series) > 24:  # Need sufficient data for seasonal patterns
            adjusted_series = self._apply_seasonal_adjustment(time_series)
        
        # Calculate threshold based on method
        if threshold_method == 'std':
            mean_val = adjusted_series.mean()
            std_val = adjusted_series.std()
            upper_threshold = mean_val + threshold_multiplier * std_val
            lower_threshold = max(0, mean_val - threshold_multiplier * std_val)
        elif threshold_method == 'iqr':
            q75 = adjusted_series.quantile(0.75)
            q25 = adjusted_series.quantile(0.25)
            iqr = q75 - q25
            upper_threshold = q75 + threshold_multiplier * iqr
            lower_threshold = max(0, q25 - threshold_multiplier * iqr)
        elif threshold_method == 'percentile':
            percentile = threshold_multiplier if threshold_multiplier <= 100 else 95
            upper_threshold = adjusted_series.quantile(percentile / 100)
            lower_threshold = adjusted_series.quantile((100 - percentile) / 100)
        else:
            # Default to standard deviation
            mean_val = adjusted_series.mean()
            std_val = adjusted_series.std()
            upper_threshold = mean_val + 2.0 * std_val
            lower_threshold = max(0, mean_val - 2.0 * std_val)
        
        # Identify anomalous periods
        for period, value in adjusted_series.items():
            if value > upper_threshold or value < lower_threshold:
                # Calculate anomaly score
                if value > upper_threshold:
                    deviation = value - upper_threshold
                    max_possible_deviation = max(adjusted_series.max() - upper_threshold, 1)
                    score = 0.5 + 0.5 * (deviation / max_possible_deviation)
                else:
                    deviation = lower_threshold - value
                    max_possible_deviation = max(lower_threshold - adjusted_series.min(), 1)
                    score = 0.5 + 0.5 * (deviation / max_possible_deviation)
                
                score = min(1.0, score)
                confidence = 0.7 + 0.3 * score  # Higher score = higher confidence
                
                anomalous_periods[period] = {
                    'score': score,
                    'confidence': confidence,
                    'period_value': float(value),
                    'expected_value': float(adjusted_series.mean()),
                    'deviation': float(abs(value - adjusted_series.mean())),
                    'threshold_upper': float(upper_threshold),
                    'threshold_lower': float(lower_threshold)
                }
        
        return anomalous_periods
    
    def _apply_seasonal_adjustment(self, time_series: pd.Series) -> pd.Series:
        """Apply simple seasonal adjustment to the time series."""
        # Simple seasonal adjustment: remove trend and seasonal patterns
        try:
            # Calculate rolling mean to remove trend
            window_size = min(24, len(time_series) // 4)  # Adaptive window size
            if window_size < 3:
                return time_series
            
            rolling_mean = time_series.rolling(window=window_size, center=True).mean()
            detrended = time_series - rolling_mean
            
            # Remove seasonal patterns (if enough data)
            if len(time_series) > 48:  # Need at least 2 full cycles
                seasonal_pattern = detrended.groupby(detrended.index.hour if hasattr(detrended.index, 'hour') else detrended.index % 24).mean()
                adjusted = detrended - detrended.index.map(lambda x: seasonal_pattern.get(x.hour if hasattr(x, 'hour') else x % 24, 0))
                return adjusted.fillna(time_series)
            else:
                return detrended.fillna(time_series)
                
        except Exception:
            # If seasonal adjustment fails, return original series
            return time_series
    
    def _get_period_key(self, transaction: pd.Series, time_window: str):
        """Get the period key for a transaction based on time window."""
        timestamp = transaction['timestamp']
        
        if time_window == 'hour':
            return timestamp.floor('H')
        elif time_window == 'day':
            return timestamp.floor('D')
        elif time_window == 'week':
            return timestamp.to_period('W')
        else:
            return timestamp.floor('H')  # Default to hourly
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate algorithm configuration."""
        # Check time_window
        if 'time_window' in config:
            valid_windows = ['hour', 'day', 'week']
            if config['time_window'] not in valid_windows:
                raise AlgorithmConfigurationError(f"time_window must be one of: {valid_windows}")
        
        # Check aggregation_method
        if 'aggregation_method' in config:
            valid_methods = ['count', 'sum', 'mean']
            if config['aggregation_method'] not in valid_methods:
                raise AlgorithmConfigurationError(f"aggregation_method must be one of: {valid_methods}")
        
        # Check threshold_method
        if 'threshold_method' in config:
            valid_methods = ['std', 'iqr', 'percentile']
            if config['threshold_method'] not in valid_methods:
                raise AlgorithmConfigurationError(f"threshold_method must be one of: {valid_methods}")
        
        # Check threshold_multiplier
        if 'threshold_multiplier' in config:
            multiplier = config['threshold_multiplier']
            if not isinstance(multiplier, (int, float)) or multiplier <= 0:
                raise AlgorithmConfigurationError("threshold_multiplier must be a positive number")
        
        # Check min_periods
        if 'min_periods' in config:
            min_periods = config['min_periods']
            if not isinstance(min_periods, int) or min_periods < 3:
                raise AlgorithmConfigurationError("min_periods must be an integer >= 3")
        
        return True
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'time_window': 'hour',
            'aggregation_method': 'count',
            'threshold_method': 'std',
            'threshold_multiplier': 2.0,
            'seasonal_adjustment': True,
            'min_periods': 10
        }
    
    def get_minimum_transactions(self) -> int:
        """Minimum number of transactions required."""
        return 15  # Need enough data for time series analysis 