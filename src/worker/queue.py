"""
Queue management for job processing.

This module handles:
- Job dequeuing from Redis
- Job state management (pending, running, completed, failed)
- Retry logic with exponential backoff
- Per-roaster concurrency limits
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


class QueueManager:
    """Manages job queue operations."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_client: Optional[redis.Redis] = None
        self.job_timeout = 3600  # 1 hour default timeout
        
    async def connect(self):
        """Connect to Redis."""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis", url=self.redis_url)
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def enqueue_job(self, job_data: Dict[str, Any], priority: int = 0) -> str:
        """Enqueue a new job."""
        await self.connect()
        
        job_id = f"job:{int(time.time() * 1000)}"
        job = {
            'id': job_id,
            'data': json.dumps(job_data),  # Serialize job_data as JSON string
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'priority': str(priority),
            'retry_count': '0',
            'max_retries': '5'
        }
        
        # Store job data
        await self.redis_client.hset(f"job:{job_id}", mapping=job)
        
        # Add to priority queue
        await self.redis_client.zadd(
            "job_queue", 
            {job_id: priority}
        )
        
        logger.info("Job enqueued", job_id=job_id, priority=priority)
        return job_id
    
    async def dequeue_job(self) -> Optional[Dict[str, Any]]:
        """Dequeue the next available job."""
        await self.connect()
        
        # Get job with highest priority
        result = await self.redis_client.bzpopmin("job_queue", timeout=1)
        
        if not result:
            return None
        
        queue_name, job_id, score = result
        
        # Get job data
        job_data = await self.redis_client.hgetall(f"job:{job_id}")
        
        if not job_data:
            logger.warning("Job data not found", job_id=job_id)
            return None
        
        # Parse the serialized job data
        try:
            parsed_data = json.loads(job_data.get('data', '{}'))
            job_data.update(parsed_data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse job data", job_id=job_id)
            # Keep original job_data if parsing fails
        
        # Update job status
        await self.redis_client.hset(f"job:{job_id}", "status", "running")
        await self.redis_client.hset(f"job:{job_id}", "started_at", datetime.now(timezone.utc).isoformat())
        
        # Set job timeout
        await self.redis_client.expire(f"job:{job_id}", self.job_timeout)
        
        logger.info("Job dequeued", job_id=job_id)
        return job_data
    
    async def complete_job(self, job_id: str, result: Dict[str, Any] = None):
        """Mark a job as completed."""
        await self.connect()
        
        await self.redis_client.hset(f"job:{job_id}", "status", "completed")
        await self.redis_client.hset(f"job:{job_id}", "completed_at", datetime.now(timezone.utc).isoformat())
        
        if result:
            await self.redis_client.hset(f"job:{job_id}", "result", json.dumps(result))
        
        # Remove from active jobs
        await self.redis_client.delete(f"job:{job_id}")
        
        logger.info("Job completed", job_id=job_id)
    
    async def fail_job(self, job_id: str, error: str, retry: bool = True):
        """Mark a job as failed and handle retry logic."""
        await self.connect()
        
        # Get current retry count
        retry_count = int(await self.redis_client.hget(f"job:{job_id}", "retry_count") or 0)
        max_retries = int(await self.redis_client.hget(f"job:{job_id}", "max_retries") or 5)
        
        if retry and retry_count < max_retries:
            # Retry with exponential backoff
            retry_count += 1
            backoff_delay = min(2 ** retry_count, 300)  # Max 5 minutes
            
            await self.redis_client.hset(f"job:{job_id}", "retry_count", retry_count)
            await self.redis_client.hset(f"job:{job_id}", "status", "pending")
            await self.redis_client.hset(f"job:{job_id}", "error", error)
            await self.redis_client.hset(f"job:{job_id}", "retry_at", 
                                       (datetime.now(timezone.utc) + timedelta(seconds=backoff_delay)).isoformat())
            
            # Re-queue with delay
            await self.redis_client.zadd("job_queue", {job_id: time.time() + backoff_delay})
            
            logger.warning("Job failed, retrying", 
                          job_id=job_id, 
                          retry_count=retry_count,
                          backoff_delay=backoff_delay,
                          error=error)
        else:
            # Mark as permanently failed
            await self.redis_client.hset(f"job:{job_id}", "status", "failed")
            await self.redis_client.hset(f"job:{job_id}", "failed_at", datetime.now(timezone.utc).isoformat())
            await self.redis_client.hset(f"job:{job_id}", "error", error)
            
            logger.error("Job permanently failed", 
                        job_id=job_id, 
                        retry_count=retry_count,
                        error=error)
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific job."""
        await self.connect()
        
        job_data = await self.redis_client.hgetall(f"job:{job_id}")
        return job_data if job_data else None
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        await self.connect()
        
        # Count jobs by status
        pending_count = await self.redis_client.zcard("job_queue")
        
        # Get active jobs
        active_jobs = await self.redis_client.keys("job:job:*")
        active_count = len(active_jobs)
        
        return {
            "pending_jobs": pending_count,
            "active_jobs": active_count,
            "queue_size": pending_count + active_count
        }
