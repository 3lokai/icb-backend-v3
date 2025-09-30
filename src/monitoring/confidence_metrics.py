"""Confidence evaluation metrics collection and Prometheus export for D.2."""

import time
from typing import Dict, Any, Optional, List
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

from .pipeline_metrics import PipelineMetrics


class ConfidenceMetrics(PipelineMetrics):
    """
    Extended metrics collection service for confidence evaluation operations.
    
    Extends PipelineMetrics with D.2-specific metrics:
    - Confidence evaluation metrics
    - Review workflow metrics
    - Enrichment persistence metrics
    - LLM result quality metrics
    """
    
    def __init__(self, prometheus_port: int = 8000):
        """Initialize confidence metrics service with Prometheus export."""
        super().__init__(prometheus_port)
        
        # Confidence evaluation metrics
        self.confidence_evaluations = Counter(
            'confidence_evaluations_total',
            'Total confidence evaluations performed',
            ['field', 'action', 'status'],
            registry=self.registry
        )
        
        self.confidence_scores = Histogram(
            'confidence_scores',
            'Distribution of confidence scores',
            ['field', 'provider', 'model'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        self.confidence_thresholds = Gauge(
            'confidence_thresholds',
            'Current confidence thresholds by field',
            ['field'],
            registry=self.registry
        )
        
        self.evaluation_rules_applied = Counter(
            'evaluation_rules_applied_total',
            'Total evaluation rules applied',
            ['rule_name', 'field'],
            registry=self.registry
        )
        
        # Review workflow metrics
        self.review_items = Counter(
            'review_items_total',
            'Total review items created',
            ['artifact_id', 'field', 'reason'],
            registry=self.registry
        )
        
        self.review_decisions = Counter(
            'review_decisions_total',
            'Total review decisions made',
            ['decision', 'reviewer_id', 'field'],
            registry=self.registry
        )
        
        self.review_duration = Histogram(
            'review_duration_seconds',
            'Time taken for review decisions',
            ['reviewer_id', 'decision'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600],
            registry=self.registry
        )
        
        self.review_backlog = Gauge(
            'review_backlog_count',
            'Number of items pending review',
            ['field', 'priority'],
            registry=self.registry
        )
        
        # Enrichment persistence metrics
        self.enrichments_persisted = Counter(
            'enrichments_persisted_total',
            'Total enrichments persisted',
            ['field', 'status', 'action'],
            registry=self.registry
        )
        
        self.enrichment_persistence_duration = Histogram(
            'enrichment_persistence_duration_seconds',
            'Time taken to persist enrichments',
            ['field', 'batch_size'],
            buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )
        
        self.enrichment_retrievals = Counter(
            'enrichment_retrievals_total',
            'Total enrichment retrievals',
            ['retrieval_type', 'field'],
            registry=self.registry
        )
        
        # LLM result quality metrics
        self.llm_result_quality = Histogram(
            'llm_result_quality_score',
            'Distribution of LLM result quality scores',
            ['field', 'provider', 'model'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        self.llm_usage_tokens = Counter(
            'llm_usage_tokens_total',
            'Total LLM tokens used',
            ['provider', 'model', 'field'],
            registry=self.registry
        )
        
        self.llm_api_calls = Counter(
            'llm_api_calls_total',
            'Total LLM API calls made',
            ['provider', 'model', 'success', 'field'],
            registry=self.registry
        )
        
        self.llm_api_latency = Histogram(
            'llm_api_latency_seconds',
            'LLM API call latency',
            ['provider', 'model', 'field'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # Error and failure metrics
        self.confidence_evaluation_errors = Counter(
            'confidence_evaluation_errors_total',
            'Confidence evaluation errors',
            ['error_type', 'field'],
            registry=self.registry
        )
        
        self.review_workflow_errors = Counter(
            'review_workflow_errors_total',
            'Review workflow errors',
            ['error_type', 'artifact_id'],
            registry=self.registry
        )
        
        self.enrichment_persistence_errors = Counter(
            'enrichment_persistence_errors_total',
            'Enrichment persistence errors',
            ['error_type', 'field'],
            registry=self.registry
        )
        
        # Performance metrics
        self.confidence_evaluation_duration = Histogram(
            'confidence_evaluation_duration_seconds',
            'Time taken for confidence evaluation',
            ['field', 'batch_size'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0],
            registry=self.registry
        )
        
        self.batch_processing_duration = Histogram(
            'batch_processing_duration_seconds',
            'Time taken for batch processing',
            ['operation_type', 'batch_size'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
    
    def record_confidence_evaluation(
        self,
        field: str,
        confidence_score: float,
        action: str,
        status: str,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
        duration: float = None
    ):
        """Record confidence evaluation metrics."""
        self.confidence_evaluations.labels(
            field=field,
            action=action,
            status=status
        ).inc()
        
        self.confidence_scores.labels(
            field=field,
            provider=provider,
            model=model
        ).observe(confidence_score)
        
        if duration is not None:
            self.confidence_evaluation_duration.labels(
                field=field,
                batch_size="single"
            ).observe(duration)
    
    def record_confidence_threshold(self, field: str, threshold: float):
        """Record confidence threshold for field."""
        self.confidence_thresholds.labels(field=field).set(threshold)
    
    def record_evaluation_rule_applied(self, rule_name: str, field: str):
        """Record evaluation rule application."""
        self.evaluation_rules_applied.labels(
            rule_name=rule_name,
            field=field
        ).inc()
    
    def record_review_item_created(
        self,
        artifact_id: str,
        field: str,
        reason: str
    ):
        """Record review item creation."""
        self.review_items.labels(
            artifact_id=artifact_id,
            field=field,
            reason=reason
        ).inc()
    
    def record_review_decision(
        self,
        decision: str,
        reviewer_id: str,
        field: str,
        duration: float = None
    ):
        """Record review decision."""
        self.review_decisions.labels(
            decision=decision,
            reviewer_id=reviewer_id,
            field=field
        ).inc()
        
        if duration is not None:
            self.review_duration.labels(
                reviewer_id=reviewer_id,
                decision=decision
            ).observe(duration)
    
    def record_review_backlog(self, field: str, priority: str, count: int):
        """Record review backlog count."""
        self.review_backlog.labels(
            field=field,
            priority=priority
        ).set(count)
    
    def record_enrichment_persisted(
        self,
        field: str,
        status: str,
        action: str,
        duration: float = None
    ):
        """Record enrichment persistence."""
        self.enrichments_persisted.labels(
            field=field,
            status=status,
            action=action
        ).inc()
        
        if duration is not None:
            self.enrichment_persistence_duration.labels(
                field=field,
                batch_size="single"
            ).observe(duration)
    
    def record_enrichment_retrieval(self, retrieval_type: str, field: str):
        """Record enrichment retrieval."""
        self.enrichment_retrievals.labels(
            retrieval_type=retrieval_type,
            field=field
        ).inc()
    
    def record_llm_result_quality(
        self,
        field: str,
        quality_score: float,
        provider: str = "deepseek",
        model: str = "deepseek-chat"
    ):
        """Record LLM result quality score."""
        self.llm_result_quality.labels(
            field=field,
            provider=provider,
            model=model
        ).observe(quality_score)
    
    def record_llm_usage(
        self,
        provider: str,
        model: str,
        field: str,
        tokens: int
    ):
        """Record LLM token usage."""
        self.llm_usage_tokens.labels(
            provider=provider,
            model=model,
            field=field
        ).inc(tokens)
    
    def record_llm_api_call(
        self,
        provider: str,
        model: str,
        field: str,
        success: bool,
        duration: float = None
    ):
        """Record LLM API call."""
        self.llm_api_calls.labels(
            provider=provider,
            model=model,
            success=str(success).lower(),
            field=field
        ).inc()
        
        if duration is not None:
            self.llm_api_latency.labels(
                provider=provider,
                model=model,
                field=field
            ).observe(duration)
    
    def record_confidence_evaluation_error(self, error_type: str, field: str):
        """Record confidence evaluation error."""
        self.confidence_evaluation_errors.labels(
            error_type=error_type,
            field=field
        ).inc()
    
    def record_review_workflow_error(self, error_type: str, artifact_id: str):
        """Record review workflow error."""
        self.review_workflow_errors.labels(
            error_type=error_type,
            artifact_id=artifact_id
        ).inc()
    
    def record_enrichment_persistence_error(self, error_type: str, field: str):
        """Record enrichment persistence error."""
        self.enrichment_persistence_errors.labels(
            error_type=error_type,
            field=field
        ).inc()
    
    def record_batch_processing(
        self,
        operation_type: str,
        batch_size: int,
        duration: float
    ):
        """Record batch processing metrics."""
        self.batch_processing_duration.labels(
            operation_type=operation_type,
            batch_size=str(batch_size)
        ).observe(duration)
    
    def get_confidence_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive confidence metrics summary."""
        return {
            "prometheus_port": self.prometheus_port,
            "confidence_metrics": {
                "confidence_evaluations_total": "Counter of total confidence evaluations",
                "confidence_scores": "Histogram of confidence score distribution",
                "confidence_thresholds": "Gauge of current confidence thresholds",
                "evaluation_rules_applied_total": "Counter of evaluation rules applied",
                "review_items_total": "Counter of review items created",
                "review_decisions_total": "Counter of review decisions made",
                "review_duration_seconds": "Histogram of review decision duration",
                "review_backlog_count": "Gauge of review backlog count",
                "enrichments_persisted_total": "Counter of enrichments persisted",
                "enrichment_persistence_duration_seconds": "Histogram of persistence duration",
                "enrichment_retrievals_total": "Counter of enrichment retrievals",
                "llm_result_quality_score": "Histogram of LLM result quality",
                "llm_usage_tokens_total": "Counter of LLM token usage",
                "llm_api_calls_total": "Counter of LLM API calls",
                "llm_api_latency_seconds": "Histogram of LLM API latency",
                "confidence_evaluation_errors_total": "Counter of confidence evaluation errors",
                "review_workflow_errors_total": "Counter of review workflow errors",
                "enrichment_persistence_errors_total": "Counter of enrichment persistence errors",
                "confidence_evaluation_duration_seconds": "Histogram of evaluation duration",
                "batch_processing_duration_seconds": "Histogram of batch processing duration"
            },
            "inherited_metrics": self.get_pipeline_metrics_summary()
        }


class ConfidenceMetricsCollector:
    """
    Centralized metrics collector for confidence evaluation operations.
    
    Provides a unified interface for collecting metrics across all
    D.2 confidence evaluation components.
    """
    
    def __init__(self, metrics: Optional[ConfidenceMetrics] = None):
        """Initialize confidence metrics collector."""
        self.metrics = metrics or ConfidenceMetrics()
        self.operation_timers: Dict[str, float] = {}
    
    def start_confidence_evaluation_timer(self, field: str) -> str:
        """Start timing a confidence evaluation operation."""
        timer_id = f"confidence_eval_{field}_{int(time.time() * 1000)}"
        self.operation_timers[timer_id] = time.time()
        return timer_id
    
    def end_confidence_evaluation_timer(
        self,
        timer_id: str,
        field: str,
        confidence_score: float,
        action: str,
        status: str,
        provider: str = "deepseek",
        model: str = "deepseek-chat"
    ) -> float:
        """End timing a confidence evaluation and record metrics."""
        if timer_id not in self.operation_timers:
            return 0.0
        
        duration = time.time() - self.operation_timers[timer_id]
        del self.operation_timers[timer_id]
        
        self.metrics.record_confidence_evaluation(
            field=field,
            confidence_score=confidence_score,
            action=action,
            status=status,
            provider=provider,
            model=model,
            duration=duration
        )
        
        return duration
    
    def start_review_timer(self, artifact_id: str, field: str) -> str:
        """Start timing a review operation."""
        timer_id = f"review_{artifact_id}_{field}_{int(time.time() * 1000)}"
        self.operation_timers[timer_id] = time.time()
        return timer_id
    
    def end_review_timer(
        self,
        timer_id: str,
        decision: str,
        reviewer_id: str,
        field: str
    ) -> float:
        """End timing a review operation and record metrics."""
        if timer_id not in self.operation_timers:
            return 0.0
        
        duration = time.time() - self.operation_timers[timer_id]
        del self.operation_timers[timer_id]
        
        self.metrics.record_review_decision(
            decision=decision,
            reviewer_id=reviewer_id,
            field=field,
            duration=duration
        )
        
        return duration
    
    def start_enrichment_persistence_timer(self, field: str) -> str:
        """Start timing an enrichment persistence operation."""
        timer_id = f"enrichment_persist_{field}_{int(time.time() * 1000)}"
        self.operation_timers[timer_id] = time.time()
        return timer_id
    
    def end_enrichment_persistence_timer(
        self,
        timer_id: str,
        field: str,
        status: str,
        action: str
    ) -> float:
        """End timing an enrichment persistence operation and record metrics."""
        if timer_id not in self.operation_timers:
            return 0.0
        
        duration = time.time() - self.operation_timers[timer_id]
        del self.operation_timers[timer_id]
        
        self.metrics.record_enrichment_persisted(
            field=field,
            status=status,
            action=action,
            duration=duration
        )
        
        return duration
    
    def record_llm_operation(
        self,
        provider: str,
        model: str,
        field: str,
        tokens: int,
        success: bool,
        duration: float = None
    ):
        """Record LLM operation metrics."""
        self.metrics.record_llm_usage(
            provider=provider,
            model=model,
            field=field,
            tokens=tokens
        )
        
        self.metrics.record_llm_api_call(
            provider=provider,
            model=model,
            field=field,
            success=success,
            duration=duration
        )
    
    def record_batch_operation(
        self,
        operation_type: str,
        batch_size: int,
        duration: float
    ):
        """Record batch operation metrics."""
        self.metrics.record_batch_processing(
            operation_type=operation_type,
            batch_size=batch_size,
            duration=duration
        )
    
    def record_error(
        self,
        error_type: str,
        component: str,
        field: str = None,
        artifact_id: str = None
    ):
        """Record error metrics."""
        if component == "confidence_evaluation":
            self.metrics.record_confidence_evaluation_error(error_type, field)
        elif component == "review_workflow":
            self.metrics.record_review_workflow_error(error_type, artifact_id)
        elif component == "enrichment_persistence":
            self.metrics.record_enrichment_persistence_error(error_type, field)
    
    def get_collector_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            "active_timers": len(self.operation_timers),
            "metrics_summary": self.metrics.get_confidence_metrics_summary(),
            "timer_ids": list(self.operation_timers.keys())
        }
