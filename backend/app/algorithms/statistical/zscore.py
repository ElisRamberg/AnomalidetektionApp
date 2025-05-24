"""Z-Score based anomaly detection algorithm."""

from typing import Dict, Any
import pandas as pd
import numpy as np
from scipy import stats

from ..base import StatisticalAlgorithm
from ...utils.exceptions import AlgorithmConfigurationError


class ZScoreAlgorithm(StatisticalAlgorithm):
    """
    Z-Score based anomaly detection algorithm.
    
    Detects anomalies based on how many standard deviations a transaction
    amount is from the mean of the account's historical transactions.
    """
    
    __version__ = "1.0.0"
    
    def __init__(self):
        super().__init__("zscore")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration for Z-Score algorithm."""
        return {
            "threshold": 3.0,  # Number of standard deviations
            "window_size": 30,  # Rolling window size for dynamic calculation
            "min_transactions": 5,  # Minimum transactions needed per account
            "use_rolling_window": True,  # Use rolling window vs global stats
            "account_specific": True,  # Calculate stats per account vs globally
            "absolute_zscore": True,  # Use absolute z-score for anomaly detection
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Z-Score algorithm configuration."""
        required_keys = ["threshold", "window_size", "min_transactions"]
        
        for key in required_keys:
            if key not in config:
                raise AlgorithmConfigurationError(f"Missing required config key: {key}")
        
        if config["threshold"] <= 0:
            raise AlgorithmConfigurationError("threshold must be positive")
        
        if config["window_size"] < 2:
            raise AlgorithmConfigurationError("window_size must be at least 2")
        
        if config["min_transactions"] < 1:
            raise AlgorithmConfigurationError("min_transactions must be at least 1")
        
        return True
    
    def get_minimum_transactions(self) -> int:
        """Z-Score algorithm needs at least 2 transactions to calculate statistics."""
        return 2
    
    def detect(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Detect anomalies using Z-Score analysis.
        
        Args:
            transactions: DataFrame with transaction data
            config: Algorithm configuration
            
        Returns:
            DataFrame with anomaly scores
        """
        # Validate configuration
        self.validate_config(config)
        
        # Validate and prepare data
        self.validate_input_data(transactions)
        df = self.prepare_data(transactions)
        
        # Get configuration values
        threshold = config["threshold"]
        window_size = config["window_size"]
        min_transactions = config["min_transactions"]
        use_rolling = config.get("use_rolling_window", True)
        account_specific = config.get("account_specific", True)
        absolute_zscore = config.get("absolute_zscore", True)
        
        results = []
        
        if account_specific:
            # Calculate Z-scores per account
            for account_id in df['account_id'].unique():
                account_data = df[df['account_id'] == account_id].copy()
                
                if len(account_data) < min_transactions:
                    # Not enough data for this account, skip or use global stats
                    continue
                
                account_results = self._calculate_account_zscores(
                    account_data, threshold, window_size, use_rolling, absolute_zscore
                )
                results.extend(account_results)
        else:
            # Calculate global Z-scores
            global_results = self._calculate_global_zscores(
                df, threshold, window_size, use_rolling, absolute_zscore
            )
            results.extend(global_results)
        
        # Create result DataFrame
        if not results:
            # Return empty results if no transactions processed
            return self.create_result_dataframe([], [], [], [])
        
        transaction_ids = [r['transaction_id'] for r in results]
        scores = [r['score'] for r in results]
        confidences = [r['confidence'] for r in results]
        metadata_list = [r['metadata'] for r in results]
        
        return self.create_result_dataframe(
            transaction_ids, scores, confidences, metadata_list
        )
    
    def _calculate_account_zscores(self, account_data: pd.DataFrame, threshold: float,
                                 window_size: int, use_rolling: bool,
                                 absolute_zscore: bool) -> list:
        """Calculate Z-scores for a single account."""
        results = []
        
        account_data = account_data.sort_values('timestamp').copy()
        amounts = account_data['amount'].values
        
        if use_rolling and len(account_data) >= window_size:
            # Rolling window calculation
            for i in range(len(account_data)):
                if i < window_size - 1:
                    # Not enough history, use what we have
                    window_amounts = amounts[:i + 1]
                else:
                    # Use rolling window
                    window_amounts = amounts[max(0, i - window_size + 1):i + 1]
                
                if len(window_amounts) < 2:
                    # Need at least 2 data points
                    z_score = 0.0
                    confidence = 0.0
                else:
                    current_amount = amounts[i]
                    mean_amount = np.mean(window_amounts[:-1])  # Exclude current transaction
                    std_amount = np.std(window_amounts[:-1], ddof=1)
                    
                    if std_amount == 0:
                        z_score = 0.0
                        confidence = 0.0
                    else:
                        z_score = (current_amount - mean_amount) / std_amount
                        if absolute_zscore:
                            z_score = abs(z_score)
                        
                        # Confidence based on how much it exceeds threshold
                        confidence = min(1.0, abs(z_score) / threshold) if threshold > 0 else 0.0
                
                transaction_id = str(account_data.iloc[i]['id'])
                results.append({
                    'transaction_id': transaction_id,
                    'score': float(z_score),
                    'confidence': float(confidence),
                    'metadata': {
                        'mean_amount': float(mean_amount) if 'mean_amount' in locals() else None,
                        'std_amount': float(std_amount) if 'std_amount' in locals() else None,
                        'window_size_used': len(window_amounts),
                        'account_id': account_data.iloc[i]['account_id']
                    }
                })
        else:
            # Global statistics for the account
            if len(amounts) < 2:
                # Not enough data
                return results
            
            mean_amount = np.mean(amounts)
            std_amount = np.std(amounts, ddof=1)
            
            for i, row in account_data.iterrows():
                current_amount = row['amount']
                
                if std_amount == 0:
                    z_score = 0.0
                    confidence = 0.0
                else:
                    z_score = (current_amount - mean_amount) / std_amount
                    if absolute_zscore:
                        z_score = abs(z_score)
                    
                    confidence = min(1.0, abs(z_score) / threshold) if threshold > 0 else 0.0
                
                transaction_id = str(row['id'])
                results.append({
                    'transaction_id': transaction_id,
                    'score': float(z_score),
                    'confidence': float(confidence),
                    'metadata': {
                        'mean_amount': float(mean_amount),
                        'std_amount': float(std_amount),
                        'total_transactions': len(amounts),
                        'account_id': row['account_id']
                    }
                })
        
        return results
    
    def _calculate_global_zscores(self, df: pd.DataFrame, threshold: float,
                                window_size: int, use_rolling: bool,
                                absolute_zscore: bool) -> list:
        """Calculate Z-scores globally across all transactions."""
        results = []
        
        df = df.sort_values('timestamp').copy()
        amounts = df['amount'].values
        
        if use_rolling and len(df) >= window_size:
            # Rolling window calculation
            for i in range(len(df)):
                if i < window_size - 1:
                    window_amounts = amounts[:i + 1]
                else:
                    window_amounts = amounts[max(0, i - window_size + 1):i + 1]
                
                if len(window_amounts) < 2:
                    z_score = 0.0
                    confidence = 0.0
                else:
                    current_amount = amounts[i]
                    mean_amount = np.mean(window_amounts[:-1])
                    std_amount = np.std(window_amounts[:-1], ddof=1)
                    
                    if std_amount == 0:
                        z_score = 0.0
                        confidence = 0.0
                    else:
                        z_score = (current_amount - mean_amount) / std_amount
                        if absolute_zscore:
                            z_score = abs(z_score)
                        
                        confidence = min(1.0, abs(z_score) / threshold) if threshold > 0 else 0.0
                
                transaction_id = str(df.iloc[i]['id'])
                results.append({
                    'transaction_id': transaction_id,
                    'score': float(z_score),
                    'confidence': float(confidence),
                    'metadata': {
                        'mean_amount': float(mean_amount) if 'mean_amount' in locals() else None,
                        'std_amount': float(std_amount) if 'std_amount' in locals() else None,
                        'window_size_used': len(window_amounts),
                        'global_calculation': True
                    }
                })
        else:
            # Global statistics
            if len(amounts) < 2:
                return results
            
            mean_amount = np.mean(amounts)
            std_amount = np.std(amounts, ddof=1)
            
            for i, row in df.iterrows():
                current_amount = row['amount']
                
                if std_amount == 0:
                    z_score = 0.0
                    confidence = 0.0
                else:
                    z_score = (current_amount - mean_amount) / std_amount
                    if absolute_zscore:
                        z_score = abs(z_score)
                    
                    confidence = min(1.0, abs(z_score) / threshold) if threshold > 0 else 0.0
                
                transaction_id = str(row['id'])
                results.append({
                    'transaction_id': transaction_id,
                    'score': float(z_score),
                    'confidence': float(confidence),
                    'metadata': {
                        'mean_amount': float(mean_amount),
                        'std_amount': float(std_amount),
                        'total_transactions': len(amounts),
                        'global_calculation': True
                    }
                })
        
        return results 