"""Unit tests for LLM service metrics."""

import pytest
import time

from src.llm.llm_metrics import LLMServiceMetrics


class TestLLMServiceMetrics:
    """Tests for LLM service metrics"""
    
    def test_initialization(self):
        """Test metrics service initializes correctly"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        assert metrics.prometheus_port == 8000
        assert metrics.llm_call_duration is not None
        assert metrics.llm_cache_hit_rate is not None
        assert metrics.llm_rate_limit_hits is not None
    
    def test_record_llm_call_cache_miss(self):
        """Test recording LLM call with cache miss"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        metrics.record_llm_call(
            duration=2.5,
            field='variety',
            model='deepseek-chat',
            success=True,
            cache_hit=False,
            tokens_used={'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            confidence=0.85
        )
        
        # Verify call was recorded
        assert metrics.llm_calls_total.labels(field='variety', model='deepseek-chat', status='success')._value.get() == 1
        assert metrics.llm_cache_misses.labels(field='variety')._value.get() == 1
        assert metrics.llm_cache_hits.labels(field='variety')._value.get() == 0
    
    def test_record_llm_call_cache_hit(self):
        """Test recording LLM call with cache hit"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        metrics.record_llm_call(
            duration=0.1,
            field='process',
            model='deepseek-chat',
            success=True,
            cache_hit=True
        )
        
        # Verify cache hit was recorded
        assert metrics.llm_cache_hits.labels(field='process')._value.get() == 1
        assert metrics.llm_cache_misses.labels(field='process')._value.get() == 0
    
    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate is calculated correctly"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        # Record 7 cache hits and 3 misses (70% hit rate)
        for _ in range(7):
            metrics.record_llm_call(
                duration=0.1,
                field='variety',
                model='deepseek-chat',
                success=True,
                cache_hit=True
            )
        
        for _ in range(3):
            metrics.record_llm_call(
                duration=2.0,
                field='variety',
                model='deepseek-chat',
                success=True,
                cache_hit=False,
                tokens_used={'total_tokens': 100}
            )
        
        # Check hit rate
        hit_rate = metrics.llm_cache_hit_rate.labels(field='variety')._value.get()
        assert hit_rate == 0.7  # 7 hits out of 10 total
    
    def test_record_failed_call(self):
        """Test recording failed LLM call"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        metrics.record_llm_call(
            duration=5.0,
            field='description',
            model='deepseek-chat',
            success=False,
            cache_hit=False
        )
        
        # Verify failure was recorded
        assert metrics.llm_calls_total.labels(field='description', model='deepseek-chat', status='failure')._value.get() == 1
        assert metrics.llm_success_rate.labels(field='description', model='deepseek-chat')._value.get() == 0.0
    
    def test_record_rate_limit_hit(self):
        """Test recording rate limit hits"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        metrics.record_rate_limit_hit('roaster_123')
        metrics.record_rate_limit_hit('roaster_123')
        metrics.record_rate_limit_hit('roaster_456')
        
        assert metrics.llm_rate_limit_hits.labels(roaster_id='roaster_123')._value.get() == 2
        assert metrics.llm_rate_limit_hits.labels(roaster_id='roaster_456')._value.get() == 1
    
    def test_record_service_health(self):
        """Test recording service health status"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        # Healthy service
        metrics.record_service_health(is_healthy=True, consecutive_failures=0)
        assert metrics.llm_service_health._value.get() == 1.0
        assert metrics.llm_consecutive_failures._value.get() == 0
        
        # Unhealthy service
        metrics.record_service_health(is_healthy=False, consecutive_failures=5)
        assert metrics.llm_service_health._value.get() == 0.0
        assert metrics.llm_consecutive_failures._value.get() == 5
    
    def test_token_cost_tracking(self):
        """Test token usage tracking for cost calculation"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        # Record multiple calls with different token counts
        metrics.record_llm_call(
            duration=2.0,
            field='variety',
            model='deepseek-chat',
            success=True,
            cache_hit=False,
            tokens_used={'prompt_tokens': 500, 'completion_tokens': 200, 'total_tokens': 700}
        )
        
        metrics.record_llm_call(
            duration=3.0,
            field='process',
            model='deepseek-chat',
            success=True,
            cache_hit=False,
            tokens_used={'prompt_tokens': 300, 'completion_tokens': 100, 'total_tokens': 400}
        )
        
        # Verify token counts
        assert metrics.llm_cost_tokens.labels(token_type='prompt', model='deepseek-chat')._value.get() == 800
        assert metrics.llm_cost_tokens.labels(token_type='completion', model='deepseek-chat')._value.get() == 300
    
    def test_confidence_score_tracking(self):
        """Test confidence score histogram"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        # Record calls with different confidence scores
        for conf in [0.6, 0.7, 0.8, 0.9, 0.95]:
            metrics.record_llm_call(
                duration=1.0,
                field='variety',
                model='deepseek-chat',
                success=True,
                cache_hit=False,
                confidence=conf
            )
        
        # Histogram should have recorded all values
        histogram = metrics.llm_confidence_scores.labels(field='variety')
        # Can't easily check histogram buckets, but verify it doesn't error
        assert histogram is not None
    
    def test_get_llm_metrics_summary(self):
        """Test getting LLM metrics summary"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        summary = metrics.get_llm_metrics_summary()
        
        assert 'deepseek_metrics' in summary
        assert 'inherited_metrics' in summary
        assert 'call_duration_seconds' in summary['deepseek_metrics']
        assert 'cache_hit_rate' in summary['deepseek_metrics']
        assert 'cost_tokens_total' in summary['deepseek_metrics']
    
    def test_multiple_models(self):
        """Test metrics work with different models"""
        metrics = LLMServiceMetrics(prometheus_port=8000)
        
        # Record calls with different models
        metrics.record_llm_call(
            duration=2.0,
            field='variety',
            model='deepseek-chat',
            success=True,
            cache_hit=False,
            tokens_used={'total_tokens': 100}
        )
        
        metrics.record_llm_call(
            duration=5.0,
            field='variety',
            model='deepseek-reasoner',
            success=True,
            cache_hit=False,
            tokens_used={'total_tokens': 200}
        )
        
        # Verify separate counters
        assert metrics.llm_calls_total.labels(field='variety', model='deepseek-chat', status='success')._value.get() == 1
        assert metrics.llm_calls_total.labels(field='variety', model='deepseek-reasoner', status='success')._value.get() == 1
