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

# Import monitoring components
from src.monitoring.price_job_metrics import PriceJobMetrics
from src.monitoring.rate_limit_backoff import DatabaseRateLimitHandler, RateLimitBackoff, CircuitBreaker
from src.monitoring.price_alert_service import PriceAlertService

logger = structlog.get_logger(__name__)


class QueueManager:
    """Manages job queue operations with monitoring and alerting."""
    
    def __init__(self, redis_url: str = None, monitoring_enabled: bool = True):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_client: Optional[redis.Redis] = None
        self.job_timeout = 3600  # 1 hour default timeout
        
        # Initialize monitoring components
        self.monitoring_enabled = monitoring_enabled
        if monitoring_enabled:
            self.metrics = PriceJobMetrics()
            self.rate_limit_handler = DatabaseRateLimitHandler(
                RateLimitBackoff(),
                CircuitBreaker()
            )
            # Initialize alert service with environment variables
            slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')
            sentry_dsn = os.getenv('SENTRY_DSN', '')
            if slack_webhook and sentry_dsn:
                self.alert_service = PriceAlertService(slack_webhook, sentry_dsn, self.metrics)
            else:
                self.alert_service = None
                logger.warning("Monitoring enabled but Slack/Sentry not configured")
        else:
            self.metrics = None
            self.rate_limit_handler = None
            self.alert_service = None
        
    async def connect(self):
        """Connect to Redis."""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis", url=self.redis_url)
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.aclose()
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
        """Mark a job as completed with monitoring."""
        await self.connect()
        
        start_time = await self.redis_client.hget(f"job:{job_id}", "started_at")
        job_duration = 0.0
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                job_duration = (datetime.now(timezone.utc) - start_dt).total_seconds()
            except (ValueError, TypeError):
                pass
        
        await self.redis_client.hset(f"job:{job_id}", "status", "completed")
        await self.redis_client.hset(f"job:{job_id}", "completed_at", datetime.now(timezone.utc).isoformat())
        
        if result:
            await self.redis_client.hset(f"job:{job_id}", "result", json.dumps(result))
        
        # Record metrics if monitoring enabled
        if self.monitoring_enabled and self.metrics:
            roaster_id = result.get('roaster_id', 'unknown') if result else 'unknown'
            self.metrics.record_price_job_duration(job_duration, roaster_id, "price_update")
            self.metrics.record_job_success(roaster_id, "price_update")
            
            # Record price changes if available
            if result and 'price_changes' in result:
                price_changes = result['price_changes']
                currency = result.get('currency', 'USD')
                self.metrics.record_price_changes(len(price_changes), roaster_id, currency)
        
        # Remove from active jobs
        await self.redis_client.delete(f"job:{job_id}")
        
        logger.info("Job completed", job_id=job_id, duration=job_duration)
    
    async def fail_job(self, job_id: str, error: str, retry: bool = True):
        """Mark a job as failed and handle retry logic with monitoring."""
        await self.connect()
        
        # Get current retry count
        retry_count = int(await self.redis_client.hget(f"job:{job_id}", "retry_count") or 0)
        max_retries = int(await self.redis_client.hget(f"job:{job_id}", "max_retries") or 5)
        
        # Get job data for monitoring
        job_data = await self.redis_client.hgetall(f"job:{job_id}")
        roaster_id = job_data.get('roaster_id', 'unknown') if job_data else 'unknown'
        
        # Record failure metrics
        if self.monitoring_enabled and self.metrics:
            error_type = self._classify_error(error)
            self.metrics.record_job_failure(roaster_id, "price_update", error_type)
        
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
            
            # Send alert for permanent failure
            if self.monitoring_enabled and self.alert_service:
                await self.alert_service.send_job_failure_alert(
                    job_id=job_id,
                    error_type=self._classify_error(error),
                    error_message=error,
                    roaster_id=roaster_id
                )
            
            logger.error("Job permanently failed", 
                        job_id=job_id, 
                        retry_count=retry_count,
                        error=error)
    
    def _classify_error(self, error: str) -> str:
        """Classify error type for monitoring."""
        error_lower = error.lower()
        if 'rate limit' in error_lower or 'too many requests' in error_lower:
            return 'rate_limit'
        elif 'timeout' in error_lower or 'connection' in error_lower:
            return 'network'
        elif 'database' in error_lower or 'sql' in error_lower:
            return 'database'
        elif 'parsing' in error_lower or 'json' in error_lower:
            return 'parsing'
        else:
            return 'unknown'
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific job."""
        await self.connect()
        
        job_data = await self.redis_client.hgetall(f"job:{job_id}")
        return job_data if job_data else None
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics with monitoring data."""
        await self.connect()
        
        # Count jobs by status
        pending_count = await self.redis_client.zcard("job_queue")
        
        # Get active jobs
        active_jobs = await self.redis_client.keys("job:job:*")
        active_count = len(active_jobs)
        
        stats = {
            "pending_jobs": pending_count,
            "active_jobs": active_count,
            "queue_size": pending_count + active_count
        }
        
        # Add monitoring data if enabled
        if self.monitoring_enabled:
            stats["monitoring"] = {
                "enabled": True,
                "metrics_available": self.metrics.get_metrics_summary() if self.metrics else None,
                "rate_limit_handler_healthy": self.rate_limit_handler.is_healthy() if self.rate_limit_handler else None,
                "alert_service_configured": self.alert_service is not None
            }
        else:
            stats["monitoring"] = {"enabled": False}
        
        return stats
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status."""
        if not self.monitoring_enabled:
            return {"monitoring_enabled": False}
        
        status = {
            "monitoring_enabled": True,
            "metrics": self.metrics.get_metrics_summary() if self.metrics else None,
            "rate_limit_handler": self.rate_limit_handler.get_health_status() if self.rate_limit_handler else None,
            "alert_service": self.alert_service.get_alert_status() if self.alert_service else None
        }
        
        return status
    
    async def record_price_spike(self, variant_id: str, old_price: float, new_price: float, roaster_id: str = ""):
        """Record price spike for monitoring and alerting."""
        if not self.monitoring_enabled or not self.alert_service:
            return
        
        from src.monitoring.price_job_metrics import PriceDelta
        from decimal import Decimal
        
        delta = PriceDelta(
            variant_id=variant_id,
            old_price=Decimal(str(old_price)),
            new_price=Decimal(str(new_price)),
            currency="USD",
            roaster_id=roaster_id
        )
        
        await self.alert_service.check_price_spike([delta])
    
    async def record_performance_issue(self, metric_name: str, current_value: float, threshold: float, roaster_id: str = ""):
        """Record performance issue for alerting."""
        if not self.monitoring_enabled or not self.alert_service:
            return
        
        await self.alert_service.send_performance_alert(
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            roaster_id=roaster_id
        )
