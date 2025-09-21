"""
Tests for scheduler functionality.

This module tests:
- Scheduler job creation and enqueuing
- Roaster configuration loading
- Job prioritization and batching
- Integration with queue system
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.scheduler.main import Scheduler
from src.config.roaster_config import RoasterConfig
from src.worker.queue import QueueManager


class TestScheduler:
    """Test scheduler functionality."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a scheduler for testing."""
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key'
        }):
            return Scheduler()
    
    @pytest.fixture
    def mock_roaster_config(self):
        """Create mock roaster configuration."""
        config = MagicMock(spec=RoasterConfig)
        config.get_roaster_config = AsyncMock()
        config.get_all_roasters = AsyncMock()
        return config
    
    @pytest.fixture
    def mock_queue_manager(self):
        """Create mock queue manager."""
        manager = MagicMock(spec=QueueManager)
        manager.enqueue_job = AsyncMock()
        manager.get_queue_stats = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_schedule_full_refresh_jobs(self, scheduler, mock_roaster_config, mock_queue_manager):
        """Test scheduling full refresh jobs."""
        # Mock roaster data
        roasters = [
            {
                'id': 'roaster_1',
                'name': 'Test Roaster 1',
                'full_cadence': '0 3 1 * *',
                'price_cadence': '0 4 * * 0'
            },
            {
                'id': 'roaster_2', 
                'name': 'Test Roaster 2',
                'full_cadence': '0 3 1 * *',
                'price_cadence': '0 4 * * 0'
            }
        ]
        
        mock_roaster_config.get_all_roasters.return_value = roasters
        mock_queue_manager.enqueue_job.return_value = 'job_123'
        
        # Patch dependencies
        with patch.object(scheduler, 'roaster_config', mock_roaster_config), \
             patch.object(scheduler, 'queue_manager', mock_queue_manager):
            
            # Schedule jobs
            await scheduler.schedule_jobs(job_type='full_refresh')
            
            # Verify jobs were enqueued
            assert mock_queue_manager.enqueue_job.call_count == 2
            
            # Check job data
            calls = mock_queue_manager.enqueue_job.call_args_list
            for i, call in enumerate(calls):
                job_data, kwargs = call[0], call[1]
                assert job_data['roaster_id'] == roasters[i]['id']
                assert job_data['job_type'] == 'full_refresh'
                assert kwargs['priority'] == 1  # Higher priority for full refresh
    
    @pytest.mark.asyncio
    async def test_schedule_price_only_jobs(self, scheduler, mock_roaster_config, mock_queue_manager):
        """Test scheduling price-only jobs."""
        roasters = [
            {
                'id': 'roaster_1',
                'name': 'Test Roaster 1',
                'full_cadence': '0 3 1 * *',
                'price_cadence': '0 4 * * 0'
            }
        ]
        
        mock_roaster_config.get_all_roasters.return_value = roasters
        mock_queue_manager.enqueue_job.return_value = 'job_123'
        
        with patch.object(scheduler, 'roaster_config', mock_roaster_config), \
             patch.object(scheduler, 'queue_manager', mock_queue_manager):
            
            await scheduler.schedule_jobs(job_type='price_only')
            
            # Verify job was enqueued with correct priority
            mock_queue_manager.enqueue_job.assert_called_once()
            call_args = mock_queue_manager.enqueue_job.call_args
            job_data, kwargs = call_args[0], call_args[1]
            assert job_data['job_type'] == 'price_only'
            assert kwargs['priority'] == 2  # Lower priority for price updates
    
    @pytest.mark.asyncio
    async def test_schedule_specific_roaster(self, scheduler, mock_roaster_config, mock_queue_manager):
        """Test scheduling jobs for a specific roaster."""
        roaster_config = {
            'id': 'specific_roaster',
            'name': 'Specific Roaster',
            'full_cadence': '0 3 1 * *',
            'price_cadence': '0 4 * * 0'
        }
        
        mock_roaster_config.get_roaster_config.return_value = roaster_config
        mock_queue_manager.enqueue_job.return_value = 'job_123'
        
        with patch.object(scheduler, 'roaster_config', mock_roaster_config), \
             patch.object(scheduler, 'queue_manager', mock_queue_manager):
            
            await scheduler.schedule_jobs(job_type='full_refresh', roaster_id='specific_roaster')
            
            # Verify roaster config was loaded
            mock_roaster_config.get_roaster_config.assert_called_once_with('specific_roaster')
            
            # Verify job was enqueued
            mock_queue_manager.enqueue_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_roasters_found(self, scheduler, mock_roaster_config, mock_queue_manager):
        """Test handling when no roasters are found."""
        mock_roaster_config.get_all_roasters.return_value = []
        
        with patch.object(scheduler, 'roaster_config', mock_roaster_config), \
             patch.object(scheduler, 'queue_manager', mock_queue_manager):
            
            await scheduler.schedule_jobs(job_type='full_refresh')
            
            # Verify no jobs were enqueued
            mock_queue_manager.enqueue_job.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_scheduler_error_handling(self, scheduler, mock_roaster_config, mock_queue_manager):
        """Test scheduler error handling."""
        # Simulate roaster config error
        mock_roaster_config.get_all_roasters.side_effect = Exception("Database error")
        
        with patch.object(scheduler, 'roaster_config', mock_roaster_config), \
             patch.object(scheduler, 'queue_manager', mock_queue_manager):
            
            # Should not raise exception, but log error
            await scheduler.schedule_jobs(job_type='full_refresh')
            
            # Verify no jobs were enqueued due to error
            mock_queue_manager.enqueue_job.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_queue_status(self, scheduler, mock_queue_manager):
        """Test getting queue status."""
        mock_stats = {
            'pending_jobs': 5,
            'active_jobs': 2,
            'queue_size': 7
        }
        mock_queue_manager.get_queue_stats.return_value = mock_stats
        
        with patch.object(scheduler, 'queue_manager', mock_queue_manager):
            status = await scheduler.get_queue_status()
            
            assert status == mock_stats
            mock_queue_manager.get_queue_stats.assert_called_once()


class TestSchedulerIntegration:
    """Integration tests for scheduler."""
    
    @pytest.mark.asyncio
    async def test_scheduler_workflow(self):
        """Test complete scheduler workflow."""
        # This would be a more comprehensive integration test
        # that tests the full workflow from roaster config to job enqueuing
        
        scheduler = Scheduler()
        
        # Mock all dependencies
        with patch.object(scheduler.roaster_config, 'get_all_roasters') as mock_get_roasters, \
             patch.object(scheduler.queue_manager, 'enqueue_job') as mock_enqueue:
            
            # Set up mock data
            mock_get_roasters.return_value = [
                {
                    'id': 'test_roaster',
                    'name': 'Test Roaster',
                    'full_cadence': '0 3 1 * *',
                    'price_cadence': '0 4 * * 0'
                }
            ]
            mock_enqueue.return_value = 'job_123'
            
            # Run scheduler
            await scheduler.schedule_jobs(job_type='full_refresh')
            
            # Verify workflow
            mock_get_roasters.assert_called_once()
            mock_enqueue.assert_called_once()
            
            # Check job data
            call_args = mock_enqueue.call_args
            job_data = call_args[0][0]
            assert job_data['roaster_id'] == 'test_roaster'
            assert job_data['job_type'] == 'full_refresh'


@pytest.mark.asyncio
async def test_scheduler_command_line_interface():
    """Test scheduler command line interface."""
    # This would test the actual command line interface
    # For now, it's a placeholder that shows expected behavior
    
    import sys
    from unittest.mock import patch
    
    # Mock command line arguments
    test_args = ['scheduler.py', '--job-type', 'full_refresh', '--status']
    
    with patch.object(sys, 'argv', test_args):
        # This would test the actual CLI parsing and execution
        # In a real test, you'd capture stdout/stderr and verify output
        pass
