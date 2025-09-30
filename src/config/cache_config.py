"""Configuration for cache service."""

from dataclasses import dataclass, field
from typing import Dict, Any
import os


@dataclass
class CacheConfig:
    """Configuration for cache service"""
    
    backend: str = "memory"  # memory, redis, or database
    default_ttl: int = 3600  # 1 hour default
    
    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Database configuration
    db_config: Dict[str, Any] = field(default_factory=lambda: {
        'table': 'llm_cache',
        'connection_string': None
    })
    
    @classmethod
    def from_env(cls) -> 'CacheConfig':
        """Create configuration from environment variables"""
        backend = os.getenv('CACHE_BACKEND', 'memory')
        
        config = cls(
            backend=backend,
            default_ttl=int(os.getenv('CACHE_TTL', '3600'))
        )
        
        # Update Redis config from env if using Redis
        if backend == 'redis':
            config.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        # Update DB config from env if using database
        elif backend == 'database':
            config.db_config = {
                'table': os.getenv('CACHE_TABLE', 'llm_cache'),
                'connection_string': os.getenv('DATABASE_URL')
            }
        
        return config
