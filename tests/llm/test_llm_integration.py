"""Integration tests for complete LLM service with all components."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from src.llm import (
    DeepSeekWrapperService,
    LLMServiceMetrics,
    CacheService,
    RateLimiter,
    LLMServiceError,
    RateLimitExceededError
)
from src.config.deepseek_config import DeepSeekConfig
from src.config.cache_config import CacheConfig


@pytest.fixture
def config():
    """Create test configuration"""
    return DeepSeekConfig(
        api_key="test_api_key",
        model="deepseek-chat",
        retry_attempts=2,
        retry_delay=0.1
    )


@pytest.fixture
def cache_config():
    """Create cache configuration"""
    return CacheConfig(backend="memory", default_ttl=3600)


@pytest_asyncio.fixture
async def llm_service(config, cache_config):
    """Create fully integrated LLM service"""
    cache = CacheService(cache_config)
    rate_limiter = RateLimiter({
        'requests_per_minute': 10,
        'requests_per_hour': 100,
        'requests_per_day': 1000
    })
    metrics = LLMServiceMetrics(prometheus_port=8001)
    
    return DeepSeekWrapperService(config, cache, rate_limiter, metrics)


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI response"""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "Gesha"
    response.usage.prompt_tokens = 100
    response.usage.completion_tokens = 50
    response.usage.total_tokens = 150
    return response


class TestLLMIntegration:
    """Integration tests for complete LLM service stack"""
    
    @pytest.mark.asyncio
    async def test_full_enrichment_flow(self, llm_service, mock_openai_response):
        """Test complete flow: API call -> cache -> metrics"""
        artifact = {
            'raw_payload_hash': 'test_hash_123',
            'roaster_id': 'roaster_1',
            'name': 'Ethiopian Coffee'
        }
        
        with patch.object(llm_service.provider.chat.completions, 'create', return_value=mock_openai_response):
            # First call - should hit API
            result1 = await llm_service.enrich_field(artifact, 'variety', 'Extract variety')
            
            assert result1.field == 'variety'
            assert result1.value == 'Gesha'
            assert result1.confidence == 0.8
            
            # Second call - should hit cache
            result2 = await llm_service.enrich_field(artifact, 'variety', 'Extract variety')
            
            assert result2.field == 'variety'
            assert result2.value == 'Gesha'
            assert result2.confidence == 0.8
        
        # Verify metrics recorded correctly
        assert llm_service.metrics.llm_calls_total.labels(field='variety', model='deepseek-chat', status='success')._value.get() == 2
        assert llm_service.metrics.llm_cache_hits.labels(field='variety')._value.get() == 1
        assert llm_service.metrics.llm_cache_misses.labels(field='variety')._value.get() == 1
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, llm_service, mock_openai_response):
        """Test rate limiting works across the service"""
        # Create service with very low limits
        low_limit_config = DeepSeekConfig(api_key="test", retry_attempts=1)
        cache_config = CacheConfig(backend="memory")
        cache = CacheService(cache_config)
        rate_limiter = RateLimiter({'requests_per_minute': 2})
        metrics = LLMServiceMetrics(prometheus_port=8002)
        
        limited_service = DeepSeekWrapperService(low_limit_config, cache, rate_limiter, metrics)
        
        with patch.object(limited_service.provider.chat.completions, 'create', return_value=mock_openai_response):
            # First 2 requests should succeed
            await limited_service.enrich_field({'raw_payload_hash': 'hash_1', 'roaster_id': 'roaster_1'}, 'variety', 'test')
            await limited_service.enrich_field({'raw_payload_hash': 'hash_2', 'roaster_id': 'roaster_1'}, 'process', 'test')
            
            # Third should fail with rate limit
            with pytest.raises(RateLimitExceededError):
                await limited_service.enrich_field({'raw_payload_hash': 'hash_3', 'roaster_id': 'roaster_1'}, 'roast', 'test')
        
        # Verify rate limit metric
        assert metrics.llm_rate_limit_hits.labels(roaster_id='roaster_1')._value.get() == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_with_retry(self, llm_service):
        """Test error handling and retry logic work together"""
        artifact = {'raw_payload_hash': 'error_test', 'roaster_id': 'roaster_1'}
        
        # Mock to fail once then succeed
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from openai import APITimeoutError
                raise APITimeoutError("Timeout")
            
            response = Mock()
            response.choices = [Mock()]
            response.choices[0].message.content = "Washed"
            response.usage.prompt_tokens = 50
            response.usage.completion_tokens = 25
            response.usage.total_tokens = 75
            return response
        
        with patch.object(llm_service.provider.chat.completions, 'create', side_effect=side_effect):
            result = await llm_service.enrich_field(artifact, 'process', 'Extract process')
            
            assert result.value == "Washed"
            assert call_count == 2  # Failed once, succeeded on retry
        
        # Verify health status updated
        assert llm_service._health_status['available'] is True
        assert llm_service._health_status['consecutive_failures'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_persistence_across_calls(self, llm_service, mock_openai_response):
        """Test cache persists across multiple calls"""
        with patch.object(llm_service.provider.chat.completions, 'create', return_value=mock_openai_response):
            artifact1 = {'raw_payload_hash': 'persist_test', 'roaster_id': 'roaster_1'}
            
            # First enrichment
            await llm_service.enrich_field(artifact1, 'variety', 'Extract variety')
            
            # Different field, same artifact - should use API
            await llm_service.enrich_field(artifact1, 'process', 'Extract process')
            
            # Same field, same artifact - should use cache
            await llm_service.enrich_field(artifact1, 'variety', 'Extract variety')
        
        # Verify cache behavior
        assert llm_service.metrics.llm_cache_hits.labels(field='variety')._value.get() == 1
        assert llm_service.metrics.llm_cache_misses.labels(field='variety')._value.get() == 1
        assert llm_service.metrics.llm_cache_misses.labels(field='process')._value.get() == 1
    
    @pytest.mark.asyncio
    async def test_batch_enrichment_integration(self, llm_service, mock_openai_response):
        """Test batch enrichment with all components"""
        artifacts = [
            {'raw_payload_hash': f'batch_{i}', 'roaster_id': 'roaster_1', 'name': f'Coffee {i}'}
            for i in range(3)
        ]
        
        with patch.object(llm_service.provider.chat.completions, 'create', return_value=mock_openai_response):
            results = await llm_service.batch_enrich(artifacts, ['variety'])
            
            assert len(results) == 3
            assert all(r.field == 'variety' for r in results)
            assert all(r.value == 'Gesha' for r in results)
        
        # Verify all were recorded
        assert llm_service.metrics.llm_calls_total.labels(field='variety', model='deepseek-chat', status='success')._value.get() == 3
    
    @pytest.mark.asyncio
    async def test_health_status_tracking(self, llm_service):
        """Test service health tracking across operations"""
        artifact = {'raw_payload_hash': 'health_test', 'roaster_id': 'roaster_1'}
        
        # Simulate failures
        with patch.object(llm_service.provider.chat.completions, 'create', side_effect=Exception("Service down")):
            with pytest.raises(LLMServiceError):
                await llm_service.enrich_field(artifact, 'variety', 'test')
        
        # Check health degraded
        assert llm_service._health_status['consecutive_failures'] > 0
        
        # Simulate recovery
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = "Recovered"
        response.usage.prompt_tokens = 50
        response.usage.completion_tokens = 25
        response.usage.total_tokens = 75
        
        with patch.object(llm_service.provider.chat.completions, 'create', return_value=response):
            result = await llm_service.enrich_field({'raw_payload_hash': 'health_test_2', 'roaster_id': 'roaster_1'}, 'variety', 'test')
            
            assert result.value == "Recovered"
        
        # Check health recovered
        assert llm_service._health_status['available'] is True
        assert llm_service._health_status['consecutive_failures'] == 0
    
    @pytest.mark.asyncio
    async def test_cost_tracking_integration(self, llm_service, mock_openai_response):
        """Test cost tracking through token usage"""
        artifact = {'raw_payload_hash': 'cost_test', 'roaster_id': 'roaster_1'}
        
        with patch.object(llm_service.provider.chat.completions, 'create', return_value=mock_openai_response):
            # Make a call that uses tokens
            await llm_service.enrich_field(artifact, 'variety', 'Extract variety')
            
            # Make cached call (should not count tokens)
            await llm_service.enrich_field(artifact, 'variety', 'Extract variety')
        
        # Only first call should have counted tokens
        assert llm_service.metrics.llm_cost_tokens.labels(token_type='prompt', model='deepseek-chat')._value.get() == 100
        assert llm_service.metrics.llm_cost_tokens.labels(token_type='completion', model='deepseek-chat')._value.get() == 50
