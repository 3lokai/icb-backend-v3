#!/usr/bin/env python3
"""
Main worker entrypoint for coffee scraping jobs.

This module implements the core worker process that:
- Dequeues jobs from Redis queue
- Executes scraping tasks with proper concurrency
- Handles retries and backoff
- Logs job start/end with structured logging
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

import structlog
from dotenv import load_dotenv

from src.config.roaster_config import RoasterConfig
from src.worker.queue import QueueManager
from src.worker.tasks import execute_scraping_job
from src.utils.logging import setup_logging

# Load environment variables
load_dotenv()

logger = structlog.get_logger(__name__)


class Worker:
    """Main worker class that manages job processing."""
    
    def __init__(self, concurrency: int = 3):
        self.concurrency = concurrency
        self.queue_manager = QueueManager()
        self.roaster_config = RoasterConfig()
        self.running = False
        self.semaphore = asyncio.Semaphore(concurrency)
        
    async def start(self):
        """Start the worker process."""
        logger.info("Starting worker", concurrency=self.concurrency)
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            await self._run_worker_loop()
        except Exception as e:
            logger.error("Worker failed", error=str(e), exc_info=True)
            raise
        finally:
            await self._cleanup()
    
    async def _run_worker_loop(self):
        """Main worker loop that processes jobs."""
        while self.running:
            try:
                # Get next job from queue
                job = await self.queue_manager.dequeue_job()
                
                if job is None:
                    # No jobs available, wait a bit
                    await asyncio.sleep(1)
                    continue
                
                # Process job with concurrency control
                await self.semaphore.acquire()
                asyncio.create_task(self._process_job(job))
                
            except Exception as e:
                logger.error("Error in worker loop", error=str(e), exc_info=True)
                await asyncio.sleep(5)  # Back off on errors
    
    async def _process_job(self, job):
        """Process a single job with proper error handling."""
        job_id = job.get('id')
        roaster_id = job.get('roaster_id')
        
        try:
            logger.info("Starting job", job_id=job_id, roaster_id=roaster_id)
            
            # Get roaster configuration
            config = await self.roaster_config.get_roaster_config(roaster_id)
            
            # Execute the scraping job
            result = await execute_scraping_job(job, config)
            
            logger.info("Job completed", 
                       job_id=job_id, 
                       roaster_id=roaster_id,
                       result=result)
            
            # Mark job as completed
            await self.queue_manager.complete_job(job_id)
            
        except Exception as e:
            logger.error("Job failed", 
                        job_id=job_id, 
                        roaster_id=roaster_id,
                        error=str(e), 
                        exc_info=True)
            
            # Handle job failure with retry logic
            await self.queue_manager.fail_job(job_id, str(e))
            
        finally:
            self.semaphore.release()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal", signal=signum)
        self.running = False
    
    async def _cleanup(self):
        """Clean up resources on shutdown."""
        logger.info("Cleaning up worker resources")
        await self.queue_manager.close()


async def main():
    """Main entrypoint for the worker."""
    # Set up logging
    setup_logging()
    
    # Get configuration from environment
    concurrency = int(os.getenv('WORKER_CONCURRENCY', '3'))
    
    # Create and start worker
    worker = Worker(concurrency=concurrency)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error("Worker failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
