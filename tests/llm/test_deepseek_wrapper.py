"""Unit tests for DeepSeek wrapper service."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.llm.deepseek_wrapper import DeepSeekWrapperService, LLMServiceError, RateLimitExceededError
from src.llm.llm_interface import LLMResult
from src.config.deepseek_config import DeepSeekConfig
from src.llm.cache_service import CacheService
from src.llm.rate_limiter import RateLimiter
from src.config.cache_config import CacheConfig


@pytest.fixture
def deepseek_config():
    """Create test DeepSeek configuration"""
    return DeepSeekConfig(
        api_key="test_api_key",
        model="deepseek-chat",
        temperature=0.7,
        max_tokens=1000,
        timeout=30,
        retry_attempts=3,
        retry_delay=0.1  # Faster for tests
    )


@pytest.fixture
def cache_config():
    """Create test cache configuration"""
    return CacheConfig(backend="memory", default_ttl=3600)


@pytest_asyncio.fixture
async def cache_service(cache_config):
    """Create cache service for testing"""
    return CacheService(cache_config)


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing"""
    return RateLimiter({
        'requests_per_minute': 60,
        'requests_per_hour': 1000,
        'requests_per_day': 10000
    })


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI API response"""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Extracted value from LLM"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150
    return mock_response


class TestDeepSeekWrapperService:
    """Tests for DeepSeek wrapper service"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, deepseek_config, cache_service, rate_limiter):
        """Test service initializes correctly"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        assert service.config == deepseek_config
        assert service.cache_service == cache_service
        assert service.rate_limiter == rate_limiter
        assert service.provider is not None
        assert service._health_status['available'] is True
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, deepseek_config, cache_service, rate_limiter):
        """Test cache key is generated correctly from raw_payload_hash and field"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        artifact = {'raw_payload_hash': 'abc123', 'name': 'Test Coffee'}
        cache_key = service._generate_cache_key(artifact, 'variety')
        
        assert cache_key == 'llm:abc123:variety'
    
    @pytest.mark.asyncio
    async def test_cache_key_generation_without_hash(self, deepseek_config, cache_service, rate_limiter):
        """Test cache key fallback when raw_payload_hash is missing"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        artifact = {'name': 'Test Coffee', 'roaster': 'Test Roaster'}
        cache_key = service._generate_cache_key(artifact, 'variety')
        
        assert cache_key.startswith('llm:')
        assert cache_key.endswith(':variety')
        assert len(cache_key) > 15  # Should have a hash in the middle
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, deepseek_config, cache_service, rate_limiter):
        """Test that cached results are returned without calling LLM"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        # Pre-populate cache
        artifact = {'raw_payload_hash': 'test123', 'name': 'Coffee'}
        cache_key = service._generate_cache_key(artifact, 'variety')
        cached_result = LLMResult(
            field='variety',
            value='Gesha',
            confidence=0.9,
            model='deepseek-chat',
            usage={'total_tokens': 100},
            created_at=datetime.now()
        )
        await cache_service.set(cache_key, cached_result)
        
        # Make request - should hit cache
        result = await service.enrich_field(artifact, 'variety', 'Extract variety')
        
        assert result.field == 'variety'
        assert result.value == 'Gesha'
        assert result.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, deepseek_config, cache_service, rate_limiter):
        """Test that rate limit is enforced"""
        # Create rate limiter with very low limit
        low_limit_limiter = RateLimiter({'requests_per_minute': 0})
        service = DeepSeekWrapperService(deepseek_config, cache_service, low_limit_limiter)
        
        artifact = {'raw_payload_hash': 'test123', 'roaster_id': 'roaster1'}
        
        with pytest.raises(RateLimitExceededError) as exc_info:
            await service.enrich_field(artifact, 'variety', 'Extract variety')
        
        assert 'Rate limit exceeded' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_successful_llm_call(self, deepseek_config, cache_service, rate_limiter, mock_openai_response):
        """Test successful LLM API call"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        # Mock the OpenAI client
        with patch.object(service.provider.chat.completions, 'create', return_value=mock_openai_response):
            artifact = {'raw_payload_hash': 'test456', 'roaster_id': 'roaster1', 'name': 'Test Coffee'}
            result = await service.enrich_field(artifact, 'variety', 'Extract the variety')
            
            assert result.field == 'variety'
            assert result.value == 'Extracted value from LLM'
            assert result.provider == 'deepseek'
            assert result.model == 'deepseek-chat'
            assert result.usage['total_tokens'] == 150
            assert service._health_status['available'] is True
            assert service._health_status['consecutive_failures'] == 0
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, deepseek_config, cache_service, rate_limiter, mock_openai_response):
        """Test retry logic on API timeout"""
        deepseek_config.retry_attempts = 2
        deepseek_config.retry_delay = 0.01
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        # Mock to fail once then succeed
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from openai import APITimeoutError
                raise APITimeoutError("Timeout")
            return mock_openai_response
        
        with patch.object(service.provider.chat.completions, 'create', side_effect=side_effect):
            artifact = {'raw_payload_hash': 'test789', 'roaster_id': 'roaster1'}
            result = await service.enrich_field(artifact, 'variety', 'Extract variety')
            
            assert result.field == 'variety'
            assert call_count == 2  # Failed once, succeeded on retry
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, deepseek_config, cache_service, rate_limiter):
        """Test that retries are exhausted and error is raised"""
        deepseek_config.retry_attempts = 2
        deepseek_config.retry_delay = 0.01
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        # Mock to always fail
        with patch.object(service.provider.chat.completions, 'create', side_effect=Exception("API Error")):
            artifact = {'raw_payload_hash': 'test999', 'roaster_id': 'roaster1'}
            
            with pytest.raises(LLMServiceError) as exc_info:
                await service.enrich_field(artifact, 'variety', 'Extract variety')
            
            assert 'failed' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_confidence_threshold(self, deepseek_config, cache_service, rate_limiter):
        """Test confidence threshold retrieval"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        threshold = service.get_confidence_threshold('variety')
        assert threshold == 0.70  # Default from Epic D requirements
    
    @pytest.mark.asyncio
    async def test_is_available(self, deepseek_config, cache_service, rate_limiter):
        """Test service availability check"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        assert service.is_available() is True
        
        # Simulate failures
        service._health_status['consecutive_failures'] = 5
        service._health_status['available'] = False
        assert service.is_available() is False
    
    @pytest.mark.asyncio
    async def test_get_service_health(self, deepseek_config, cache_service, rate_limiter):
        """Test service health status retrieval"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        health = service.get_service_health()
        
        assert health['provider'] == 'deepseek'
        assert health['model'] == 'deepseek-chat'
        assert 'available' in health
        assert 'last_success' in health
        assert 'rate_limit_config' in health
    
    @pytest.mark.asyncio
    async def test_batch_enrich(self, deepseek_config, cache_service, rate_limiter, mock_openai_response):
        """Test batch enrichment of multiple artifacts"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        artifacts = [
            {'raw_payload_hash': 'hash1', 'roaster_id': 'roaster1', 'name': 'Coffee 1'},
            {'raw_payload_hash': 'hash2', 'roaster_id': 'roaster1', 'name': 'Coffee 2'}
        ]
        fields = ['variety']
        
        with patch.object(service.provider.chat.completions, 'create', return_value=mock_openai_response):
            results = await service.batch_enrich(artifacts, fields)
            
            assert len(results) == 2
            assert all(r.field == 'variety' for r in results)
    
    @pytest.mark.asyncio
    async def test_batch_enrich_continues_on_error(self, deepseek_config, cache_service, rate_limiter, mock_openai_response):
        """Test that batch_enrich continues processing even if one item fails"""
        service = DeepSeekWrapperService(deepseek_config, cache_service, rate_limiter)
        
        artifacts = [
            {'raw_payload_hash': 'hash1', 'roaster_id': 'roaster1'},
            {'raw_payload_hash': 'hash2', 'roaster_id': 'roaster2'}
        ]
        fields = ['variety']
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First call failed")
            return mock_openai_response
        
        with patch.object(service.provider.chat.completions, 'create', side_effect=side_effect):
            results = await service.batch_enrich(artifacts, fields)
            
            # Should have 1 result (second artifact succeeded)
            assert len(results) == 1
            assert results[0].field == 'variety'
