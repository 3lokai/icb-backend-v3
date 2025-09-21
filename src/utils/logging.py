"""
Logging configuration for the worker system.

This module sets up structured logging with:
- JSON format for production
- Human-readable format for development
- Proper log levels and filtering
- Contextual information for debugging
"""

import logging
import os
import sys
from typing import Any, Dict

import structlog


def setup_logging():
    """Set up structured logging for the worker."""
    
    # Get configuration from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = os.getenv('LOG_FORMAT', 'json')
    environment = os.getenv('ENVIRONMENT', 'development')
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
    ]
    
    if log_format == 'json':
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        logger_factory=structlog.WriteLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(message)s",
        stream=sys.stdout,
    )
    
    # Set third-party loggers to appropriate levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for the given name."""
    return structlog.get_logger(name)


def log_job_start(job_id: str, roaster_id: str, job_type: str) -> None:
    """Log the start of a job execution."""
    logger = get_logger(__name__)
    logger.info("Job started", 
               job_id=job_id, 
               roaster_id=roaster_id, 
               job_type=job_type)


def log_job_end(job_id: str, roaster_id: str, result: Dict[str, Any]) -> None:
    """Log the end of a job execution."""
    logger = get_logger(__name__)
    logger.info("Job completed", 
               job_id=job_id, 
               roaster_id=roaster_id, 
               result=result)


def log_job_error(job_id: str, roaster_id: str, error: str, exc_info: bool = False) -> None:
    """Log a job execution error."""
    logger = get_logger(__name__)
    logger.error("Job failed", 
                job_id=job_id, 
                roaster_id=roaster_id, 
                error=error,
                exc_info=exc_info)
