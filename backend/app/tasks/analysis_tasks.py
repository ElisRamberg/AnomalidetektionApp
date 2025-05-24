"""Celery tasks for analysis operations."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..celery_app import celery_app
from ..database import get_async_db
from ..models.analysis import AnalysisRun
from ..models.transaction import Transaction
from ..models.strategy import Strategy
from ..services.analysis_engine import AnalysisEngineService
from ..utils.exceptions import AnalysisError
from ..config import get_settings

settings = get_settings()


@celery_app.task(bind=True)
def run_anomaly_detection(self, analysis_run_id: str) -> Dict[str, Any]:
    """
    Execute anomaly detection analysis in the background.
    
    Args:
        analysis_run_id: ID of the analysis run to execute
        
    Returns:
        Analysis results dictionary
    """
    return asyncio.run(_run_anomaly_detection_async(self, analysis_run_id))


async def _run_anomaly_detection_async(task, analysis_run_id: str) -> Dict[str, Any]:
    """Async implementation of anomaly detection."""
    analysis_engine = AnalysisEngineService()
    
    async for db in get_async_db():
        try:
            # Update task status
            task.update_state(state='PROGRESS', meta={'status': 'Initializing analysis'})
            
            # Get analysis run
            result = await db.execute(
                select(AnalysisRun).where(AnalysisRun.id == analysis_run_id)
            )
            analysis_run = result.scalar_one_or_none()
            
            if not analysis_run:
                raise AnalysisError(f"Analysis run {analysis_run_id} not found")
            
            # Update analysis run status
            analysis_run.status = "running"
            analysis_run.started_at = datetime.utcnow()
            analysis_run.metadata['celery_task_id'] = task.request.id
            await db.commit()
            
            task.update_state(state='PROGRESS', meta={'status': 'Loading transactions'})
            
            # Load transactions
            transactions_result = await db.execute(
                select(Transaction).where(Transaction.upload_id == analysis_run.upload_id)
            )
            transactions = transactions_result.scalars().all()
            
            if not transactions:
                raise AnalysisError("No transactions found for analysis")
            
            # Convert to DataFrame for processing
            import pandas as pd
            
            transaction_data = []
            for transaction in transactions:
                data = {
                    'id': str(transaction.id),
                    'amount': float(transaction.amount),
                    'timestamp': transaction.timestamp,
                    'account_id': transaction.account_id,
                    'external_transaction_id': transaction.external_transaction_id,
                    'raw_data': transaction.raw_data,
                }
                
                # Add processed data if available
                if transaction.processed_data:
                    data.update(transaction.processed_data)
                
                transaction_data.append(data)
            
            transactions_df = pd.DataFrame(transaction_data)
            
            task.update_state(
                state='PROGRESS', 
                meta={
                    'status': 'Getting strategy configuration',
                    'transactions_loaded': len(transactions_df)
                }
            )
            
            # Get strategy configuration
            strategy_config = await _get_strategy_config(analysis_run.strategy_id, db)
            
            task.update_state(state='PROGRESS', meta={'status': 'Executing algorithms'})
            
            # Execute algorithms
            algorithms_config = strategy_config.get("algorithms", [])
            enabled_algorithms = [algo for algo in algorithms_config if algo.get("enabled", True)]
            
            results = {}
            algorithm_count = len(enabled_algorithms)
            
            for i, algo_config in enumerate(enabled_algorithms):
                algo_type = algo_config["type"]
                algo_name = algo_config["name"]
                algo_params = algo_config.get("config", {})
                
                task.update_state(
                    state='PROGRESS',
                    meta={
                        'status': f'Running algorithm {i+1}/{algorithm_count}: {algo_type}.{algo_name}',
                        'algorithm_progress': (i / algorithm_count) * 100
                    }
                )
                
                try:
                    # Get algorithm instance
                    from ..algorithms import AlgorithmRegistry
                    algorithm_registry = AlgorithmRegistry()
                    algorithm = algorithm_registry.get_algorithm(algo_type, algo_name)
                    
                    # Prepare data
                    prepared_data = algorithm.prepare_data(transactions_df)
                    
                    # Execute algorithm
                    algorithm_results = algorithm.detect(prepared_data, algo_params)
                    
                    results[f"{algo_type}.{algo_name}"] = {
                        'results_df': algorithm_results,
                        'execution_time': 0,  # Could be tracked if needed
                        'anomalies_found': len(algorithm_results[algorithm_results['score'] > 0.5])
                    }
                    
                except Exception as e:
                    print(f"Algorithm {algo_type}.{algo_name} failed: {str(e)}")
                    continue
            
            if not results:
                raise AnalysisError("No algorithms executed successfully")
            
            task.update_state(state='PROGRESS', meta={'status': 'Aggregating results'})
            
            # Aggregate results
            final_results = _aggregate_algorithm_results(results, strategy_config)
            
            task.update_state(state='PROGRESS', meta={'status': 'Storing results'})
            
            # Store results (placeholder for now - would integrate with anomaly_scores table)
            analysis_run.metadata['results'] = {
                'summary': {
                    'anomaly_count': final_results.get('anomaly_count', 0),
                    'total_transactions': len(transactions_df),
                    'anomaly_rate': final_results.get('anomaly_rate', 0),
                    'algorithms_executed': list(results.keys())
                },
                'detailed_results': final_results
            }
            
            # Update analysis run with success
            analysis_run.status = "completed"
            analysis_run.completed_at = datetime.utcnow()
            analysis_run.metadata.update({
                'execution_summary': {
                    'transactions_processed': len(transactions_df),
                    'algorithms_executed': len(results),
                    'anomalies_detected': final_results.get('anomaly_count', 0),
                    'execution_time_seconds': (datetime.utcnow() - analysis_run.started_at).total_seconds()
                }
            })
            await db.commit()
            
            return {
                'status': 'completed',
                'analysis_run_id': analysis_run_id,
                'transactions_processed': len(transactions_df),
                'anomalies_detected': final_results.get('anomaly_count', 0),
                'algorithms_executed': len(results),
                'results_summary': final_results
            }
            
        except Exception as e:
            # Update analysis run with error status
            try:
                analysis_run.status = "failed"
                analysis_run.completed_at = datetime.utcnow()
                analysis_run.error_message = str(e)
                await db.commit()
            except:
                pass  # Don't fail on status update failure
            
            # Re-raise for Celery to handle
            raise AnalysisError(f"Analysis execution failed: {str(e)}")


async def _get_strategy_config(strategy_id: str, db: AsyncSession) -> Dict[str, Any]:
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


def _aggregate_algorithm_results(algorithm_results: Dict[str, Any], 
                               strategy_config: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate results from multiple algorithms."""
    global_settings = strategy_config.get("global_settings", {})
    aggregation_method = global_settings.get("aggregation_method", "max")
    confidence_threshold = global_settings.get("confidence_threshold", 0.7)
    
    # Combine all algorithm results
    transaction_scores = {}
    
    for algo_key, algo_data in algorithm_results.items():
        results_df = algo_data['results_df']
        
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


@celery_app.task(bind=True)
def cancel_analysis_run(self, analysis_run_id: str) -> Dict[str, Any]:
    """
    Cancel a running analysis.
    
    Args:
        analysis_run_id: ID of the analysis run to cancel
        
    Returns:
        Cancellation results
    """
    return asyncio.run(_cancel_analysis_run_async(analysis_run_id))


async def _cancel_analysis_run_async(analysis_run_id: str) -> Dict[str, Any]:
    """Async implementation of analysis cancellation."""
    async for db in get_async_db():
        try:
            # Get analysis run
            result = await db.execute(
                select(AnalysisRun).where(AnalysisRun.id == analysis_run_id)
            )
            analysis_run = result.scalar_one_or_none()
            
            if not analysis_run:
                return {'error': f'Analysis run {analysis_run_id} not found'}
            
            if analysis_run.status not in ["pending", "running"]:
                return {'error': f'Cannot cancel analysis with status: {analysis_run.status}'}
            
            # Update status
            analysis_run.status = "cancelled"
            analysis_run.completed_at = datetime.utcnow()
            analysis_run.error_message = "Analysis cancelled by user"
            
            await db.commit()
            
            return {
                'status': 'cancelled',
                'analysis_run_id': analysis_run_id,
                'cancelled_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}


@celery_app.task
def cleanup_old_analyses() -> Dict[str, Any]:
    """
    Periodic task to clean up old analysis runs and results.
    
    Returns:
        Cleanup results
    """
    return asyncio.run(_cleanup_old_analyses_async())


async def _cleanup_old_analyses_async() -> Dict[str, Any]:
    """Async implementation of analysis cleanup."""
    cutoff_date = datetime.utcnow() - timedelta(days=settings.analysis_retention_days or 90)
    analyses_deleted = 0
    errors = []
    
    async for db in get_async_db():
        try:
            # Find old analysis runs
            result = await db.execute(
                select(AnalysisRun).where(AnalysisRun.started_at < cutoff_date)
            )
            old_analyses = result.scalars().all()
            
            for analysis in old_analyses:
                try:
                    # Delete analysis run record (results are stored in metadata for now)
                    await db.delete(analysis)
                    analyses_deleted += 1
                    
                except Exception as e:
                    errors.append(f"Failed to cleanup analysis {analysis.id}: {str(e)}")
            
            await db.commit()
            
            return {
                'analyses_deleted': analyses_deleted,
                'errors': errors,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'analyses_deleted': analyses_deleted
            }


@celery_app.task
def get_analysis_stats() -> Dict[str, Any]:
    """
    Get statistics about analysis operations.
    
    Returns:
        Analysis statistics
    """
    return asyncio.run(_get_analysis_stats_async())


async def _get_analysis_stats_async() -> Dict[str, Any]:
    """Async implementation of analysis stats collection."""
    async for db in get_async_db():
        try:
            # Get analysis run statistics
            all_analyses_result = await db.execute(select(AnalysisRun))
            all_analyses = all_analyses_result.scalars().all()
            
            # Count by status
            status_counts = {}
            execution_times = []
            anomaly_rates = []
            
            for analysis in all_analyses:
                status = analysis.status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Calculate execution time if available
                if analysis.completed_at and analysis.started_at:
                    execution_time = (analysis.completed_at - analysis.started_at).total_seconds()
                    execution_times.append(execution_time)
                
                # Get anomaly rate if available
                if analysis.metadata and 'results' in analysis.metadata:
                    results = analysis.metadata['results']
                    if 'summary' in results:
                        anomaly_rate = results['summary'].get('anomaly_rate', 0)
                        anomaly_rates.append(anomaly_rate)
            
            return {
                'total_analyses': len(all_analyses),
                'status_breakdown': status_counts,
                'average_execution_time_seconds': sum(execution_times) / len(execution_times) if execution_times else 0,
                'average_anomaly_rate': sum(anomaly_rates) / len(anomaly_rates) if anomaly_rates else 0,
                'stats_generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'stats_generated_at': datetime.utcnow().isoformat()
            }


@celery_app.task
def validate_strategy_async(strategy_config: Dict[str, Any], 
                           sample_upload_id: str = None) -> Dict[str, Any]:
    """
    Validate a strategy configuration asynchronously.
    
    Args:
        strategy_config: Strategy configuration to validate
        sample_upload_id: Optional upload ID for testing with real data
        
    Returns:
        Validation results
    """
    return asyncio.run(_validate_strategy_async_impl(strategy_config, sample_upload_id))


async def _validate_strategy_async_impl(strategy_config: Dict[str, Any], 
                                      sample_upload_id: str) -> Dict[str, Any]:
    """Async implementation of strategy validation."""
    from ..services.strategy_manager import StrategyManagerService
    
    strategy_manager = StrategyManagerService()
    
    try:
        # Validate configuration structure
        validation_results = strategy_manager.validate_strategy_configuration(strategy_config)
        
        # If sample data provided, test compatibility
        if sample_upload_id and validation_results.get('valid', False):
            async for db in get_async_db():
                # Load sample transactions
                transactions_result = await db.execute(
                    select(Transaction).where(Transaction.upload_id == sample_upload_id).limit(100)
                )
                transactions = transactions_result.scalars().all()
                
                if transactions:
                    import pandas as pd
                    
                    # Convert to DataFrame
                    transaction_data = []
                    for transaction in transactions:
                        data = {
                            'id': str(transaction.id),
                            'amount': float(transaction.amount),
                            'timestamp': transaction.timestamp,
                            'account_id': transaction.account_id,
                        }
                        if transaction.processed_data:
                            data.update(transaction.processed_data)
                        transaction_data.append(data)
                    
                    transactions_df = pd.DataFrame(transaction_data)
                    
                    # Test strategy compatibility
                    from ..services.analysis_engine import AnalysisEngineService
                    analysis_engine = AnalysisEngineService()
                    
                    compatibility_results = analysis_engine.validate_strategy_compatibility(
                        strategy_config, transactions_df
                    )
                    
                    validation_results['compatibility_test'] = compatibility_results
        
        return validation_results
        
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'validation_type': 'async_strategy_validation'
        } 