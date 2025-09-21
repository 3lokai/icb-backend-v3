#!/usr/bin/env python3
"""
Scheduler for coffee scraping jobs.

This module handles:
- Enqueuing jobs based on roaster cadence
- Full refresh and price-only job scheduling
- Integration with GitHub Actions
- Job prioritization and batching
"""

import argparse
import asyncio
import os
import sys
from typing import List, Dict, Any

import structlog
from dotenv import load_dotenv

from src.config.roaster_config import RoasterConfig
from src.worker.queue import QueueManager
from src.utils.logging import setup_logging

# Load environment variables
load_dotenv()

logger = structlog.get_logger(__name__)


class Scheduler:
    """Manages job scheduling and enqueuing."""
    
    def __init__(self):
        self.roaster_config = RoasterConfig()
        self.queue_manager = QueueManager()
    
    async def schedule_jobs(self, job_type: str = 'full_refresh', roaster_id: str = None):
        """
        Schedule jobs based on job type and roaster selection.
        
        Args:
            job_type: Type of job to schedule ('full_refresh' or 'price_only')
            roaster_id: Specific roaster ID to schedule (None for all)
        """
        logger.info("Starting job scheduling", job_type=job_type, roaster_id=roaster_id)
        
        try:
            # Get roasters to schedule
            if roaster_id:
                roasters = [await self.roaster_config.get_roaster_config(roaster_id)]
            else:
                roasters = await self.roaster_config.get_all_roasters()
            
            if not roasters:
                logger.warning("No roasters found for scheduling")
                return
            
            # Schedule jobs for each roaster
            scheduled_count = 0
            for roaster in roasters:
                try:
                    await self._schedule_roaster_job(roaster, job_type)
                    scheduled_count += 1
                except Exception as e:
                    logger.error("Failed to schedule job for roaster", 
                               roaster_id=roaster.get('id'),
                               error=str(e), 
                               exc_info=True)
            
            logger.info("Job scheduling completed", 
                       scheduled_count=scheduled_count,
                       total_roasters=len(roasters))
            
        except Exception as e:
            logger.error("Scheduling failed", error=str(e), exc_info=True)
            raise
    
    async def _schedule_roaster_job(self, roaster: Dict[str, Any], job_type: str):
        """Schedule a job for a specific roaster."""
        roaster_id = roaster['id']
        roaster_name = roaster.get('name', 'Unknown')
        
        # Determine cadence based on job type
        if job_type == 'full_refresh':
            cadence = roaster.get('full_cadence', '0 3 1 * *')
            priority = 1  # Higher priority for full refresh
        elif job_type == 'price_only':
            cadence = roaster.get('price_cadence', '0 4 * * 0')
            priority = 2  # Lower priority for price updates
        else:
            raise ValueError(f"Unknown job type: {job_type}")
        
        # Create job data
        job_data = {
            'roaster_id': roaster_id,
            'roaster_name': roaster_name,
            'job_type': job_type,
            'cadence': cadence,
            'scheduled_at': asyncio.get_event_loop().time(),
        }
        
        # Enqueue the job
        job_id = await self.queue_manager.enqueue_job(job_data, priority=priority)
        
        logger.info("Job scheduled", 
                   job_id=job_id,
                   roaster_id=roaster_id,
                   roaster_name=roaster_name,
                   job_type=job_type,
                   priority=priority)
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        try:
            stats = await self.queue_manager.get_queue_stats()
            return stats
        except Exception as e:
            logger.error("Failed to get queue status", error=str(e))
            return {"error": str(e)}


async def main():
    """Main entrypoint for the scheduler."""
    # Set up logging
    setup_logging()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Coffee scraping scheduler')
    parser.add_argument('--job-type', 
                       choices=['full_refresh', 'price_only'],
                       default='full_refresh',
                       help='Type of job to schedule')
    parser.add_argument('--roaster-id', 
                       help='Specific roaster ID to schedule (default: all)')
    parser.add_argument('--status', 
                       action='store_true',
                       help='Show queue status instead of scheduling')
    
    args = parser.parse_args()
    
    # Create scheduler
    scheduler = Scheduler()
    
    try:
        if args.status:
            # Show queue status
            status = await scheduler.get_queue_status()
            print(f"Queue Status: {status}")
        else:
            # Schedule jobs
            await scheduler.schedule_jobs(
                job_type=args.job_type,
                roaster_id=args.roaster_id
            )
            
    except Exception as e:
        logger.error("Scheduler failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
