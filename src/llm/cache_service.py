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
    """Redis cache backend implementation"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Redis client connection"""
        try:
            import redis.asyncio as redis
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            logger.info("Redis client initialized", redis_url=self.redis_url)
        except ImportError:
            raise ImportError("Redis package not installed. Install with: pip install redis")
        except Exception as e:
            logger.error("Failed to initialize Redis client", error=str(e), redis_url=self.redis_url)
            raise
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis cache"""
        try:
            if not self._client:
                self._initialize_client()
            value = await self._client.get(key)
            return value
        except Exception as e:
            logger.warning("Redis get failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in Redis cache with TTL"""
        try:
            if not self._client:
                self._initialize_client()
            await self._client.setex(key, ttl, value)
            logger.debug("Redis set successful", key=key, ttl=ttl)
        except Exception as e:
            logger.warning("Redis set failed", key=key, error=str(e))
    
    async def delete(self, key: str):
        """Delete key from Redis cache"""
        try:
            if not self._client:
                self._initialize_client()
            await self._client.delete(key)
            logger.debug("Redis delete successful", key=key)
        except Exception as e:
            logger.warning("Redis delete failed", key=key, error=str(e))
    
    async def clear(self, pattern: Optional[str] = None):
        """Clear cache entries matching pattern"""
        try:
            if not self._client:
                self._initialize_client()
            if pattern:
                keys = await self._client.keys(pattern)
                if keys:
                    await self._client.delete(*keys)
                    logger.info("Redis clear successful", pattern=pattern, keys_deleted=len(keys))
            else:
                await self._client.flushdb()
                logger.info("Redis clear all successful")
        except Exception as e:
            logger.warning("Redis clear failed", pattern=pattern, error=str(e))


class DatabaseBackend:
    """Database cache backend using Supabase"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client connection"""
        try:
            # Extract supabase client from config
            self._client = self.db_config.get('supabase_client')
            if not self._client:
                raise ValueError("supabase_client not provided in db_config")
            logger.info("Database cache client initialized")
        except Exception as e:
            logger.error("Failed to initialize database cache client", error=str(e))
            raise
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from database cache"""
        try:
            if not self._client:
                return None
            
            # Query cache table for the key
            result = self._client.table("llm_cache").select("value, expires_at").eq("key", key).execute()
            
            if result.data and len(result.data) > 0:
                cache_entry = result.data[0]
                expires_at = cache_entry.get('expires_at')
                
                # Check if expired
                if expires_at:
                    from datetime import datetime
                    if datetime.fromisoformat(expires_at) < datetime.now():
                        # Entry expired, delete it
                        await self.delete(key)
                        return None
                
                return cache_entry.get('value')
            return None
        except Exception as e:
            # Check if it's a table not found error
            if "relation \"llm_cache\" does not exist" in str(e) or "table \"llm_cache\" does not exist" in str(e):
                logger.warning("LLM cache table does not exist. Run migration: create_llm_cache_table.sql", key=key)
                return None
            logger.warning("Database cache get failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in database cache with TTL"""
        try:
            if not self._client:
                return
            
            from datetime import datetime, timedelta
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            # Upsert cache entry
            self._client.table("llm_cache").upsert({
                "key": key,
                "value": value,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now().isoformat()
            }).execute()
            
            logger.debug("Database cache set successful", key=key, ttl=ttl)
        except Exception as e:
            # Check if it's a table not found error
            if "relation \"llm_cache\" does not exist" in str(e) or "table \"llm_cache\" does not exist" in str(e):
                logger.warning("LLM cache table does not exist. Run migration: create_llm_cache_table.sql", key=key)
                return
            logger.warning("Database cache set failed", key=key, error=str(e))
    
    async def delete(self, key: str):
        """Delete key from database cache"""
        try:
            if not self._client:
                return
            
            self._client.table("llm_cache").delete().eq("key", key).execute()
            logger.debug("Database cache delete successful", key=key)
        except Exception as e:
            # Check if it's a table not found error
            if "relation \"llm_cache\" does not exist" in str(e) or "table \"llm_cache\" does not exist" in str(e):
                logger.warning("LLM cache table does not exist. Run migration: create_llm_cache_table.sql", key=key)
                return
            logger.warning("Database cache delete failed", key=key, error=str(e))
    
    async def clear(self, pattern: Optional[str] = None):
        """Clear cache entries matching pattern"""
        try:
            if not self._client:
                return
            
            if pattern:
                # For pattern matching, we need to get all keys and filter
                # This is a simplified implementation - in production you might want
                # to use SQL LIKE or similar for better performance
                result = self._client.table("llm_cache").select("key").execute()
                keys_to_delete = []
                
                for entry in result.data:
                    key = entry.get('key', '')
                    if pattern in key:  # Simple pattern matching
                        keys_to_delete.append(key)
                
                if keys_to_delete:
                    self._client.table("llm_cache").delete().in_("key", keys_to_delete).execute()
                    logger.info("Database cache clear successful", pattern=pattern, keys_deleted=len(keys_to_delete))
            else:
                # Clear all cache entries
                self._client.table("llm_cache").delete().neq("key", "").execute()
                logger.info("Database cache clear all successful")
        except Exception as e:
            # Check if it's a table not found error
            if "relation \"llm_cache\" does not exist" in str(e) or "table \"llm_cache\" does not exist" in str(e):
                logger.warning("LLM cache table does not exist. Run migration: create_llm_cache_table.sql", pattern=pattern)
                return
            logger.warning("Database cache clear failed", pattern=pattern, error=str(e))
