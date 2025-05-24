"""Isolation Forest algorithm for unsupervised anomaly detection."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from ..base import MLBasedAlgorithm
from ...utils.exceptions import AlgorithmError, AlgorithmConfigurationError


class IsolationForestAlgorithm(MLBasedAlgorithm):
    """
    Isolation Forest algorithm for detecting anomalies using machine learning.
    
    This algorithm uses the scikit-learn IsolationForest implementation to
    identify anomalous transactions based on feature isolation in random subsamples.
    """
    
    __version__ = "1.0.0"
    
    def __init__(self):
        super().__init__("isolation_forest")
        self.model = None
        self.scaler = None
        self.imputer = None
        self.feature_columns = None
        self.is_fitted = False
    
    def detect(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Detect anomalies using Isolation Forest.
        
        Args:
            transactions: Prepared transaction DataFrame
            config: Algorithm configuration
            
        Returns:
            DataFrame with transaction_id, score, confidence, metadata
        """
        # Extract configuration parameters
        contamination = config.get('contamination', 0.1)
        n_estimators = config.get('n_estimators', 100)
        max_samples = config.get('max_samples', 'auto')
        features = config.get('features', ['amount', 'hour', 'day_of_week'])
        account_specific = config.get('account_specific', False)
        min_samples_fit = config.get('min_samples_fit', 50)
        
        results = []
        
        if account_specific:
            # Run separate models for each account
            results = self._detect_account_specific(transactions, config)
        else:
            # Run global model
            results = self._detect_global(transactions, config)
        
        return self.create_result_dataframe(
            [r['transaction_id'] for r in results],
            [r['score'] for r in results],
            [r['confidence'] for r in results],
            [r['metadata'] for r in results]
        )
    
    def _detect_global(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run global Isolation Forest model."""
        results = []
        
        # Prepare features
        feature_matrix, feature_columns = self._prepare_features(transactions, config)
        
        if feature_matrix is None or len(feature_matrix) < config.get('min_samples_fit', 50):
            # Insufficient data for ML model
            for _, transaction in transactions.iterrows():
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.2,
                    'metadata': {
                        'algorithm_type': 'ml_based',
                        'model_type': 'isolation_forest',
                        'analysis_level': 'global',
                        'reason': 'insufficient_data',
                        'available_samples': len(feature_matrix) if feature_matrix is not None else 0
                    }
                })
            return results
        
        # Fit the model
        try:
            model_results = self._fit_and_predict(feature_matrix, config)
        except Exception as e:
            # Model fitting failed
            for _, transaction in transactions.iterrows():
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.1,
                    'metadata': {
                        'algorithm_type': 'ml_based',
                        'model_type': 'isolation_forest',
                        'analysis_level': 'global',
                        'reason': 'model_fitting_failed',
                        'error': str(e)
                    }
                })
            return results
        
        # Map results back to transactions
        for i, (_, transaction) in enumerate(transactions.iterrows()):
            if i < len(model_results['anomaly_scores']):
                score = model_results['anomaly_scores'][i]
                confidence = model_results['confidence_scores'][i]
                
                metadata = {
                    'algorithm_type': 'ml_based',
                    'model_type': 'isolation_forest',
                    'analysis_level': 'global',
                    'features_used': feature_columns,
                    'isolation_score': float(model_results['isolation_scores'][i]),
                    'is_outlier': bool(model_results['outlier_predictions'][i] == -1),
                    'model_params': {
                        'n_estimators': config.get('n_estimators', 100),
                        'contamination': config.get('contamination', 0.1),
                        'max_samples': config.get('max_samples', 'auto')
                    }
                }
                
                results.append({
                    'transaction_id': transaction['id'],
                    'score': score,
                    'confidence': confidence,
                    'metadata': metadata
                })
            else:
                # Fallback for missing results
                results.append({
                    'transaction_id': transaction['id'],
                    'score': 0.1,
                    'confidence': 0.3,
                    'metadata': {
                        'algorithm_type': 'ml_based',
                        'model_type': 'isolation_forest',
                        'analysis_level': 'global',
                        'reason': 'missing_prediction'
                    }
                })
        
        return results
    
    def _detect_account_specific(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run account-specific Isolation Forest models."""
        results = []
        min_samples_fit = config.get('min_samples_fit', 50)
        
        for account_id in transactions['account_id'].unique():
            account_transactions = transactions[transactions['account_id'] == account_id].copy()
            
            if len(account_transactions) < min_samples_fit:
                # Insufficient data for this account
                for _, transaction in account_transactions.iterrows():
                    results.append({
                        'transaction_id': transaction['id'],
                        'score': 0.1,
                        'confidence': 0.3,
                        'metadata': {
                            'algorithm_type': 'ml_based',
                            'model_type': 'isolation_forest',
                            'analysis_level': 'account',
                            'account_id': account_id,
                            'reason': 'insufficient_account_data',
                            'transaction_count': len(account_transactions)
                        }
                    })
                continue
            
            # Prepare features for this account
            feature_matrix, feature_columns = self._prepare_features(account_transactions, config)
            
            if feature_matrix is None:
                # Feature preparation failed
                for _, transaction in account_transactions.iterrows():
                    results.append({
                        'transaction_id': transaction['id'],
                        'score': 0.1,
                        'confidence': 0.2,
                        'metadata': {
                            'algorithm_type': 'ml_based',
                            'model_type': 'isolation_forest',
                            'analysis_level': 'account',
                            'account_id': account_id,
                            'reason': 'feature_preparation_failed'
                        }
                    })
                continue
            
            # Fit account-specific model
            try:
                model_results = self._fit_and_predict(feature_matrix, config)
                
                # Map results to transactions
                for i, (_, transaction) in enumerate(account_transactions.iterrows()):
                    if i < len(model_results['anomaly_scores']):
                        score = model_results['anomaly_scores'][i]
                        confidence = model_results['confidence_scores'][i]
                        
                        metadata = {
                            'algorithm_type': 'ml_based',
                            'model_type': 'isolation_forest',
                            'analysis_level': 'account',
                            'account_id': account_id,
                            'features_used': feature_columns,
                            'isolation_score': float(model_results['isolation_scores'][i]),
                            'is_outlier': bool(model_results['outlier_predictions'][i] == -1),
                            'model_params': {
                                'n_estimators': config.get('n_estimators', 100),
                                'contamination': config.get('contamination', 0.1),
                                'max_samples': config.get('max_samples', 'auto')
                            }
                        }
                        
                        results.append({
                            'transaction_id': transaction['id'],
                            'score': score,
                            'confidence': confidence,
                            'metadata': metadata
                        })
                
            except Exception as e:
                # Model fitting failed for this account
                for _, transaction in account_transactions.iterrows():
                    results.append({
                        'transaction_id': transaction['id'],
                        'score': 0.1,
                        'confidence': 0.1,
                        'metadata': {
                            'algorithm_type': 'ml_based',
                            'model_type': 'isolation_forest',
                            'analysis_level': 'account',
                            'account_id': account_id,
                            'reason': 'model_fitting_failed',
                            'error': str(e)
                        }
                    })
        
        return results
    
    def _prepare_features(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> tuple:
        """Prepare feature matrix for ML model."""
        features = config.get('features', ['amount', 'hour', 'day_of_week'])
        
        # Select available features
        available_features = [f for f in features if f in transactions.columns]
        
        if len(available_features) == 0:
            return None, []
        
        # Extract feature matrix
        feature_matrix = transactions[available_features].copy()
        
        # Add derived features if not already present
        if 'amount_abs' not in feature_matrix.columns and 'amount' in feature_matrix.columns:
            feature_matrix['amount_abs'] = feature_matrix['amount'].abs()
            available_features.append('amount_abs')
        
        if 'amount_log' not in feature_matrix.columns and 'amount' in feature_matrix.columns:
            # Add log-transformed amount (handling negative values)
            feature_matrix['amount_log'] = np.log1p(feature_matrix['amount'].abs())
            available_features.append('amount_log')
        
        # Handle categorical features
        categorical_features = ['day_of_week']
        for cat_feature in categorical_features:
            if cat_feature in feature_matrix.columns:
                # One-hot encode if not already numeric
                if feature_matrix[cat_feature].dtype == 'object':
                    dummies = pd.get_dummies(feature_matrix[cat_feature], prefix=cat_feature)
                    feature_matrix = pd.concat([feature_matrix.drop(cat_feature, axis=1), dummies], axis=1)
                    available_features.remove(cat_feature)
                    available_features.extend(dummies.columns.tolist())
        
        # Convert to numeric
        feature_matrix = feature_matrix.select_dtypes(include=[np.number])
        
        if feature_matrix.empty:
            return None, []
        
        # Handle missing values
        if feature_matrix.isnull().any().any():
            imputer = SimpleImputer(strategy='median')
            feature_matrix = pd.DataFrame(
                imputer.fit_transform(feature_matrix),
                columns=feature_matrix.columns,
                index=feature_matrix.index
            )
        
        return feature_matrix.values, feature_matrix.columns.tolist()
    
    def _fit_and_predict(self, feature_matrix: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fit Isolation Forest model and generate predictions."""
        # Extract parameters
        contamination = config.get('contamination', 0.1)
        n_estimators = config.get('n_estimators', 100)
        max_samples = config.get('max_samples', 'auto')
        random_state = config.get('random_state', 42)
        
        # Scale features
        scaler = StandardScaler()
        feature_matrix_scaled = scaler.fit_transform(feature_matrix)
        
        # Create and fit Isolation Forest
        model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1  # Use all available cores
        )
        
        # Fit model
        model.fit(feature_matrix_scaled)
        
        # Generate predictions
        outlier_predictions = model.predict(feature_matrix_scaled)  # 1 for inliers, -1 for outliers
        isolation_scores = model.decision_function(feature_matrix_scaled)  # Higher scores = more normal
        
        # Convert isolation scores to anomaly scores (0-1 scale)
        # Isolation scores are typically in range [-0.5, 0.5], with lower values being more anomalous
        anomaly_scores = self._convert_isolation_scores_to_anomaly_scores(isolation_scores)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(isolation_scores, outlier_predictions)
        
        return {
            'anomaly_scores': anomaly_scores,
            'confidence_scores': confidence_scores,
            'isolation_scores': isolation_scores,
            'outlier_predictions': outlier_predictions
        }
    
    def _convert_isolation_scores_to_anomaly_scores(self, isolation_scores: np.ndarray) -> np.ndarray:
        """Convert isolation scores to anomaly scores (0-1 scale)."""
        # Isolation scores are typically negative for outliers
        # Lower (more negative) scores indicate higher anomaly
        
        # Invert and normalize to 0-1 scale
        min_score = isolation_scores.min()
        max_score = isolation_scores.max()
        
        if max_score == min_score:
            # All scores are the same
            return np.full_like(isolation_scores, 0.1)
        
        # Invert scores so lower isolation scores become higher anomaly scores
        inverted_scores = max_score - isolation_scores
        
        # Normalize to 0-1 range
        normalized_scores = (inverted_scores - inverted_scores.min()) / (inverted_scores.max() - inverted_scores.min())
        
        # Ensure minimum score of 0.01 and maximum of 0.99
        normalized_scores = np.clip(normalized_scores, 0.01, 0.99)
        
        return normalized_scores
    
    def _calculate_confidence_scores(self, isolation_scores: np.ndarray, 
                                   outlier_predictions: np.ndarray) -> np.ndarray:
        """Calculate confidence scores based on isolation scores and predictions."""
        confidence_scores = np.full_like(isolation_scores, 0.5)
        
        # Higher confidence for more extreme isolation scores
        score_abs = np.abs(isolation_scores)
        max_abs_score = score_abs.max() if score_abs.max() > 0 else 1.0
        
        # Base confidence on distance from center
        base_confidence = score_abs / max_abs_score
        
        # Boost confidence for clear outliers
        outlier_mask = outlier_predictions == -1
        confidence_scores[outlier_mask] = np.clip(base_confidence[outlier_mask] + 0.3, 0.1, 0.95)
        
        # Normal confidence for inliers
        inlier_mask = outlier_predictions == 1
        confidence_scores[inlier_mask] = np.clip(base_confidence[inlier_mask] + 0.1, 0.1, 0.9)
        
        return confidence_scores
    
    def fit(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> None:
        """
        Fit the Isolation Forest model (for pre-training scenarios).
        
        Args:
            transactions: Training transaction DataFrame
            config: Algorithm configuration
        """
        # Prepare features
        feature_matrix, feature_columns = self._prepare_features(transactions, config)
        
        if feature_matrix is None or len(feature_matrix) < config.get('min_samples_fit', 50):
            raise AlgorithmError("Insufficient data to fit Isolation Forest model")
        
        # Store feature columns
        self.feature_columns = feature_columns
        
        # Scale features
        self.scaler = StandardScaler()
        feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
        
        # Create and fit model
        contamination = config.get('contamination', 0.1)
        n_estimators = config.get('n_estimators', 100)
        max_samples = config.get('max_samples', 'auto')
        random_state = config.get('random_state', 42)
        
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1
        )
        
        self.model.fit(feature_matrix_scaled)
        self.is_fitted = True
    
    def predict(self, transactions: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Predict anomaly scores using pre-fitted model.
        
        Args:
            transactions: Transaction DataFrame for prediction
            config: Algorithm configuration
            
        Returns:
            DataFrame with transaction_id, score, confidence, metadata
        """
        if not self.is_fitted or self.model is None:
            raise AlgorithmError("Model must be fitted before prediction")
        
        # Prepare features
        feature_matrix, _ = self._prepare_features(transactions, config)
        
        if feature_matrix is None:
            raise AlgorithmError("Feature preparation failed")
        
        # Ensure feature compatibility
        if feature_matrix.shape[1] != len(self.feature_columns):
            raise AlgorithmError("Feature dimension mismatch")
        
        # Scale features using fitted scaler
        feature_matrix_scaled = self.scaler.transform(feature_matrix)
        
        # Generate predictions
        outlier_predictions = self.model.predict(feature_matrix_scaled)
        isolation_scores = self.model.decision_function(feature_matrix_scaled)
        
        # Convert to anomaly scores
        anomaly_scores = self._convert_isolation_scores_to_anomaly_scores(isolation_scores)
        confidence_scores = self._calculate_confidence_scores(isolation_scores, outlier_predictions)
        
        # Create results
        results = []
        for i, (_, transaction) in enumerate(transactions.iterrows()):
            metadata = {
                'algorithm_type': 'ml_based',
                'model_type': 'isolation_forest',
                'features_used': self.feature_columns,
                'isolation_score': float(isolation_scores[i]),
                'is_outlier': bool(outlier_predictions[i] == -1),
                'model_fitted': True
            }
            
            results.append({
                'transaction_id': transaction['id'],
                'score': anomaly_scores[i],
                'confidence': confidence_scores[i],
                'metadata': metadata
            })
        
        return self.create_result_dataframe(
            [r['transaction_id'] for r in results],
            [r['score'] for r in results],
            [r['confidence'] for r in results],
            [r['metadata'] for r in results]
        )
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance (not applicable for Isolation Forest)."""
        # Isolation Forest doesn't provide traditional feature importance
        # Could implement permutation importance if needed
        return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate algorithm configuration."""
        # Check contamination
        if 'contamination' in config:
            contamination = config['contamination']
            if not isinstance(contamination, (int, float)) or not 0 < contamination <= 0.5:
                raise AlgorithmConfigurationError("contamination must be between 0 and 0.5")
        
        # Check n_estimators
        if 'n_estimators' in config:
            n_estimators = config['n_estimators']
            if not isinstance(n_estimators, int) or n_estimators < 1:
                raise AlgorithmConfigurationError("n_estimators must be a positive integer")
        
        # Check max_samples
        if 'max_samples' in config:
            max_samples = config['max_samples']
            if max_samples != 'auto':
                if isinstance(max_samples, float):
                    if not 0 < max_samples <= 1:
                        raise AlgorithmConfigurationError("max_samples as float must be between 0 and 1")
                elif isinstance(max_samples, int):
                    if max_samples < 1:
                        raise AlgorithmConfigurationError("max_samples as int must be positive")
                else:
                    raise AlgorithmConfigurationError("max_samples must be 'auto', float, or int")
        
        # Check features
        if 'features' in config:
            features = config['features']
            if not isinstance(features, list) or len(features) == 0:
                raise AlgorithmConfigurationError("features must be a non-empty list")
        
        # Check min_samples_fit
        if 'min_samples_fit' in config:
            min_samples = config['min_samples_fit']
            if not isinstance(min_samples, int) or min_samples < 10:
                raise AlgorithmConfigurationError("min_samples_fit must be an integer >= 10")
        
        return True
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'contamination': 0.1,
            'n_estimators': 100,
            'max_samples': 'auto',
            'features': ['amount', 'hour', 'day_of_week'],
            'account_specific': False,
            'min_samples_fit': 50,
            'random_state': 42
        }
    
    def get_minimum_transactions(self) -> int:
        """Minimum number of transactions required."""
        return 50  # Need sufficient data for meaningful ML model 