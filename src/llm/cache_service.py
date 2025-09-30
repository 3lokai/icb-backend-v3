"""Caching service for LLM results with Redis/database backend."""

import json
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import structlog

from src.llm.llm_interface import LLMResult
from src.config.cache_config import CacheConfig

logger = structlog.get_logger(__name__)


class CacheService:
    """Service for caching LLM results with multiple backend support"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.backend = self._initialize_backend(config)
    
    def _initialize_backend(self, config: CacheConfig):
        """Initialize cache backend (Redis or database)"""
        if config.backend == 'redis':
            return RedisBackend(config.redis_url)
        elif config.backend == 'database':
            return DatabaseBackend(config.db_config)
        elif config.backend == 'memory':
            return MemoryBackend()
        else:
            raise ValueError(f"Unsupported cache backend: {config.backend}")
    
    async def get(self, key: str) -> Optional[LLMResult]:
        """Retrieve cached LLM result
        
        Args:
            key: Cache key
            
        Returns:
            Cached LLMResult or None if not found/expired
        """
        try:
            cached_data = await self.backend.get(key)
            if cached_data:
                # Parse cached data back to LLMResult
                data_dict = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                # Convert created_at string back to datetime
                if 'created_at' in data_dict and isinstance(data_dict['created_at'], str):
                    data_dict['created_at'] = datetime.fromisoformat(data_dict['created_at'])
                return LLMResult(**data_dict)
            return None
        except Exception as e:
            logger.warning("cache_retrieval_failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, result: LLMResult, ttl: int = 3600):
        """Store LLM result in cache
        
        Args:
            key: Cache key
            result: LLMResult to cache
            ttl: Time to live in seconds (default 1 hour)
        """
        try:
            # Convert LLMResult to dict for storage
            data_dict = result.model_dump()
            # Convert datetime to ISO format string for JSON serialization
            if 'created_at' in data_dict and isinstance(data_dict['created_at'], datetime):
                data_dict['created_at'] = data_dict['created_at'].isoformat()
            
            cached_data = json.dumps(data_dict)
            await self.backend.set(key, cached_data, ttl=ttl)
            logger.info("cache_stored", key=key, ttl=ttl)
        except Exception as e:
            logger.warning("cache_storage_failed", key=key, error=str(e))
    
    async def delete(self, key: str):
        """Delete cached result
        
        Args:
            key: Cache key to delete
        """
        try:
            await self.backend.delete(key)
            logger.info("cache_deleted", key=key)
        except Exception as e:
            logger.warning("cache_deletion_failed", key=key, error=str(e))
    
    async def clear(self, pattern: Optional[str] = None):
        """Clear cache entries matching pattern
        
        Args:
            pattern: Optional pattern to match keys (e.g., "llm:*")
        """
        try:
            await self.backend.clear(pattern)
            logger.info("cache_cleared", pattern=pattern)
        except Exception as e:
            logger.warning("cache_clear_failed", pattern=pattern, error=str(e))


class MemoryBackend:
    """In-memory cache backend for testing"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[str, datetime]] = {}
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from memory cache"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            else:
                # Expired, remove from cache
                del self._cache[key]
        return None
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in memory cache"""
        expiry = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)
    
    async def delete(self, key: str):
        """Delete key from memory cache"""
        if key in self._cache:
            del self._cache[key]
    
    async def clear(self, pattern: Optional[str] = None):
        """Clear cache entries matching pattern"""
        if pattern:
            # Simple pattern matching for memory backend
            keys_to_delete = [k for k in self._cache.keys() if pattern.replace('*', '') in k]
            for key in keys_to_delete:
                del self._cache[key]
        else:
            self._cache.clear()


class RedisBackend:
    """Redis cache backend (placeholder for future implementation)"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        # TODO: Initialize Redis connection using redis_url
        raise NotImplementedError("Redis backend not yet implemented - use memory or database backend")
    
    async def get(self, key: str) -> Optional[str]:
        raise NotImplementedError()
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        raise NotImplementedError()
    
    async def delete(self, key: str):
        raise NotImplementedError()
    
    async def clear(self, pattern: Optional[str] = None):
        raise NotImplementedError()


class DatabaseBackend:
    """Database cache backend (placeholder for future implementation)"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        # TODO: Initialize database connection
        raise NotImplementedError("Database backend not yet implemented - use memory backend")
    
    async def get(self, key: str) -> Optional[str]:
        raise NotImplementedError()
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        raise NotImplementedError()
    
    async def delete(self, key: str):
        raise NotImplementedError()
    
    async def clear(self, pattern: Optional[str] = None):
        raise NotImplementedError()
