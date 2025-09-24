"""
Pipeline metrics collection and Prometheus export.

This module extends the existing PriceJobMetrics with comprehensive pipeline-wide
metrics collection for A.1-A.5 and B.1-B.3 operations, including fetch latency,
artifact counts, review rates, and database performance metrics.
"""

import time
from typing import Dict, Any, Optional, List
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

from .price_job_metrics import PriceJobMetrics


class PipelineMetrics(PriceJobMetrics):
    """
    Extended metrics collection service for pipeline-wide operations.
    
    Extends existing PriceJobMetrics with:
    - Fetch latency metrics for A.1-A.5 operations
    - Artifact count metrics from scrape_artifacts table
    - Review rate metrics from scrape_runs table
    - Database performance metrics
    - Pipeline health indicators
    """
    
    def __init__(self, prometheus_port: int = 8000):
        """Initialize pipeline metrics service with Prometheus export."""
        # Use a custom registry to avoid duplication issues
        self.registry = CollectorRegistry()
        super().__init__(prometheus_port)
        
        # Pipeline-specific metrics
        self.fetch_latency = Histogram(
            'fetch_latency_seconds',
            'Fetch operation duration',
            ['source', 'platform', 'operation_type'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
            registry=self.registry
        )
        
        self.artifact_count = Counter(
            'artifacts_total',
            'Total artifacts processed',
            ['source', 'status', 'platform'],
            registry=self.registry
        )
        
        self.review_rate = Gauge(
            'review_rate_percent',
            'Review rate percentage',
            ['roaster_id', 'platform'],
            registry=self.registry
        )
        
        self.database_queries = Counter(
            'database_queries_total',
            'Database queries executed',
            ['query_type', 'success', 'table'],
            registry=self.registry
        )
        
        self.pipeline_health = Gauge(
            'pipeline_health_score',
            'Overall pipeline health score (0-100)',
            ['component'],
            registry=self.registry
        )
        
        self.fetch_errors = Counter(
            'fetch_errors_total',
            'Fetch operation errors',
            ['source', 'error_type', 'platform'],
            registry=self.registry
        )
        
        self.validation_errors = Counter(
            'validation_errors_total',
            'Validation errors encountered',
            ['error_type', 'platform', 'roaster_id'],
            registry=self.registry
        )
        
        self.storage_operations = Counter(
            'storage_operations_total',
            'Storage operations performed',
            ['operation_type', 'success', 'platform'],
            registry=self.registry
        )
        
        self.rpc_operations = Counter(
            'rpc_operations_total',
            'RPC operations performed',
            ['operation_type', 'success', 'table'],
            registry=self.registry
        )
        
        self.price_deltas = Counter(
            'price_deltas_total',
            'Price changes detected',
            ['roaster_id', 'currency', 'change_type'],
            registry=self.registry
        )
        
        self.system_resources = Gauge(
            'system_resources_usage',
            'System resource usage',
            ['resource_type', 'component'],
            registry=self.registry
        )
    
    def record_fetch_operation(
        self,
        duration: float,
        source: str,
        platform: str,
        operation_type: str = "fetch_products"
    ):
        """Record fetch operation metrics."""
        self.fetch_latency.labels(
            source=source,
            platform=platform,
            operation_type=operation_type
        ).observe(duration)
    
    def record_fetch_error(
        self,
        source: str,
        error_type: str,
        platform: str
    ):
        """Record fetch operation error."""
        self.fetch_errors.labels(
            source=source,
            error_type=error_type,
            platform=platform
        ).inc()
    
    def record_artifact_processing(
        self,
        source: str,
        status: str,
        platform: str,
        count: int = 1
    ):
        """Record artifact processing metrics."""
        self.artifact_count.labels(
            source=source,
            status=status,
            platform=platform
        ).inc(count)
    
    def record_validation_error(
        self,
        error_type: str,
        platform: str,
        roaster_id: str
    ):
        """Record validation error."""
        self.validation_errors.labels(
            error_type=error_type,
            platform=platform,
            roaster_id=roaster_id
        ).inc()
    
    def record_database_operation(
        self,
        query_type: str,
        success: bool,
        table: str,
        duration: float = None
    ):
        """Record database operation metrics."""
        self.database_queries.labels(
            query_type=query_type,
            success=str(success).lower(),
            table=table
        ).inc()
    
    def record_storage_operation(
        self,
        operation_type: str,
        success: bool,
        platform: str
    ):
        """Record storage operation metrics."""
        self.storage_operations.labels(
            operation_type=operation_type,
            success=str(success).lower(),
            platform=platform
        ).inc()
    
    def record_rpc_operation(
        self,
        operation_type: str,
        success: bool,
        table: str
    ):
        """Record RPC operation metrics."""
        self.rpc_operations.labels(
            operation_type=operation_type,
            success=str(success).lower(),
            table=table
        ).inc()
    
    def record_price_delta(
        self,
        roaster_id: str,
        currency: str,
        change_type: str,
        count: int = 1
    ):
        """Record price change metrics."""
        self.price_deltas.labels(
            roaster_id=roaster_id,
            currency=currency,
            change_type=change_type
        ).inc(count)
    
    def record_review_rate(
        self,
        roaster_id: str,
        platform: str,
        rate_percent: float
    ):
        """Record review rate metrics."""
        self.review_rate.labels(
            roaster_id=roaster_id,
            platform=platform
        ).set(rate_percent)
    
    def record_pipeline_health(
        self,
        component: str,
        health_score: float
    ):
        """Record pipeline health score (0-100)."""
        self.pipeline_health.labels(
            component=component
        ).set(health_score)
    
    def record_system_resources(
        self,
        resource_type: str,
        component: str,
        usage_value: float
    ):
        """Record system resource usage."""
        self.system_resources.labels(
            resource_type=resource_type,
            component=component
        ).set(usage_value)
    
    def get_pipeline_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics summary."""
        return {
            "prometheus_port": self.prometheus_port,
            "pipeline_metrics": {
                "fetch_latency_seconds": "Histogram of fetch operation durations",
                "artifacts_total": "Counter of total artifacts processed",
                "review_rate_percent": "Gauge of review rate percentages",
                "database_queries_total": "Counter of database queries executed",
                "pipeline_health_score": "Gauge of pipeline health scores",
                "fetch_errors_total": "Counter of fetch operation errors",
                "validation_errors_total": "Counter of validation errors",
                "storage_operations_total": "Counter of storage operations",
                "rpc_operations_total": "Counter of RPC operations",
                "price_deltas_total": "Counter of price changes detected",
                "system_resources_usage": "Gauge of system resource usage"
            },
            "inherited_metrics": self.get_metrics_summary()
        }


class MetricsCollector:
    """
    Centralized metrics collector for pipeline operations.
    
    Provides a unified interface for collecting metrics across all
    pipeline components (A.1-A.5 and B.1-B.3 operations).
    """
    
    def __init__(self, metrics: Optional[PipelineMetrics] = None):
        """Initialize metrics collector."""
        self.metrics = metrics or PipelineMetrics()
        self.operation_timers: Dict[str, float] = {}
    
    def start_operation_timer(self, operation_id: str) -> str:
        """Start timing an operation."""
        timer_id = f"{operation_id}_{int(time.time() * 1000)}"
        self.operation_timers[timer_id] = time.time()
        return timer_id
    
    def end_operation_timer(
        self,
        timer_id: str,
        source: str,
        platform: str,
        operation_type: str
    ) -> float:
        """End timing an operation and record metrics."""
        if timer_id not in self.operation_timers:
            return 0.0
        
        duration = time.time() - self.operation_timers[timer_id]
        del self.operation_timers[timer_id]
        
        self.metrics.record_fetch_operation(
            duration=duration,
            source=source,
            platform=platform,
            operation_type=operation_type
        )
        
        return duration
    
    def record_fetch_success(
        self,
        source: str,
        platform: str,
        artifact_count: int,
        duration: float
    ):
        """Record successful fetch operation."""
        self.metrics.record_fetch_operation(
            duration=duration,
            source=source,
            platform=platform,
            operation_type="fetch_products"
        )
        
        self.metrics.record_artifact_processing(
            source=source,
            status="success",
            platform=platform,
            count=artifact_count
        )
    
    def record_fetch_failure(
        self,
        source: str,
        platform: str,
        error_type: str,
        duration: float
    ):
        """Record failed fetch operation."""
        self.metrics.record_fetch_operation(
            duration=duration,
            source=source,
            platform=platform,
            operation_type="fetch_products"
        )
        
        self.metrics.record_fetch_error(
            source=source,
            error_type=error_type,
            platform=platform
        )
    
    def record_validation_result(
        self,
        source: str,
        platform: str,
        roaster_id: str,
        is_valid: bool,
        error_type: Optional[str] = None
    ):
        """Record validation result."""
        status = "valid" if is_valid else "invalid"
        
        self.metrics.record_artifact_processing(
            source=source,
            status=status,
            platform=platform,
            count=1
        )
        
        if not is_valid and error_type:
            self.metrics.record_validation_error(
                error_type=error_type,
                platform=platform,
                roaster_id=roaster_id
            )
    
    def record_database_operation(
        self,
        query_type: str,
        table: str,
        success: bool,
        duration: float = None
    ):
        """Record database operation."""
        self.metrics.record_database_operation(
            query_type=query_type,
            success=success,
            table=table
        )
    
    def record_storage_operation(
        self,
        operation_type: str,
        platform: str,
        success: bool
    ):
        """Record storage operation."""
        self.metrics.record_storage_operation(
            operation_type=operation_type,
            success=success,
            platform=platform
        )
    
    def record_rpc_operation(
        self,
        operation_type: str,
        table: str,
        success: bool
    ):
        """Record RPC operation."""
        self.metrics.record_rpc_operation(
            operation_type=operation_type,
            success=success,
            table=table
        )
    
    def record_price_changes(
        self,
        roaster_id: str,
        currency: str,
        changes: List[Dict[str, Any]]
    ):
        """Record price changes."""
        for change in changes:
            change_type = change.get('change_type', 'unknown')
            count = change.get('count', 1)
            
            self.metrics.record_price_delta(
                roaster_id=roaster_id,
                currency=currency,
                change_type=change_type,
                count=count
            )
    
    def record_review_metrics(
        self,
        roaster_id: str,
        platform: str,
        total_artifacts: int,
        reviewed_artifacts: int
    ):
        """Record review metrics."""
        if total_artifacts > 0:
            review_rate = (reviewed_artifacts / total_artifacts) * 100
            self.metrics.record_review_rate(
                roaster_id=roaster_id,
                platform=platform,
                rate_percent=review_rate
            )
    
    def record_system_metrics(
        self,
        component: str,
        health_score: float,
        resource_usage: Dict[str, float]
    ):
        """Record system metrics."""
        self.metrics.record_pipeline_health(
            component=component,
            health_score=health_score
        )
        
        for resource_type, usage in resource_usage.items():
            self.metrics.record_system_resources(
                resource_type=resource_type,
                component=component,
                usage_value=usage
            )
    
    def get_collector_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            "active_timers": len(self.operation_timers),
            "metrics_summary": self.metrics.get_pipeline_metrics_summary(),
            "timer_ids": list(self.operation_timers.keys())
        }
