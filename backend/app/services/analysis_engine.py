"""Analysis engine service for coordinating anomaly detection algorithms."""

import pandas as pd
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..algorithms import AlgorithmRegistry
from ..models.transaction import Transaction
from ..models.analysis import AnalysisRun
from ..models.strategy import Strategy
from ..utils.exceptions import AnalysisError, AlgorithmError
from ..config import get_settings

settings = get_settings()


class AnalysisEngineService:
    """Service for coordinating and executing anomaly detection analysis."""
    
    def __init__(self):
        self.algorithm_registry = AlgorithmRegistry()
    
    async def run_analysis(self, analysis_run_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Execute anomaly detection analysis for a given analysis run.
        
        Args:
            analysis_run_id: ID of the analysis run to execute
            db: Database session
            
        Returns:
            Analysis results dictionary
            
        Raises:
            AnalysisError: If analysis execution fails
        """
        try:
            # Get analysis run details
            analysis_run = await self._get_analysis_run(analysis_run_id, db)
            if not analysis_run:
                raise AnalysisError(f"Analysis run {analysis_run_id} not found")
            
            # Update status to running
            analysis_run.status = "running"
            analysis_run.started_at = datetime.utcnow()
            await db.commit()
            
            # Get transactions for analysis
            transactions_df = await self._load_transactions(analysis_run.upload_id, db)
            if transactions_df.empty:
                raise AnalysisError("No transactions found for analysis")
            
            # Get strategy configuration
            strategy_config = await self._get_strategy_config(analysis_run.strategy_id, db)
            
            # Execute algorithms
            results = await self._execute_algorithms(transactions_df, strategy_config)
            
            # Aggregate results
            final_results = self._aggregate_results(results, strategy_config)
            
            # Store results in database
            await self._store_results(analysis_run_id, final_results, db)
            
            # Update analysis run status
            analysis_run.status = "completed"
            analysis_run.completed_at = datetime.utcnow()
            analysis_run.metadata.update({
                "execution_summary": {
                    "transactions_processed": len(transactions_df),
                    "algorithms_executed": len(results),
                    "anomalies_detected": final_results.get("anomaly_count", 0),
                    "execution_time_seconds": (datetime.utcnow() - analysis_run.started_at).total_seconds()
                }
            })
            await db.commit()
            
            return final_results
            
        except Exception as e:
            # Update analysis run with error status
            try:
                analysis_run.status = "failed"
                analysis_run.completed_at = datetime.utcnow()
                analysis_run.error_message = str(e)
                await db.commit()
            except:
                pass  # Don't fail on status update failure
            
            raise AnalysisError(f"Analysis execution failed: {str(e)}")
    
    async def _get_analysis_run(self, analysis_run_id: str, db: AsyncSession) -> Optional[AnalysisRun]:
        """Get analysis run from database."""
        result = await db.execute(
            select(AnalysisRun).where(AnalysisRun.id == analysis_run_id)
        )
        return result.scalar_one_or_none()
    
    async def _load_transactions(self, upload_id: str, db: AsyncSession) -> pd.DataFrame:
        """Load transactions for analysis."""
        result = await db.execute(
            select(Transaction).where(Transaction.upload_id == upload_id)
        )
        transactions = result.scalars().all()
        
        if not transactions:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for transaction in transactions:
            data.append({
                'id': str(transaction.id),
                'amount': float(transaction.amount),
                'timestamp': transaction.timestamp,
                'account_id': transaction.account_id,
                'external_transaction_id': transaction.external_transaction_id,
                'raw_data': transaction.raw_data,
                'processed_data': transaction.processed_data or {}
            })
        
        df = pd.DataFrame(data)
        
        # Add derived features if not present
        if 'day_of_week' not in df.columns:
            df = self._add_basic_features(df)
        
        return df
    
    def _add_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add basic features needed for analysis if not present."""
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month
        df['day'] = df['timestamp'].dt.day
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6])
        df['amount_abs'] = df['amount'].abs()
        
        return df
    
    async def _get_strategy_config(self, strategy_id: Optional[str], db: AsyncSession) -> Dict[str, Any]:
        """Get strategy configuration or use default."""
        if strategy_id:
            result = await db.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategy = result.scalar_one_or_none()
            
            if strategy:
                return strategy.configuration
        
        # Return default strategy configuration
        return {
            "algorithms": [
                {
                    "type": "statistical",
                    "name": "zscore",
                    "enabled": True,
                    "config": {
                        "threshold": 3.0,
                        "window_size": 30
                    }
                }
            ],
            "global_settings": {
                "aggregation_method": "max",
                "confidence_threshold": 0.7
            }
        }
    
    async def _execute_algorithms(self, transactions_df: pd.DataFrame, 
                                strategy_config: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Execute all enabled algorithms in the strategy."""
        results = {}
        algorithms_config = strategy_config.get("algorithms", [])
        
        for algo_config in algorithms_config:
            if not algo_config.get("enabled", True):
                continue
            
            algo_type = algo_config["type"]
            algo_name = algo_config["name"]
            algo_params = algo_config.get("config", {})
            
            try:
                # Get algorithm instance
                algorithm = self.algorithm_registry.get_algorithm(algo_type, algo_name)
                
                # Prepare data
                prepared_data = algorithm.prepare_data(transactions_df)
                
                # Validate input data
                algorithm.validate_input_data(prepared_data)
                
                # Execute algorithm
                start_time = time.time()
                algorithm_results = algorithm.detect(prepared_data, algo_params)
                execution_time = time.time() - start_time
                
                # Add execution metadata
                algorithm_results['algorithm_type'] = algo_type
                algorithm_results['algorithm_name'] = algo_name
                algorithm_results['execution_time'] = execution_time
                
                results[f"{algo_type}.{algo_name}"] = algorithm_results
                
                # Log execution
                log_entry = algorithm.log_execution(
                    transactions_count=len(prepared_data),
                    execution_time=execution_time,
                    anomalies_found=len(algorithm_results[algorithm_results['score'] > 0.5]),
                    config=algo_params
                )
                
                print(f"Algorithm {algo_type}.{algo_name} completed: {log_entry}")
                
            except Exception as e:
                print(f"Algorithm {algo_type}.{algo_name} failed: {str(e)}")
                # Continue with other algorithms
                continue
        
        if not results:
            raise AnalysisError("No algorithms executed successfully")
        
        return results
    
    def _aggregate_results(self, algorithm_results: Dict[str, pd.DataFrame], 
                          strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from multiple algorithms."""
        global_settings = strategy_config.get("global_settings", {})
        aggregation_method = global_settings.get("aggregation_method", "max")
        confidence_threshold = global_settings.get("confidence_threshold", 0.7)
        
        # Combine all algorithm results
        all_scores = []
        transaction_scores = {}
        
        for algo_key, results_df in algorithm_results.items():
            for _, row in results_df.iterrows():
                transaction_id = row['transaction_id']
                score = row['score']
                confidence = row.get('confidence', 1.0)
                
                if transaction_id not in transaction_scores:
                    transaction_scores[transaction_id] = {
                        'scores': [],
                        'confidences': [],
                        'algorithms': []
                    }
                
                transaction_scores[transaction_id]['scores'].append(score)
                transaction_scores[transaction_id]['confidences'].append(confidence)
                transaction_scores[transaction_id]['algorithms'].append(algo_key)
        
        # Aggregate scores per transaction
        aggregated_scores = []
        anomaly_count = 0
        
        for transaction_id, data in transaction_scores.items():
            scores = data['scores']
            confidences = data['confidences']
            algorithms = data['algorithms']
            
            # Apply aggregation method
            if aggregation_method == "max":
                final_score = max(scores)
                final_confidence = confidences[scores.index(final_score)]
            elif aggregation_method == "min":
                final_score = min(scores)
                final_confidence = confidences[scores.index(final_score)]
            elif aggregation_method == "mean":
                final_score = sum(scores) / len(scores)
                final_confidence = sum(confidences) / len(confidences)
            elif aggregation_method == "weighted_average":
                weights = global_settings.get("weights", {})
                weighted_scores = []
                weighted_confidences = []
                total_weight = 0
                
                for i, algo_key in enumerate(algorithms):
                    algo_type = algo_key.split('.')[0]
                    weight = weights.get(algo_type, 1.0)
                    weighted_scores.append(scores[i] * weight)
                    weighted_confidences.append(confidences[i] * weight)
                    total_weight += weight
                
                final_score = sum(weighted_scores) / total_weight if total_weight > 0 else 0
                final_confidence = sum(weighted_confidences) / total_weight if total_weight > 0 else 0
            else:
                final_score = max(scores)  # Default to max
                final_confidence = confidences[scores.index(final_score)]
            
            # Check if anomaly based on threshold
            is_anomaly = final_score >= confidence_threshold
            if is_anomaly:
                anomaly_count += 1
            
            aggregated_scores.append({
                'transaction_id': transaction_id,
                'final_score': final_score,
                'final_confidence': final_confidence,
                'is_anomaly': is_anomaly,
                'algorithms_used': algorithms,
                'individual_scores': dict(zip(algorithms, scores))
            })
        
        return {
            'transaction_scores': aggregated_scores,
            'anomaly_count': anomaly_count,
            'total_transactions': len(transaction_scores),
            'anomaly_rate': anomaly_count / len(transaction_scores) if transaction_scores else 0,
            'algorithms_executed': list(algorithm_results.keys()),
            'aggregation_method': aggregation_method,
            'confidence_threshold': confidence_threshold
        }
    
    async def _store_results(self, analysis_run_id: str, results: Dict[str, Any], 
                           db: AsyncSession) -> None:
        """Store analysis results in database."""
        # TODO: Implement storage to anomaly_scores and rule_flags tables
        # This will be implemented when those models are properly integrated
        
        # For now, we'll store the results in the analysis run metadata
        result = await db.execute(
            select(AnalysisRun).where(AnalysisRun.id == analysis_run_id)
        )
        analysis_run = result.scalar_one_or_none()
        
        if analysis_run:
            analysis_run.metadata['results'] = {
                'summary': {
                    'anomaly_count': results['anomaly_count'],
                    'total_transactions': results['total_transactions'],
                    'anomaly_rate': results['anomaly_rate'],
                    'algorithms_executed': results['algorithms_executed']
                },
                'configuration': {
                    'aggregation_method': results['aggregation_method'],
                    'confidence_threshold': results['confidence_threshold']
                }
            }
            await db.commit()
    
    def validate_strategy_compatibility(self, strategy_config: Dict[str, Any], 
                                      transactions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate that the strategy can be executed with the given data.
        
        Args:
            strategy_config: Strategy configuration
            transactions_df: Transaction data
            
        Returns:
            Validation results
        """
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'algorithm_checks': {}
        }
        
        algorithms_config = strategy_config.get("algorithms", [])
        
        for algo_config in algorithms_config:
            if not algo_config.get("enabled", True):
                continue
            
            algo_type = algo_config["type"]
            algo_name = algo_config["name"]
            algo_params = algo_config.get("config", {})
            
            try:
                # Get algorithm instance
                algorithm = self.algorithm_registry.get_algorithm(algo_type, algo_name)
                
                # Check minimum data requirements
                min_transactions = algorithm.get_minimum_transactions()
                if len(transactions_df) < min_transactions:
                    validation_results['warnings'].append(
                        f"Algorithm {algo_type}.{algo_name} requires at least {min_transactions} "
                        f"transactions, but only {len(transactions_df)} available"
                    )
                
                # Validate configuration
                algorithm.validate_config(algo_params)
                
                validation_results['algorithm_checks'][f"{algo_type}.{algo_name}"] = {
                    'valid': True,
                    'min_transactions_met': len(transactions_df) >= min_transactions
                }
                
            except Exception as e:
                validation_results['valid'] = False
                validation_results['errors'].append(
                    f"Algorithm {algo_type}.{algo_name} validation failed: {str(e)}"
                )
                validation_results['algorithm_checks'][f"{algo_type}.{algo_name}"] = {
                    'valid': False,
                    'error': str(e)
                }
        
        return validation_results 