"""
C.8 Normalizer Pipeline metrics collection and monitoring.

Features:
- Extend existing G.1 monitoring infrastructure
- Add C.8 specific metrics for normalizer pipeline
- LLM fallback metrics integration
- Pipeline performance tracking
- Error recovery metrics
"""

import time
from typing import Dict, Any, Optional, List
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from structlog import get_logger

from .pipeline_metrics import PipelineMetrics

logger = get_logger(__name__)


class NormalizerPipelineMetrics(PipelineMetrics):
    """
    Extended metrics collection for C.8 normalizer pipeline.
    
    Extends existing G.1 PipelineMetrics with:
    - Normalizer pipeline execution metrics
    - LLM fallback usage and performance
    - Parser success rates and confidence scores
    - Error recovery metrics
    - Transaction management metrics
    """
    
    def __init__(self, prometheus_port: int = 8000):
        """Initialize normalizer pipeline metrics service."""
        super().__init__(prometheus_port)
        
        # C.8 Normalizer Pipeline Metrics
        self.normalizer_pipeline_duration = Histogram(
            'normalizer_pipeline_duration_seconds',
            'Normalizer pipeline execution time',
            ['execution_id', 'stage'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.parser_success_rate = Gauge(
            'parser_success_rate',
            'Success rate per parser',
            ['parser_name', 'execution_id'],
            registry=self.registry
        )
        
        self.parser_confidence = Histogram(
            'parser_confidence_score',
            'Parser confidence scores',
            ['parser_name', 'execution_id'],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        self.llm_fallback_usage = Counter(
            'llm_fallback_total',
            'LLM fallback usage count',
            ['field_name', 'execution_id', 'success'],
            registry=self.registry
        )
        
        self.llm_fallback_duration = Histogram(
            'llm_fallback_duration_seconds',
            'LLM fallback execution time',
            ['field_name', 'execution_id'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.llm_confidence = Histogram(
            'llm_confidence_score',
            'LLM confidence scores',
            ['field_name', 'execution_id'],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        self.pipeline_confidence = Histogram(
            'pipeline_confidence_score',
            'Pipeline confidence scores',
            ['execution_id', 'stage'],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        self.error_recovery_attempts = Counter(
            'error_recovery_attempts_total',
            'Error recovery attempts',
            ['parser_name', 'error_type', 'success'],
            registry=self.registry
        )
        
        self.transaction_operations = Counter(
            'transaction_operations_total',
            'Transaction operations',
            ['operation_type', 'success', 'execution_id'],
            registry=self.registry
        )
        
        self.transaction_duration = Histogram(
            'transaction_duration_seconds',
            'Transaction duration',
            ['execution_id', 'boundary_type'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.pipeline_errors = Counter(
            'pipeline_errors_total',
            'Pipeline errors',
            ['error_type', 'stage', 'execution_id'],
            registry=self.registry
        )
        
        self.pipeline_warnings = Counter(
            'pipeline_warnings_total',
            'Pipeline warnings',
            ['warning_type', 'stage', 'execution_id'],
            registry=self.registry
        )
        
        self.batch_processing_metrics = Gauge(
            'batch_processing_metrics',
            'Batch processing metrics',
            ['metric_type', 'execution_id'],
            registry=self.registry
        )
        
        logger.info("C.8 Normalizer Pipeline metrics initialized")
    
    def record_pipeline_execution(self, 
                                 execution_id: str, 
                                 duration: float, 
                                 stage: str,
                                 parsers_used: List[str],
                                 llm_fallback_used: bool):
        """Record normalizer pipeline execution metrics."""
        self.normalizer_pipeline_duration.labels(
            execution_id=execution_id,
            stage=stage
        ).observe(duration)
        
        # Record batch processing metrics
        self.batch_processing_metrics.labels(
            metric_type='parsers_used',
            execution_id=execution_id
        ).set(len(parsers_used))
        
        if llm_fallback_used:
            self.llm_fallback_usage.labels(
                field_name='batch',
                execution_id=execution_id,
                success=True
            ).inc()
        
        logger.debug("Pipeline execution recorded", 
                    execution_id=execution_id,
                    duration=duration,
                    stage=stage)
    
    def record_parser_success(self, 
                             parser_name: str, 
                             execution_id: str, 
                             success: bool, 
                             confidence: float):
        """Record individual parser success metrics."""
        self.parser_success_rate.labels(
            parser_name=parser_name,
            execution_id=execution_id
        ).set(1.0 if success else 0.0)
        
        self.parser_confidence.labels(
            parser_name=parser_name,
            execution_id=execution_id
        ).observe(confidence)
        
        logger.debug("Parser success recorded", 
                    parser=parser_name,
                    execution_id=execution_id,
                    success=success,
                    confidence=confidence)
    
    def record_llm_fallback(self, 
                           field_name: str, 
                           execution_id: str, 
                           duration: float, 
                           confidence: float, 
                           success: bool):
        """Record LLM fallback metrics."""
        self.llm_fallback_usage.labels(
            field_name=field_name,
            execution_id=execution_id,
            success=success
        ).inc()
        
        self.llm_fallback_duration.labels(
            field_name=field_name,
            execution_id=execution_id
        ).observe(duration)
        
        self.llm_confidence.labels(
            field_name=field_name,
            execution_id=execution_id
        ).observe(confidence)
        
        logger.debug("LLM fallback recorded", 
                    field=field_name,
                    execution_id=execution_id,
                    duration=duration,
                    confidence=confidence,
                    success=success)
    
    def record_pipeline_confidence(self, 
                                   execution_id: str, 
                                   stage: str, 
                                   confidence: float):
        """Record pipeline confidence metrics."""
        self.pipeline_confidence.labels(
            execution_id=execution_id,
            stage=stage
        ).observe(confidence)
        
        logger.debug("Pipeline confidence recorded", 
                    execution_id=execution_id,
                    stage=stage,
                    confidence=confidence)
    
    def record_error_recovery(self, 
                             parser_name: str, 
                             error_type: str, 
                             success: bool):
        """Record error recovery metrics."""
        self.error_recovery_attempts.labels(
            parser_name=parser_name,
            error_type=error_type,
            success=success
        ).inc()
        
        logger.debug("Error recovery recorded", 
                    parser=parser_name,
                    error_type=error_type,
                    success=success)
    
    def record_transaction_operation(self, 
                                   execution_id: str, 
                                   operation_type: str, 
                                   success: bool, 
                                   duration: float,
                                   boundary_type: str = "pipeline"):
        """Record transaction operation metrics."""
        self.transaction_operations.labels(
            operation_type=operation_type,
            success=success,
            execution_id=execution_id
        ).inc()
        
        self.transaction_duration.labels(
            execution_id=execution_id,
            boundary_type=boundary_type
        ).observe(duration)
        
        logger.debug("Transaction operation recorded", 
                    execution_id=execution_id,
                    operation_type=operation_type,
                    success=success,
                    duration=duration)
    
    def record_pipeline_error(self, 
                             execution_id: str, 
                             error_type: str, 
                             stage: str):
        """Record pipeline error metrics."""
        self.pipeline_errors.labels(
            error_type=error_type,
            stage=stage,
            execution_id=execution_id
        ).inc()
        
        logger.warning("Pipeline error recorded", 
                      execution_id=execution_id,
                      error_type=error_type,
                      stage=stage)
    
    def record_pipeline_warning(self, 
                               execution_id: str, 
                               warning_type: str, 
                               stage: str):
        """Record pipeline warning metrics."""
        self.pipeline_warnings.labels(
            warning_type=warning_type,
            stage=stage,
            execution_id=execution_id
        ).inc()
        
        logger.info("Pipeline warning recorded", 
                   execution_id=execution_id,
                   warning_type=warning_type,
                   stage=stage)
    
    def record_batch_processing(self, 
                               execution_id: str, 
                               batch_size: int, 
                               processing_time: float,
                               success_count: int,
                               error_count: int):
        """Record batch processing metrics."""
        self.batch_processing_metrics.labels(
            metric_type='batch_size',
            execution_id=execution_id
        ).set(batch_size)
        
        self.batch_processing_metrics.labels(
            metric_type='processing_time',
            execution_id=execution_id
        ).set(processing_time)
        
        self.batch_processing_metrics.labels(
            metric_type='success_count',
            execution_id=execution_id
        ).set(success_count)
        
        self.batch_processing_metrics.labels(
            metric_type='error_count',
            execution_id=execution_id
        ).set(error_count)
        
        logger.info("Batch processing recorded", 
                   execution_id=execution_id,
                   batch_size=batch_size,
                   processing_time=processing_time,
                   success_count=success_count,
                   error_count=error_count)
    
    def get_pipeline_health_score(self, execution_id: str) -> float:
        """Calculate pipeline health score for specific execution."""
        # This would typically query the metrics to calculate health
        # For now, return a placeholder implementation
        return 85.0  # Placeholder health score
    
    def get_parser_performance_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get parser performance summary for specific execution."""
        # This would typically query the metrics to get performance data
        # For now, return a placeholder implementation
        return {
            'total_parsers': 12,
            'successful_parsers': 10,
            'failed_parsers': 2,
            'average_confidence': 0.85,
            'execution_time': 5.2
        }
    
    def get_llm_fallback_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get LLM fallback summary for specific execution."""
        # This would typically query the metrics to get LLM data
        # For now, return a placeholder implementation
        return {
            'total_llm_calls': 3,
            'successful_calls': 2,
            'failed_calls': 1,
            'average_confidence': 0.78,
            'total_duration': 2.1
        }
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        from prometheus_client import generate_latest
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            'normalizer_pipeline_metrics': {
                'total_executions': 'N/A',  # Would be calculated from actual metrics
                'average_duration': 'N/A',
                'success_rate': 'N/A'
            },
            'parser_metrics': {
                'total_parsers': 12,
                'average_confidence': 'N/A',
                'success_rate': 'N/A'
            },
            'llm_fallback_metrics': {
                'total_calls': 'N/A',
                'average_confidence': 'N/A',
                'success_rate': 'N/A'
            },
            'error_recovery_metrics': {
                'total_attempts': 'N/A',
                'success_rate': 'N/A'
            },
            'transaction_metrics': {
                'total_operations': 'N/A',
                'success_rate': 'N/A'
            }
        }

