"""Base algorithm interface for anomaly detection."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

from ..utils.exceptions import AlgorithmError, AlgorithmConfigurationError


class AnomalyDetectionAlgorithm(ABC):
    """Abstract base class for all anomaly detection algorithms."""
    
    def __init__(self, name: str, algorithm_type: str):
        self._name = name
        self._algorithm_type = algorithm_type
        self._default_config = self._get_default_config()
    
    @property
    def name(self) -> str:
        """Return algorithm name."""
        return self._name
    
    @property
    def algorithm_type(self) -> str:
        """Return algorithm type (statistical, rule_based, ml_based)."""
        return self._algorithm_type
    
    @abstractmethod
    def detect(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Run anomaly detection on transaction data.
        
        Args:
            transactions: DataFrame with transaction data
            config: Algorithm-specific configuration
            
        Returns:
            DataFrame with columns: transaction_id, score, confidence, metadata
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate algorithm configuration.
        
        Args:
            config: Algorithm configuration to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            AlgorithmConfigurationError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration for the algorithm."""
        pass
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return self._default_config.copy()
    
    def prepare_data(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare transaction data for algorithm processing.
        
        Default implementation - can be overridden by specific algorithms.
        
        Args:
            transactions: Raw transaction DataFrame
            
        Returns:
            Prepared DataFrame
        """
        # Ensure required columns exist
        required_columns = ['id', 'amount', 'timestamp', 'account_id']
        missing_columns = [col for col in required_columns if col not in transactions.columns]
        
        if missing_columns:
            raise AlgorithmError(f"Missing required columns: {missing_columns}")
        
        # Basic data cleaning
        df = transactions.copy()
        
        # Convert timestamp to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
        
        # Remove any rows with null values in required columns
        df = df.dropna(subset=required_columns)
        
        return df
    
    def create_result_dataframe(self, transaction_ids: List[str], scores: List[float],
                              confidence_scores: Optional[List[float]] = None,
                              metadata_list: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
        """
        Create standardized result DataFrame.
        
        Args:
            transaction_ids: List of transaction IDs
            scores: List of anomaly scores
            confidence_scores: Optional list of confidence scores
            metadata_list: Optional list of metadata dictionaries
            
        Returns:
            Standardized result DataFrame
        """
        if len(transaction_ids) != len(scores):
            raise AlgorithmError("Length of transaction_ids and scores must match")
        
        result_df = pd.DataFrame({
            'transaction_id': transaction_ids,
            'score': scores,
            'confidence': confidence_scores or [None] * len(transaction_ids),
            'metadata': metadata_list or [{}] * len(transaction_ids)
        })
        
        return result_df
    
    def validate_input_data(self, transactions: pd.DataFrame) -> None:
        """
        Validate input transaction data.
        
        Args:
            transactions: Transaction DataFrame to validate
            
        Raises:
            AlgorithmError: If data is invalid
        """
        if transactions.empty:
            raise AlgorithmError("Transaction data is empty")
        
        required_columns = ['id', 'amount', 'timestamp', 'account_id']
        missing_columns = [col for col in required_columns if col not in transactions.columns]
        
        if missing_columns:
            raise AlgorithmError(f"Missing required columns: {missing_columns}")
        
        # Check for minimum number of transactions
        min_transactions = self.get_minimum_transactions()
        if len(transactions) < min_transactions:
            raise AlgorithmError(
                f"Insufficient data: algorithm requires at least {min_transactions} transactions, "
                f"got {len(transactions)}"
            )
    
    def get_minimum_transactions(self) -> int:
        """
        Get minimum number of transactions required for this algorithm.
        
        Returns:
            Minimum number of transactions needed
        """
        return 1  # Default minimum, can be overridden by specific algorithms
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """
        Get information about the algorithm.
        
        Returns:
            Dictionary with algorithm information
        """
        return {
            'name': self.name,
            'type': self.algorithm_type,
            'description': self.__doc__ or "No description available",
            'default_config': self.get_default_config(),
            'minimum_transactions': self.get_minimum_transactions(),
            'version': getattr(self, '__version__', '1.0.0')
        }
    
    def log_execution(self, transactions_count: int, execution_time: float, 
                     anomalies_found: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log algorithm execution details.
        
        Args:
            transactions_count: Number of transactions processed
            execution_time: Execution time in seconds
            anomalies_found: Number of anomalies detected
            config: Configuration used
            
        Returns:
            Execution log dictionary
        """
        return {
            'algorithm': self.name,
            'type': self.algorithm_type,
            'timestamp': datetime.utcnow().isoformat(),
            'transactions_processed': transactions_count,
            'execution_time_seconds': execution_time,
            'anomalies_found': anomalies_found,
            'anomaly_rate': anomalies_found / transactions_count if transactions_count > 0 else 0,
            'config_used': config
        }


class StatisticalAlgorithm(AnomalyDetectionAlgorithm):
    """Base class for statistical anomaly detection algorithms."""
    
    def __init__(self, name: str):
        super().__init__(name, "statistical")


class RuleBasedAlgorithm(AnomalyDetectionAlgorithm):
    """Base class for rule-based anomaly detection algorithms."""
    
    def __init__(self, name: str):
        super().__init__(name, "rule_based")
    
    def detect(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Run rule-based detection.
        
        For rule-based algorithms, we typically return binary results (0 or 1)
        instead of continuous scores.
        """
        # This will be implemented by specific rule algorithms
        pass


class MLBasedAlgorithm(AnomalyDetectionAlgorithm):
    """Base class for machine learning-based anomaly detection algorithms."""
    
    def __init__(self, name: str):
        super().__init__(name, "ml_based")
    
    def fit(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> None:
        """
        Fit the ML model on transaction data.
        
        Args:
            transactions: Training transaction data
            config: Algorithm configuration
        """
        # Default implementation - can be overridden
        pass
    
    def predict(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Predict anomalies on new transaction data.
        
        Args:
            transactions: Transaction data to predict on
            config: Algorithm configuration
            
        Returns:
            DataFrame with predictions
        """
        # Default implementation calls detect method
        return self.detect(transactions, config)
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance scores if available.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        return None  # Default implementation - can be overridden


class AlgorithmRegistry:
    """Registry for managing anomaly detection algorithms."""
    
    def __init__(self):
        self._algorithms: Dict[str, Dict[str, AnomalyDetectionAlgorithm]] = {
            'statistical': {},
            'rule_based': {},
            'ml_based': {}
        }
    
    def register(self, algorithm: AnomalyDetectionAlgorithm) -> None:
        """Register an algorithm."""
        self._algorithms[algorithm.algorithm_type][algorithm.name] = algorithm
    
    def get_algorithm(self, algorithm_type: str, algorithm_name: str) -> AnomalyDetectionAlgorithm:
        """Get a specific algorithm."""
        if algorithm_type not in self._algorithms:
            raise AlgorithmError(f"Unknown algorithm type: {algorithm_type}")
        
        if algorithm_name not in self._algorithms[algorithm_type]:
            raise AlgorithmError(f"Unknown algorithm: {algorithm_type}.{algorithm_name}")
        
        return self._algorithms[algorithm_type][algorithm_name]
    
    def list_algorithms(self, algorithm_type: Optional[str] = None) -> Dict[str, Any]:
        """List available algorithms."""
        if algorithm_type:
            if algorithm_type not in self._algorithms:
                return {}
            return {
                algorithm_type: list(self._algorithms[algorithm_type].keys())
            }
        
        return {
            algo_type: list(algorithms.keys())
            for algo_type, algorithms in self._algorithms.items()
        }
    
    def get_algorithm_info(self, algorithm_type: str, algorithm_name: str) -> Dict[str, Any]:
        """Get information about a specific algorithm."""
        algorithm = self.get_algorithm(algorithm_type, algorithm_name)
        return algorithm.get_algorithm_info()


# Global algorithm registry
algorithm_registry = AlgorithmRegistry() 