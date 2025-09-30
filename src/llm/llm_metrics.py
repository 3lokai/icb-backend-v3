"""LLM service metrics for DeepSeek API integration with G.1 monitoring."""

import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge

from src.monitoring.pipeline_metrics import PipelineMetrics


class LLMServiceMetrics(PipelineMetrics):
    """
    Extended metrics collection for DeepSeek API LLM services.
    
    Extends PipelineMetrics with:
    - DeepSeek API call duration and success rates
    - Cache hit rates and performance
    - Rate limiting metrics
    - Cost tracking (token usage)
    - Service health monitoring
    """
    
    def __init__(self, prometheus_port: int = 8000):
        """Initialize LLM service metrics with Prometheus export."""
        super().__init__(prometheus_port)
        
        # DeepSeek API call metrics
        self.llm_call_duration = Histogram(
            'deepseek_call_duration_seconds',
            'DeepSeek API call duration',
            ['field', 'model', 'cache_status'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        self.llm_calls_total = Counter(
            'deepseek_calls_total',
            'Total DeepSeek API calls made',
            ['field', 'model', 'status'],
            registry=self.registry
        )
        
        self.llm_cache_hits = Counter(
            'deepseek_cache_hits_total',
            'DeepSeek API cache hits',
            ['field'],
            registry=self.registry
        )
        
        self.llm_cache_misses = Counter(
            'deepseek_cache_misses_total',
            'DeepSeek API cache misses',
            ['field'],
            registry=self.registry
        )
        
        self.llm_cache_hit_rate = Gauge(
            'deepseek_cache_hit_rate',
            'DeepSeek API cache hit rate (0-1)',
            ['field'],
            registry=self.registry
        )
        
        self.llm_rate_limit_hits = Counter(
            'deepseek_rate_limit_hits_total',
            'DeepSeek API rate limit hits',
            ['roaster_id'],
            registry=self.registry
        )
        
        self.llm_success_rate = Gauge(
            'deepseek_success_rate',
            'DeepSeek API call success rate (0-1)',
            ['field', 'model'],
            registry=self.registry
        )
        
        self.llm_cost_tokens = Counter(
            'deepseek_cost_tokens_total',
            'DeepSeek API token usage for cost tracking',
            ['token_type', 'model'],
            registry=self.registry
        )
        
        self.llm_confidence_scores = Histogram(
            'deepseek_confidence_scores',
            'DeepSeek API response confidence scores',
            ['field'],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        self.llm_service_health = Gauge(
            'deepseek_service_health',
            'DeepSeek service health status (1=healthy, 0=unhealthy)',
            [],
            registry=self.registry
        )
        
        self.llm_consecutive_failures = Gauge(
            'deepseek_consecutive_failures',
            'Consecutive DeepSeek API failures',
            [],
            registry=self.registry
        )
    
    def record_llm_call(
        self,
        duration: float,
        field: str,
        model: str,
        success: bool,
        cache_hit: bool,
        tokens_used: Optional[Dict[str, int]] = None,
        confidence: Optional[float] = None
    ):
        """Record DeepSeek API call metrics
        
        Args:
            duration: Call duration in seconds
            field: Field being enriched
            model: Model used (deepseek-chat or deepseek-reasoner)
            success: Whether the call succeeded
            cache_hit: Whether result came from cache
            tokens_used: Token usage dict with prompt_tokens, completion_tokens, total_tokens
            confidence: Confidence score of the result (0-1)
        """
        # Record call duration
        cache_status = 'hit' if cache_hit else 'miss'
        self.llm_call_duration.labels(
            field=field,
            model=model,
            cache_status=cache_status
        ).observe(duration)
        
        # Record call status
        status = 'success' if success else 'failure'
        self.llm_calls_total.labels(
            field=field,
            model=model,
            status=status
        ).inc()
        
        # Record cache hits/misses
        if cache_hit:
            self.llm_cache_hits.labels(field=field).inc()
        else:
            self.llm_cache_misses.labels(field=field).inc()
        
        # Update cache hit rate
        self._update_cache_hit_rate(field)
        
        # Record success rate
        if success:
            self.llm_success_rate.labels(field=field, model=model).set(1.0)
        else:
            self.llm_success_rate.labels(field=field, model=model).set(0.0)
        
        # Record token usage for cost tracking
        if tokens_used and not cache_hit:
            self.llm_cost_tokens.labels(
                token_type='prompt',
                model=model
            ).inc(tokens_used.get('prompt_tokens', 0))
            
            self.llm_cost_tokens.labels(
                token_type='completion',
                model=model
            ).inc(tokens_used.get('completion_tokens', 0))
        
        # Record confidence score
        if confidence is not None:
            self.llm_confidence_scores.labels(field=field).observe(confidence)
    
    def _update_cache_hit_rate(self, field: str):
        """Update cache hit rate gauge for a field"""
        # Get current counts
        hits = self.llm_cache_hits.labels(field=field)._value.get()
        misses = self.llm_cache_misses.labels(field=field)._value.get()
        
        total = hits + misses
        if total > 0:
            hit_rate = hits / total
            self.llm_cache_hit_rate.labels(field=field).set(hit_rate)
    
    def record_rate_limit_hit(self, roaster_id: str):
        """Record a rate limit hit for a roaster
        
        Args:
            roaster_id: The roaster that hit the rate limit
        """
        self.llm_rate_limit_hits.labels(roaster_id=roaster_id).inc()
    
    def record_service_health(self, is_healthy: bool, consecutive_failures: int = 0):
        """Record DeepSeek service health status
        
        Args:
            is_healthy: Whether the service is healthy
            consecutive_failures: Number of consecutive failures
        """
        self.llm_service_health.set(1.0 if is_healthy else 0.0)
        self.llm_consecutive_failures.set(consecutive_failures)
    
    def get_llm_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive LLM metrics summary"""
        return {
            "deepseek_metrics": {
                "call_duration_seconds": "Histogram of DeepSeek API call durations",
                "calls_total": "Counter of total DeepSeek API calls",
                "cache_hits_total": "Counter of cache hits",
                "cache_misses_total": "Counter of cache misses",
                "cache_hit_rate": "Gauge of cache hit rate per field",
                "rate_limit_hits_total": "Counter of rate limit hits per roaster",
                "success_rate": "Gauge of call success rate",
                "cost_tokens_total": "Counter of token usage for cost tracking",
                "confidence_scores": "Histogram of confidence scores",
                "service_health": "Gauge of service health status",
                "consecutive_failures": "Gauge of consecutive failures"
            },
            "inherited_metrics": self.get_pipeline_metrics_summary()
        }
