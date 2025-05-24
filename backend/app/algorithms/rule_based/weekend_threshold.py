"""Weekend threshold rule-based algorithm for detecting unusual weekend activity."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from ..base import RuleBasedAlgorithm
from ...utils.exceptions import AlgorithmError, AlgorithmConfigurationError


class WeekendThresholdAlgorithm(RuleBasedAlgorithm):
    """
    Rule-based algorithm that detects anomalous transactions during weekends.
    
    This algorithm applies business logic that weekends typically have lower
    transaction activity, and flags transactions that exceed expected weekend
    thresholds based on weekday patterns.
    """
    
    __version__ = "1.0.0"
    
    def __init__(self):
        super().__init__("weekend_threshold")
    
    def detect(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Detect anomalies based on weekend transaction patterns.
        
        Args:
            transactions: Prepared transaction DataFrame
            config: Algorithm configuration
            
        Returns:
            DataFrame with transaction_id, score, confidence, metadata
        """
        # Extract configuration parameters
        weekday_multiplier = config.get('weekday_multiplier', 1.0)
        weekend_multiplier = config.get('weekend_multiplier', 0.3)
        amount_threshold_method = config.get('amount_threshold_method', 'percentile')
        amount_percentile = config.get('amount_percentile', 75)
        frequency_analysis = config.get('frequency_analysis', True)
        account_specific = config.get('account_specific', True)
        
        results = []
        
        # Ensure required columns exist
        if 'is_weekend' not in transactions.columns:
            # Calculate weekend flag if not present
            transactions['day_of_week'] = transactions['timestamp'].dt.dayofweek
            transactions['is_weekend'] = transactions['day_of_week'].isin([5, 6])  # Saturday, Sunday
        
        # Analyze global patterns first
        global_results = self._analyze_global_weekend_patterns(transactions, config)
        
        # Analyze account-specific patterns if enabled
        if account_specific:
            account_results = self._analyze_account_weekend_patterns(transactions, config)
            results.extend(account_results)
        else:
            results.extend(global_results)
        
        # If account-specific analysis was done, merge with global results
        if account_specific and global_results:
            results = self._merge_results(results, global_results)
        
        return self.create_result_dataframe(
            [r['transaction_id'] for r in results],
            [r['score'] for r in results],
            [r['confidence'] for r in results],
            [r['metadata'] for r in results]
        )
    
    def _analyze_global_weekend_patterns(self, transactions: pd.DataFrame, 
                                       config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze weekend patterns across all transactions."""
        results = []
        
        # Calculate global weekday and weekend statistics
        weekday_transactions = transactions[~transactions['is_weekend']]
        weekend_transactions = transactions[transactions['is_weekend']]
        
        if len(weekday_transactions) == 0:
            # No weekday data to establish baseline
            for _, transaction in transactions.iterrows():
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.2,
                    'metadata': {
                        'rule_type': 'weekend_threshold',
                        'analysis_level': 'global',
                        'reason': 'no_weekday_baseline'
                    }
                })
            return results
        
        # Calculate weekday baseline statistics
        weekday_stats = self._calculate_baseline_stats(weekday_transactions, config)
        
        # Analyze each weekend transaction
        for _, transaction in weekend_transactions.iterrows():
            score, confidence, metadata = self._evaluate_weekend_transaction(
                transaction, weekday_stats, config, 'global'
            )
            
            results.append({
                'transaction_id': transaction['id'],
                'score': score,
                'confidence': confidence,
                'metadata': metadata
            })
        
        # Add normal scores for weekday transactions
        for _, transaction in weekday_transactions.iterrows():
            results.append({
                'transaction_id': transaction['id'],
                'score': 0.1,
                'confidence': 0.8,
                'metadata': {
                    'rule_type': 'weekend_threshold',
                    'analysis_level': 'global',
                    'reason': 'weekday_transaction'
                }
            })
        
        return results
    
    def _analyze_account_weekend_patterns(self, transactions: pd.DataFrame, 
                                        config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze weekend patterns per account."""
        results = []
        
        for account_id in transactions['account_id'].unique():
            account_transactions = transactions[transactions['account_id'] == account_id].copy()
            
            # Get weekday and weekend transactions for this account
            weekday_transactions = account_transactions[~account_transactions['is_weekend']]
            weekend_transactions = account_transactions[account_transactions['is_weekend']]
            
            if len(weekday_transactions) < 3:
                # Insufficient weekday data for this account
                for _, transaction in account_transactions.iterrows():
                    results.append({
                        'transaction_id': transaction['id'],
                        'score': 0.1,
                        'confidence': 0.3,
                        'metadata': {
                            'rule_type': 'weekend_threshold',
                            'analysis_level': 'account',
                            'account_id': account_id,
                            'reason': 'insufficient_weekday_data',
                            'weekday_count': len(weekday_transactions)
                        }
                    })
                continue
            
            # Calculate account-specific weekday baseline
            weekday_stats = self._calculate_baseline_stats(weekday_transactions, config)
            
            # Analyze weekend transactions for this account
            for _, transaction in weekend_transactions.iterrows():
                score, confidence, metadata = self._evaluate_weekend_transaction(
                    transaction, weekday_stats, config, 'account'
                )
                metadata['account_id'] = account_id
                
                results.append({
                    'transaction_id': transaction['id'],
                    'score': score,
                    'confidence': confidence,
                    'metadata': metadata
                })
            
            # Add normal scores for weekday transactions
            for _, transaction in weekday_transactions.iterrows():
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.8,
                    'metadata': {
                        'rule_type': 'weekend_threshold',
                        'analysis_level': 'account',
                        'account_id': account_id,
                        'reason': 'weekday_transaction'
                    }
                })
        
        return results
    
    def _calculate_baseline_stats(self, weekday_transactions: pd.DataFrame, 
                                config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate baseline statistics from weekday transactions."""
        amount_threshold_method = config.get('amount_threshold_method', 'percentile')
        amount_percentile = config.get('amount_percentile', 75)
        
        if len(weekday_transactions) == 0:
            return {
                'count': 0,
                'amount_threshold': 0,
                'mean_amount': 0,
                'std_amount': 0,
                'frequency_per_day': 0
            }
        
        amounts = weekday_transactions['amount'].abs()  # Use absolute values
        
        # Calculate amount threshold
        if amount_threshold_method == 'percentile':
            amount_threshold = amounts.quantile(amount_percentile / 100)
        elif amount_threshold_method == 'mean_std':
            mean_amount = amounts.mean()
            std_amount = amounts.std()
            amount_threshold = mean_amount + 2 * std_amount
        elif amount_threshold_method == 'median_iqr':
            median_amount = amounts.median()
            q75 = amounts.quantile(0.75)
            q25 = amounts.quantile(0.25)
            iqr = q75 - q25
            amount_threshold = median_amount + 1.5 * iqr
        else:
            amount_threshold = amounts.quantile(0.75)  # Default to 75th percentile
        
        # Calculate frequency statistics
        weekdays_span = (weekday_transactions['timestamp'].max() - 
                        weekday_transactions['timestamp'].min()).days
        weekdays_count = max(1, weekdays_span * 5 / 7)  # Approximate weekdays
        frequency_per_day = len(weekday_transactions) / weekdays_count
        
        return {
            'count': len(weekday_transactions),
            'amount_threshold': float(amount_threshold),
            'mean_amount': float(amounts.mean()),
            'std_amount': float(amounts.std()),
            'median_amount': float(amounts.median()),
            'frequency_per_day': float(frequency_per_day),
            'max_amount': float(amounts.max()),
            'min_amount': float(amounts.min())
        }
    
    def _evaluate_weekend_transaction(self, transaction: pd.Series, weekday_stats: Dict[str, Any],
                                    config: Dict[str, Any], analysis_level: str) -> tuple:
        """Evaluate a single weekend transaction against weekday baseline."""
        weekend_multiplier = config.get('weekend_multiplier', 0.3)
        frequency_analysis = config.get('frequency_analysis', True)
        
        transaction_amount = abs(transaction['amount'])
        score = 0.1
        confidence = 0.7
        
        metadata = {
            'rule_type': 'weekend_threshold',
            'analysis_level': analysis_level,
            'transaction_amount': float(transaction_amount),
            'is_weekend': True,
            'day_of_week': int(transaction.get('day_of_week', 6)),
            'violations': []
        }
        
        # Check amount threshold violation
        expected_weekend_threshold = weekday_stats['amount_threshold'] * weekend_multiplier
        metadata['expected_weekend_threshold'] = float(expected_weekend_threshold)
        metadata['weekday_threshold'] = float(weekday_stats['amount_threshold'])
        
        if transaction_amount > expected_weekend_threshold:
            # Calculate violation severity
            excess_amount = transaction_amount - expected_weekend_threshold
            max_excess = max(weekday_stats['max_amount'] - expected_weekend_threshold, 1)
            amount_violation_score = min(1.0, excess_amount / max_excess)
            
            score += amount_violation_score * 0.6  # Amount violations are significant
            metadata['violations'].append('amount_threshold')
            metadata['amount_violation_score'] = float(amount_violation_score)
            metadata['excess_amount'] = float(excess_amount)
        
        # Check if transaction is unusually large even for weekdays
        if transaction_amount > weekday_stats['amount_threshold']:
            # This transaction would be unusual even on weekdays
            weekday_excess = transaction_amount - weekday_stats['amount_threshold']
            max_weekday_excess = max(weekday_stats['max_amount'] - weekday_stats['amount_threshold'], 1)
            weekday_violation_score = min(1.0, weekday_excess / max_weekday_excess)
            
            score += weekday_violation_score * 0.3  # Additional penalty for being unusual overall
            metadata['violations'].append('weekday_threshold')
            metadata['weekday_violation_score'] = float(weekday_violation_score)
        
        # Apply business hour analysis if timestamp information is available
        if 'hour' in transaction:
            hour = transaction['hour']
            # Weekend business hours are typically more restricted
            if hour < 6 or hour > 22:  # Very early or very late
                score += 0.2
                metadata['violations'].append('unusual_weekend_hour')
                metadata['transaction_hour'] = int(hour)
        
        # Apply frequency context if available
        if frequency_analysis and 'timestamp' in transaction:
            # This would require more complex analysis of transaction frequency
            # For now, we'll add a placeholder for future enhancement
            metadata['frequency_analysis'] = 'not_implemented'
        
        # Normalize score to 0-1 range
        score = min(1.0, score)
        
        # Adjust confidence based on data quality and violation types
        if len(metadata['violations']) > 1:
            confidence = min(1.0, confidence + 0.2)  # More confident with multiple violations
        
        if weekday_stats['count'] < 10:
            confidence *= 0.7  # Less confident with limited baseline data
        
        metadata['final_score'] = float(score)
        metadata['confidence'] = float(confidence)
        
        return score, confidence, metadata
    
    def _merge_results(self, account_results: List[Dict[str, Any]], 
                      global_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge account-specific results with global results."""
        # Create a map of global results
        global_map = {r['transaction_id']: r for r in global_results}
        
        merged_results = []
        
        for account_result in account_results:
            transaction_id = account_result['transaction_id']
            
            if transaction_id in global_map:
                global_result = global_map[transaction_id]
                
                # Take the maximum score between account and global analysis
                final_score = max(account_result['score'], global_result['score'])
                final_confidence = max(account_result['confidence'], global_result['confidence'])
                
                # Merge metadata
                merged_metadata = account_result['metadata'].copy()
                merged_metadata['global_analysis'] = global_result['metadata']
                merged_metadata['score_source'] = 'account' if account_result['score'] > global_result['score'] else 'global'
                
                merged_results.append({
                    'transaction_id': transaction_id,
                    'score': final_score,
                    'confidence': final_confidence,
                    'metadata': merged_metadata
                })
            else:
                merged_results.append(account_result)
        
        return merged_results
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate algorithm configuration."""
        # Check weekday_multiplier
        if 'weekday_multiplier' in config:
            multiplier = config['weekday_multiplier']
            if not isinstance(multiplier, (int, float)) or multiplier <= 0:
                raise AlgorithmConfigurationError("weekday_multiplier must be a positive number")
        
        # Check weekend_multiplier
        if 'weekend_multiplier' in config:
            multiplier = config['weekend_multiplier']
            if not isinstance(multiplier, (int, float)) or multiplier <= 0:
                raise AlgorithmConfigurationError("weekend_multiplier must be a positive number")
        
        # Check amount_threshold_method
        if 'amount_threshold_method' in config:
            valid_methods = ['percentile', 'mean_std', 'median_iqr']
            if config['amount_threshold_method'] not in valid_methods:
                raise AlgorithmConfigurationError(f"amount_threshold_method must be one of: {valid_methods}")
        
        # Check amount_percentile
        if 'amount_percentile' in config:
            percentile = config['amount_percentile']
            if not isinstance(percentile, (int, float)) or not 1 <= percentile <= 99:
                raise AlgorithmConfigurationError("amount_percentile must be between 1 and 99")
        
        return True
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'weekday_multiplier': 1.0,
            'weekend_multiplier': 0.3,
            'amount_threshold_method': 'percentile',
            'amount_percentile': 75,
            'frequency_analysis': True,
            'account_specific': True
        }
    
    def get_minimum_transactions(self) -> int:
        """Minimum number of transactions required."""
        return 10  # Need both weekday and weekend transactions 