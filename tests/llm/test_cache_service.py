"""Unit tests for cache service."""

import pytest
from datetime import datetime

from src.llm.cache_service import CacheService, MemoryBackend
from src.llm.llm_interface import LLMResult
from src.config.cache_config import CacheConfig


@pytest.fixture
def cache_config():
    """Create test cache configuration"""
    return CacheConfig(backend="memory", default_ttl=3600)


@pytest.fixture
def cache_service(cache_config):
    """Create cache service for testing"""
    return CacheService(cache_config)


class TestCacheService:
    """Tests for cache service"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, cache_config):
        """Test cache service initializes correctly"""
        service = CacheService(cache_config)
        
        assert service.config == cache_config
        assert isinstance(service.backend, MemoryBackend)
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_service):
        """Test setting and getting cached values"""
        result = LLMResult(
            field='variety',
            value='Gesha',
            confidence=0.9,
            model='deepseek-chat',
            usage={'total_tokens': 100},
            created_at=datetime.now()
        )
        
        cache_key = 'llm:test123:variety'
        await cache_service.set(cache_key, result, ttl=3600)
        
        cached = await cache_service.get(cache_key)
        
        assert cached is not None
        assert cached.field == 'variety'
        assert cached.value == 'Gesha'
        assert cached.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_service):
        """Test getting a nonexistent cache key returns None"""
        result = await cache_service.get('nonexistent:key')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete(self, cache_service):
        """Test deleting cached values"""
        result = LLMResult(
            field='process',
            value='Washed',
            confidence=0.85,
            model='deepseek-chat',
            usage={'total_tokens': 50},
            created_at=datetime.now()
        )
        
        cache_key = 'llm:delete123:process'
        await cache_service.set(cache_key, result)
        
        # Verify it's cached
        cached = await cache_service.get(cache_key)
        assert cached is not None
        
        # Delete it
        await cache_service.delete(cache_key)
        
        # Verify it's gone
        cached_after = await cache_service.get(cache_key)
        assert cached_after is None
    
    @pytest.mark.asyncio
    async def test_clear_all(self, cache_service):
        """Test clearing all cache entries"""
        # Add multiple entries
        for i in range(3):
            result = LLMResult(
                field=f'field{i}',
                value=f'value{i}',
                confidence=0.8,
                model='deepseek-chat',
                usage={'total_tokens': 50},
                created_at=datetime.now()
            )
            await cache_service.set(f'llm:key{i}:field{i}', result)
        
        # Clear all
        await cache_service.clear()
        
        # Verify all are gone
        for i in range(3):
            cached = await cache_service.get(f'llm:key{i}:field{i}')
            assert cached is None
    
    @pytest.mark.asyncio
    async def test_clear_pattern(self, cache_service):
        """Test clearing cache entries matching pattern"""
        # Add entries with different prefixes
        for prefix in ['llm', 'other']:
            for i in range(2):
                result = LLMResult(
                    field='field',
                    value='value',
                    confidence=0.8,
                    model='deepseek-chat',
                    usage={'total_tokens': 50},
                    created_at=datetime.now()
                )
                await cache_service.set(f'{prefix}:key{i}:field', result)
        
        # Clear only 'llm:*' entries
        await cache_service.clear('llm:*')
        
        # Verify llm entries are gone but other entries remain
        assert await cache_service.get('llm:key0:field') is None
        assert await cache_service.get('llm:key1:field') is None
        assert await cache_service.get('other:key0:field') is not None


class TestMemoryBackend:
    """Tests for in-memory cache backend"""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting values"""
        backend = MemoryBackend()
        
        await backend.set('key1', 'value1', ttl=3600)
        value = await backend.get('key1')
        
        assert value == 'value1'
    
    @pytest.mark.asyncio
    async def test_expiry(self):
        """Test that values expire after TTL"""
        backend = MemoryBackend()
        
        # Set with 0 second TTL (should expire immediately)
        await backend.set('key1', 'value1', ttl=0)
        
        # Small delay to ensure expiry
        import asyncio
        await asyncio.sleep(0.1)
        
        value = await backend.get('key1')
        assert value is None
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting values"""
        backend = MemoryBackend()
        
        await backend.set('key1', 'value1')
        await backend.delete('key1')
        
        value = await backend.get('key1')
        assert value is None
    
    @pytest.mark.asyncio
    async def test_clear_all(self):
        """Test clearing all values"""
        backend = MemoryBackend()
        
        await backend.set('key1', 'value1')
        await backend.set('key2', 'value2')
        await backend.clear()
        
        assert await backend.get('key1') is None
        assert await backend.get('key2') is None
    
    @pytest.mark.asyncio
    async def test_clear_pattern(self):
        """Test clearing with pattern matching"""
        backend = MemoryBackend()
        
        await backend.set('llm:key1', 'value1')
        await backend.set('llm:key2', 'value2')
        await backend.set('other:key3', 'value3')
        
        await backend.clear('llm:*')
        
        assert await backend.get('llm:key1') is None
        assert await backend.get('llm:key2') is None
        assert await backend.get('other:key3') == 'value3'
