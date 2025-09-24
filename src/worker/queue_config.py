"""
Queue configuration and setup utilities.

This module provides:
- Queue configuration management
- Connection pooling and health checks
- Per-roaster concurrency configuration
- Queue monitoring and metrics
"""

import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


class QueueConfig:
    """Manages queue configuration and connection settings."""
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.connection_pool_size = int(os.getenv('REDIS_POOL_SIZE', '10'))
        self.connection_timeout = int(os.getenv('REDIS_TIMEOUT', '5'))
        self.retry_attempts = int(os.getenv('REDIS_RETRY_ATTEMPTS', '3'))
        self.health_check_interval = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30'))
        
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis connection configuration."""
        return {
            'url': self.redis_url,
            'max_connections': self.connection_pool_size,
            'socket_timeout': self.connection_timeout,
            'socket_connect_timeout': self.connection_timeout,
            'retry_on_timeout': True,
            'health_check_interval': self.health_check_interval,
        }
    
    async def create_connection_pool(self) -> redis.ConnectionPool:
        """Create a Redis connection pool."""
        config = self.get_redis_config()
        
        return redis.ConnectionPool.from_url(
            config['url'],
            max_connections=config['max_connections'],
            socket_timeout=config['socket_timeout'],
            socket_connect_timeout=config['socket_connect_timeout'],
            retry_on_timeout=config['retry_on_timeout'],
            health_check_interval=config['health_check_interval'],
        )


class QueueHealthChecker:
    """Monitors queue health and connection status."""
    
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager
        self.last_health_check = None
        self.health_status = 'unknown'
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        try:
            # Test basic connectivity
            await self.queue_manager.connect()
            
            # Test queue operations
            stats = await self.queue_manager.get_queue_stats()
            
            # Check Redis info
            redis_info = await self._get_redis_info()
            
            self.health_status = 'healthy'
            self.last_health_check = datetime.now(timezone.utc)
            
            return {
                'status': 'healthy',
                'timestamp': self.last_health_check.isoformat(),
                'queue_stats': stats,
                'redis_info': redis_info,
            }
            
        except Exception as e:
            self.health_status = 'unhealthy'
            self.last_health_check = datetime.now(timezone.utc)
            
            logger.error("Queue health check failed", error=str(e), exc_info=True)
            
            return {
                'status': 'unhealthy',
                'timestamp': self.last_health_check.isoformat(),
                'error': str(e),
            }
    
    async def _get_redis_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        try:
            if self.queue_manager.redis_client:
                info = await self.queue_manager.redis_client.info()
                return {
                    'version': info.get('redis_version'),
                    'uptime': info.get('uptime_in_seconds'),
                    'connected_clients': info.get('connected_clients'),
                    'used_memory': info.get('used_memory_human'),
                    'keyspace': info.get('db0', {}),
                }
        except Exception as e:
            logger.warning("Failed to get Redis info", error=str(e))
        
        return {}


class ConcurrencyManager:
    """Manages per-roaster concurrency limits."""
    
    def __init__(self):
        self.active_jobs: Dict[str, int] = {}
        self.concurrency_limits: Dict[str, int] = {}
        self.semaphores: Dict[str, asyncio.Semaphore] = {}
    
    async def get_semaphore(self, roaster_id: str, concurrency_limit: int) -> asyncio.Semaphore:
        """Get or create a semaphore for a roaster."""
        if roaster_id not in self.semaphores:
            self.semaphores[roaster_id] = asyncio.Semaphore(concurrency_limit)
            self.concurrency_limits[roaster_id] = concurrency_limit
            self.active_jobs[roaster_id] = 0
        
        return self.semaphores[roaster_id]
    
    async def acquire_job_slot(self, roaster_id: str) -> bool:
        """Acquire a job slot for a roaster."""
        if roaster_id not in self.semaphores:
            logger.warning("No semaphore found for roaster", roaster_id=roaster_id)
            return False
        
        try:
            await self.semaphores[roaster_id].acquire()
            self.active_jobs[roaster_id] += 1
            
            logger.debug("Acquired job slot", 
                        roaster_id=roaster_id, 
                        active_jobs=self.active_jobs[roaster_id],
                        limit=self.concurrency_limits[roaster_id])
            
            return True
            
        except Exception as e:
            logger.error("Failed to acquire job slot", 
                        roaster_id=roaster_id, 
                        error=str(e))
            return False
    
    async def release_job_slot(self, roaster_id: str):
        """Release a job slot for a roaster."""
        if roaster_id in self.semaphores:
            self.semaphores[roaster_id].release()
            self.active_jobs[roaster_id] = max(0, self.active_jobs[roaster_id] - 1)
            
            logger.debug("Released job slot", 
                        roaster_id=roaster_id, 
                        active_jobs=self.active_jobs[roaster_id])
    
    def get_concurrency_status(self) -> Dict[str, Any]:
        """Get current concurrency status for all roasters."""
        return {
            'active_jobs': self.active_jobs.copy(),
            'concurrency_limits': self.concurrency_limits.copy(),
            'total_active_jobs': sum(self.active_jobs.values()),
        }
