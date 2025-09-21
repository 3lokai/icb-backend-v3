"""
Integration tests for queue functionality.

This module tests:
- Queue connection and basic operations
- Job enqueuing and dequeuing
- Retry logic and error handling
- Concurrency management
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from src.worker.queue import QueueManager
from src.worker.queue_config import QueueConfig, QueueHealthChecker, ConcurrencyManager


class TestQueueIntegration:
    """Test queue integration functionality."""
    
    @pytest.fixture
    def queue_manager(self):
        """Create a queue manager for testing."""
        return QueueManager(redis_url='redis://localhost:6379/1')  # Use test DB
    
    @pytest.fixture
    def concurrency_manager(self):
        """Create a concurrency manager for testing."""
        return ConcurrencyManager()
    
    @pytest.mark.asyncio
    async def test_queue_connection(self, queue_manager):
        """Test queue connection."""
        await queue_manager.connect()
        assert queue_manager.redis_client is not None
    
    @pytest.mark.asyncio
    async def test_job_enqueue_dequeue(self, queue_manager):
        """Test basic job enqueuing and dequeuing."""
        # Enqueue a test job
        job_data = {
            'roaster_id': 'test_roaster',
            'job_type': 'full_refresh'
        }
        
        job_id = await queue_manager.enqueue_job(job_data, priority=1)
        assert job_id is not None
        
        # Dequeue the job
        dequeued_job = await queue_manager.dequeue_job()
        assert dequeued_job is not None
        assert dequeued_job['roaster_id'] == 'test_roaster'
        assert dequeued_job['data']['job_type'] == 'full_refresh'
    
    @pytest.mark.asyncio
    async def test_job_completion(self, queue_manager):
        """Test job completion flow."""
        # Enqueue and dequeue a job
        job_data = {'roaster_id': 'test_roaster', 'job_type': 'full_refresh'}
        job_id = await queue_manager.enqueue_job(job_data)
        job = await queue_manager.dequeue_job()
        
        # Complete the job
        result = {'status': 'completed', 'items_processed': 42}
        await queue_manager.complete_job(job_id, result)
        
        # Verify job is no longer in queue
        job_status = await queue_manager.get_job_status(job_id)
        assert job_status is None or job_status.get('status') == 'completed'
    
    @pytest.mark.asyncio
    async def test_job_failure_retry(self, queue_manager):
        """Test job failure and retry logic."""
        # Enqueue a job
        job_data = {'roaster_id': 'test_roaster', 'job_type': 'full_refresh'}
        job_id = await queue_manager.enqueue_job(job_data)
        
        # Simulate job failure
        await queue_manager.fail_job(job_id, "Test error", retry=True)
        
        # Check that job is retried
        job_status = await queue_manager.get_job_status(job_id)
        assert job_status is not None
        assert job_status.get('status') == 'pending'
        assert int(job_status.get('retry_count', 0)) == 1
    
    @pytest.mark.asyncio
    async def test_queue_stats(self, queue_manager):
        """Test queue statistics."""
        # Enqueue some test jobs
        for i in range(3):
            job_data = {'roaster_id': f'test_roaster_{i}', 'job_type': 'full_refresh'}
            await queue_manager.enqueue_job(job_data)
        
        # Get queue stats
        stats = await queue_manager.get_queue_stats()
        assert 'pending_jobs' in stats
        assert 'active_jobs' in stats
        assert 'queue_size' in stats
    
    @pytest.mark.asyncio
    async def test_concurrency_management(self, concurrency_manager):
        """Test concurrency management."""
        roaster_id = 'test_roaster'
        concurrency_limit = 2
        
        # Create semaphore
        semaphore = await concurrency_manager.get_semaphore(roaster_id, concurrency_limit)
        assert semaphore is not None
        
        # Acquire job slots
        slot1 = await concurrency_manager.acquire_job_slot(roaster_id)
        assert slot1 is True
        
        slot2 = await concurrency_manager.acquire_job_slot(roaster_id)
        assert slot2 is True
        
        # Third slot should be blocked (would need async context)
        # This is a simplified test - in practice, you'd test with asyncio.wait_for
        
        # Release slots
        await concurrency_manager.release_job_slot(roaster_id)
        await concurrency_manager.release_job_slot(roaster_id)
        
        # Check status
        status = concurrency_manager.get_concurrency_status()
        assert roaster_id in status['active_jobs']
        assert status['active_jobs'][roaster_id] == 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, queue_manager):
        """Test queue health checking."""
        health_checker = QueueHealthChecker(queue_manager)
        
        # Perform health check
        health_status = await health_checker.check_health()
        
        assert 'status' in health_status
        assert 'timestamp' in health_status
        assert health_status['status'] in ['healthy', 'unhealthy']


class TestQueueConfig:
    """Test queue configuration."""
    
    def test_queue_config_creation(self):
        """Test queue configuration creation."""
        config = QueueConfig()
        
        redis_config = config.get_redis_config()
        assert 'url' in redis_config
        assert 'max_connections' in redis_config
        assert 'socket_timeout' in redis_config
    
    def test_connection_pool_config(self):
        """Test connection pool configuration."""
        config = QueueConfig()
        
        # This would test the actual pool creation in a real test
        # For now, just verify the config is valid
        redis_config = config.get_redis_config()
        assert redis_config['max_connections'] > 0
        assert redis_config['socket_timeout'] > 0


@pytest.mark.asyncio
async def test_queue_integration_workflow():
    """Test complete queue integration workflow."""
    # This is a comprehensive test that would run in a real environment
    # For now, it's a placeholder that shows the expected workflow
    
    # 1. Create queue manager
    queue_manager = QueueManager(redis_url='redis://localhost:6379/1')
    
    try:
        # 2. Connect to queue
        await queue_manager.connect()
        
        # 3. Enqueue multiple jobs
        job_ids = []
        for i in range(5):
            job_data = {
                'roaster_id': f'roaster_{i}',
                'job_type': 'full_refresh'
            }
            job_id = await queue_manager.enqueue_job(job_data, priority=i)
            job_ids.append(job_id)
        
        # 4. Process jobs
        processed_jobs = []
        for _ in range(5):
            job = await queue_manager.dequeue_job()
            if job:
                processed_jobs.append(job)
                await queue_manager.complete_job(job['id'])
        
        # 5. Verify all jobs processed
        assert len(processed_jobs) == 5
        
        # 6. Check final queue stats
        stats = await queue_manager.get_queue_stats()
        assert stats['pending_jobs'] == 0
        
    finally:
        await queue_manager.close()
