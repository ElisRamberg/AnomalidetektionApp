"""Strategy manager service for handling strategy execution and management."""

import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..algorithms import AlgorithmRegistry
from ..models.strategy import Strategy
from ..utils.exceptions import StrategyError, StrategyConfigurationError
from ..config import get_settings

settings = get_settings()


class StrategyManagerService:
    """Service for managing and executing anomaly detection strategies."""
    
    def __init__(self):
        self.algorithm_registry = AlgorithmRegistry()
    
    def validate_strategy_configuration(self, configuration: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate strategy configuration and return validation results.
        
        Args:
            configuration: Strategy configuration to validate
            
        Returns:
            Validation results with errors, warnings, and algorithm checks
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'algorithm_checks': {},
            'global_settings_check': {}
        }
        
        try:
            # Check basic structure
            if not isinstance(configuration, dict):
                validation_results['valid'] = False
                validation_results['errors'].append("Configuration must be a dictionary")
                return validation_results
            
            # Validate algorithms section
            algorithms_validation = self._validate_algorithms_section(configuration)
            validation_results['algorithm_checks'] = algorithms_validation
            
            if not algorithms_validation.get('valid', True):
                validation_results['valid'] = False
                validation_results['errors'].extend(algorithms_validation.get('errors', []))
            
            validation_results['warnings'].extend(algorithms_validation.get('warnings', []))
            
            # Validate global settings
            global_settings_validation = self._validate_global_settings(configuration)
            validation_results['global_settings_check'] = global_settings_validation
            
            if not global_settings_validation.get('valid', True):
                validation_results['valid'] = False
                validation_results['errors'].extend(global_settings_validation.get('errors', []))
            
            validation_results['warnings'].extend(global_settings_validation.get('warnings', []))
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation failed: {str(e)}")
        
        return validation_results
    
    def _validate_algorithms_section(self, configuration: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the algorithms section of the configuration."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'algorithms': {}
        }
        
        if 'algorithms' not in configuration:
            result['valid'] = False
            result['errors'].append("Configuration must include 'algorithms' section")
            return result
        
        algorithms = configuration['algorithms']
        if not isinstance(algorithms, list):
            result['valid'] = False
            result['errors'].append("Algorithms must be a list")
            return result
        
        if len(algorithms) == 0:
            result['valid'] = False
            result['errors'].append("At least one algorithm must be configured")
            return result
        
        enabled_count = 0
        
        for i, algo_config in enumerate(algorithms):
            algo_result = self._validate_single_algorithm(algo_config, i)
            algo_key = f"algorithm_{i}"
            
            if 'type' in algo_config and 'name' in algo_config:
                algo_key = f"{algo_config['type']}.{algo_config['name']}"
            
            result['algorithms'][algo_key] = algo_result
            
            if not algo_result['valid']:
                result['valid'] = False
                result['errors'].extend(algo_result['errors'])
            
            result['warnings'].extend(algo_result['warnings'])
            
            if algo_config.get('enabled', True):
                enabled_count += 1
        
        if enabled_count == 0:
            result['warnings'].append("No algorithms are enabled")
        
        return result
    
    def _validate_single_algorithm(self, algo_config: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Validate a single algorithm configuration."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'config_check': {}
        }
        
        # Check required fields
        required_fields = ['type', 'name', 'enabled']
        for field in required_fields:
            if field not in algo_config:
                result['valid'] = False
                result['errors'].append(f"Algorithm {index} missing required field: {field}")
        
        if not result['valid']:
            return result
        
        algo_type = algo_config['type']
        algo_name = algo_config['name']
        
        # Validate algorithm exists
        try:
            algorithm = self.algorithm_registry.get_algorithm(algo_type, algo_name)
            
            # Validate algorithm-specific configuration
            if 'config' in algo_config:
                try:
                    algorithm.validate_config(algo_config['config'])
                    result['config_check'] = {
                        'valid': True,
                        'message': "Configuration is valid"
                    }
                except Exception as e:
                    result['valid'] = False
                    result['errors'].append(f"Algorithm {algo_type}.{algo_name} config invalid: {str(e)}")
                    result['config_check'] = {
                        'valid': False,
                        'error': str(e)
                    }
            else:
                result['warnings'].append(f"Algorithm {algo_type}.{algo_name} using default configuration")
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Algorithm {algo_type}.{algo_name} not found: {str(e)}")
        
        return result
    
    def _validate_global_settings(self, configuration: Dict[str, Any]) -> Dict[str, Any]:
        """Validate global settings section."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if 'global_settings' not in configuration:
            result['warnings'].append("No global settings specified, using defaults")
            return result
        
        global_settings = configuration['global_settings']
        if not isinstance(global_settings, dict):
            result['valid'] = False
            result['errors'].append("Global settings must be a dictionary")
            return result
        
        # Validate aggregation method
        if 'aggregation_method' in global_settings:
            valid_methods = ['max', 'min', 'mean', 'weighted_average']
            method = global_settings['aggregation_method']
            
            if method not in valid_methods:
                result['valid'] = False
                result['errors'].append(f"Invalid aggregation method '{method}'. Must be one of: {valid_methods}")
            
            # Special validation for weighted_average
            if method == 'weighted_average':
                if 'weights' not in global_settings:
                    result['warnings'].append("Weighted average method specified but no weights provided")
                else:
                    weights = global_settings['weights']
                    if not isinstance(weights, dict):
                        result['valid'] = False
                        result['errors'].append("Weights must be a dictionary")
        
        # Validate confidence threshold
        if 'confidence_threshold' in global_settings:
            threshold = global_settings['confidence_threshold']
            if not isinstance(threshold, (int, float)):
                result['valid'] = False
                result['errors'].append("Confidence threshold must be a number")
            elif not 0 <= threshold <= 1:
                result['valid'] = False
                result['errors'].append("Confidence threshold must be between 0 and 1")
        
        return result
    
    def optimize_strategy_for_data(self, base_strategy: Dict[str, Any], 
                                 sample_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Optimize strategy parameters based on sample data characteristics.
        
        Args:
            base_strategy: Base strategy configuration
            sample_data: Sample transaction data for optimization
            
        Returns:
            Optimized strategy configuration
        """
        optimized_strategy = base_strategy.copy()
        
        try:
            # Analyze data characteristics
            data_stats = self._analyze_data_characteristics(sample_data)
            
            # Optimize algorithm parameters based on data
            algorithms = optimized_strategy.get('algorithms', [])
            
            for algo_config in algorithms:
                if not algo_config.get('enabled', True):
                    continue
                
                algo_type = algo_config['type']
                algo_name = algo_config['name']
                
                # Apply optimization based on algorithm type
                if algo_type == 'statistical':
                    algo_config['config'] = self._optimize_statistical_params(
                        algo_config.get('config', {}), data_stats
                    )
                elif algo_type == 'rule_based':
                    algo_config['config'] = self._optimize_rule_based_params(
                        algo_config.get('config', {}), data_stats
                    )
                elif algo_type == 'ml_based':
                    algo_config['config'] = self._optimize_ml_params(
                        algo_config.get('config', {}), data_stats
                    )
            
            # Optimize global settings
            global_settings = optimized_strategy.get('global_settings', {})
            global_settings = self._optimize_global_settings(global_settings, data_stats)
            optimized_strategy['global_settings'] = global_settings
            
            # Add optimization metadata
            optimized_strategy['_optimization_metadata'] = {
                'optimized_at': datetime.utcnow().isoformat(),
                'data_characteristics': data_stats,
                'optimization_applied': True
            }
            
        except Exception as e:
            # If optimization fails, return original strategy
            optimized_strategy['_optimization_metadata'] = {
                'optimization_failed': True,
                'error': str(e)
            }
        
        return optimized_strategy
    
    def _analyze_data_characteristics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze characteristics of the transaction data."""
        if data.empty:
            return {'empty': True}
        
        # Basic statistics
        stats = {
            'transaction_count': len(data),
            'unique_accounts': data['account_id'].nunique() if 'account_id' in data.columns else 0,
            'date_range_days': None,
            'amount_stats': {},
            'temporal_patterns': {},
            'data_quality': {}
        }
        
        # Amount analysis
        if 'amount' in data.columns:
            amounts = data['amount'].dropna()
            stats['amount_stats'] = {
                'mean': float(amounts.mean()),
                'std': float(amounts.std()),
                'min': float(amounts.min()),
                'max': float(amounts.max()),
                'median': float(amounts.median()),
                'skewness': float(amounts.skew()) if len(amounts) > 1 else 0,
                'outlier_potential': float(amounts.std() / amounts.mean()) if amounts.mean() != 0 else 0
            }
        
        # Temporal analysis
        if 'timestamp' in data.columns:
            timestamps = pd.to_datetime(data['timestamp'])
            date_range = (timestamps.max() - timestamps.min()).days
            stats['date_range_days'] = date_range
            
            # Weekend/weekday distribution
            if 'day_of_week' in data.columns:
                weekend_ratio = data['is_weekend'].mean() if 'is_weekend' in data.columns else 0
                stats['temporal_patterns']['weekend_ratio'] = float(weekend_ratio)
            
            # Business hours distribution
            if 'is_business_hours' in data.columns:
                business_hours_ratio = data['is_business_hours'].mean()
                stats['temporal_patterns']['business_hours_ratio'] = float(business_hours_ratio)
        
        # Data quality assessment
        stats['data_quality'] = {
            'completeness': float((data.notna().sum() / len(data)).mean()),
            'duplicate_rate': float(data.duplicated().mean()),
            'missing_critical_fields': []
        }
        
        # Check for missing critical fields
        critical_fields = ['amount', 'timestamp', 'account_id']
        for field in critical_fields:
            if field not in data.columns or data[field].isna().any():
                stats['data_quality']['missing_critical_fields'].append(field)
        
        return stats
    
    def _optimize_statistical_params(self, config: Dict[str, Any], 
                                   data_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize parameters for statistical algorithms."""
        optimized_config = config.copy()
        
        # Adjust threshold based on data variability
        amount_stats = data_stats.get('amount_stats', {})
        if amount_stats:
            outlier_potential = amount_stats.get('outlier_potential', 1.0)
            
            # If data has low variability, use stricter threshold
            if outlier_potential < 0.5:
                optimized_config['threshold'] = optimized_config.get('threshold', 3.0) * 0.8
            # If data has high variability, use more lenient threshold
            elif outlier_potential > 2.0:
                optimized_config['threshold'] = optimized_config.get('threshold', 3.0) * 1.2
        
        # Adjust window size based on data volume
        transaction_count = data_stats.get('transaction_count', 0)
        if transaction_count < 100:
            optimized_config['window_size'] = min(optimized_config.get('window_size', 30), 10)
        elif transaction_count > 10000:
            optimized_config['window_size'] = max(optimized_config.get('window_size', 30), 100)
        
        return optimized_config
    
    def _optimize_rule_based_params(self, config: Dict[str, Any], 
                                  data_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize parameters for rule-based algorithms."""
        optimized_config = config.copy()
        
        # Adjust weekend thresholds based on actual weekend activity
        temporal_patterns = data_stats.get('temporal_patterns', {})
        weekend_ratio = temporal_patterns.get('weekend_ratio', 0.2)
        
        if weekend_ratio < 0.1:  # Very low weekend activity
            optimized_config['weekend_multiplier'] = optimized_config.get('weekend_multiplier', 0.3) * 0.5
        elif weekend_ratio > 0.3:  # High weekend activity
            optimized_config['weekend_multiplier'] = optimized_config.get('weekend_multiplier', 0.3) * 1.5
        
        return optimized_config
    
    def _optimize_ml_params(self, config: Dict[str, Any], 
                          data_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize parameters for ML-based algorithms."""
        optimized_config = config.copy()
        
        # Adjust contamination rate based on expected anomaly rate
        transaction_count = data_stats.get('transaction_count', 0)
        
        # For smaller datasets, use lower contamination rate
        if transaction_count < 1000:
            optimized_config['contamination'] = min(optimized_config.get('contamination', 0.1), 0.05)
        
        # Adjust number of estimators based on data size
        if transaction_count < 500:
            optimized_config['n_estimators'] = min(optimized_config.get('n_estimators', 100), 50)
        elif transaction_count > 10000:
            optimized_config['n_estimators'] = max(optimized_config.get('n_estimators', 100), 200)
        
        return optimized_config
    
    def _optimize_global_settings(self, global_settings: Dict[str, Any], 
                                data_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize global settings based on data characteristics."""
        optimized_settings = global_settings.copy()
        
        # Adjust confidence threshold based on data quality
        data_quality = data_stats.get('data_quality', {})
        completeness = data_quality.get('completeness', 1.0)
        
        # If data quality is poor, use higher threshold to reduce false positives
        if completeness < 0.8:
            current_threshold = optimized_settings.get('confidence_threshold', 0.7)
            optimized_settings['confidence_threshold'] = min(current_threshold * 1.2, 0.9)
        
        return optimized_settings
    
    async def get_strategy_performance_history(self, strategy_id: str, 
                                             db: AsyncSession) -> Dict[str, Any]:
        """
        Get performance history for a strategy.
        
        Args:
            strategy_id: Strategy ID
            db: Database session
            
        Returns:
            Performance history data
        """
        # TODO: This would query analysis_runs table for historical performance
        # For now, return placeholder data
        
        return {
            'strategy_id': strategy_id,
            'total_runs': 0,
            'successful_runs': 0,
            'average_execution_time': 0.0,
            'average_anomaly_rate': 0.0,
            'performance_trend': [],
            'last_executed': None
        }
    
    def compare_strategies(self, strategy1: Dict[str, Any], 
                          strategy2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two strategies and highlight differences.
        
        Args:
            strategy1: First strategy configuration
            strategy2: Second strategy configuration
            
        Returns:
            Comparison results
        """
        comparison = {
            'identical': False,
            'differences': {
                'algorithms': [],
                'global_settings': []
            },
            'recommendations': []
        }
        
        # Compare algorithms
        algos1 = strategy1.get('algorithms', [])
        algos2 = strategy2.get('algorithms', [])
        
        if len(algos1) != len(algos2):
            comparison['differences']['algorithms'].append(
                f"Different number of algorithms: {len(algos1)} vs {len(algos2)}"
            )
        
        # Compare global settings
        settings1 = strategy1.get('global_settings', {})
        settings2 = strategy2.get('global_settings', {})
        
        for key in set(settings1.keys()) | set(settings2.keys()):
            if settings1.get(key) != settings2.get(key):
                comparison['differences']['global_settings'].append(
                    f"{key}: {settings1.get(key)} vs {settings2.get(key)}"
                )
        
        # Check if identical
        comparison['identical'] = (
            len(comparison['differences']['algorithms']) == 0 and
            len(comparison['differences']['global_settings']) == 0
        )
        
        return comparison 