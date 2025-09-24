"""
Logging configuration for image deduplication operations.

Provides structured logging for hash computation, deduplication,
and performance monitoring with appropriate log levels and formats.
"""

import logging
import structlog
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class ImageDeduplicationLogger:
    """
    Structured logger for image deduplication operations.
    
    Provides consistent logging format and context for all
    image processing and deduplication activities.
    """
    
    def __init__(self, logger_name: str = "image_deduplication"):
        """
        Initialize the image deduplication logger.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = structlog.get_logger(logger_name)
        
        # Configure structured logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def log_hash_computation_start(self, image_url: str, method: str = "content") -> None:
        """
        Log the start of hash computation for an image.
        
        Args:
            image_url: URL of the image being processed
            method: Method used for hash computation (content, headers)
        """
        self.logger.info(
            "Starting hash computation",
            image_url=image_url,
            method=method,
            operation="hash_computation_start"
        )
    
    def log_hash_computation_success(self, image_url: str, hash_value: str, 
                                    method: str, duration_ms: float) -> None:
        """
        Log successful hash computation.
        
        Args:
            image_url: URL of the image processed
            hash_value: Computed hash value
            method: Method used for computation
            duration_ms: Time taken in milliseconds
        """
        self.logger.info(
            "Hash computation completed",
            image_url=image_url,
            hash_value=hash_value,
            method=method,
            duration_ms=round(duration_ms, 2),
            operation="hash_computation_success"
        )
    
    def log_hash_computation_failure(self, image_url: str, error: str, 
                                   method: str, duration_ms: float) -> None:
        """
        Log failed hash computation.
        
        Args:
            image_url: URL of the image that failed
            error: Error message
            method: Method that failed
            duration_ms: Time taken before failure
        """
        self.logger.warning(
            "Hash computation failed",
            image_url=image_url,
            error=error,
            method=method,
            duration_ms=round(duration_ms, 2),
            operation="hash_computation_failure"
        )
    
    def log_batch_hash_computation_start(self, batch_size: int, method: str = "content") -> None:
        """
        Log the start of batch hash computation.
        
        Args:
            batch_size: Number of images in the batch
            method: Method used for hash computation
        """
        self.logger.info(
            "Starting batch hash computation",
            batch_size=batch_size,
            method=method,
            operation="batch_hash_computation_start"
        )
    
    def log_batch_hash_computation_complete(self, batch_size: int, successful: int, 
                                          failed: int, duration_ms: float) -> None:
        """
        Log completion of batch hash computation.
        
        Args:
            batch_size: Total number of images in batch
            successful: Number of successful computations
            failed: Number of failed computations
            duration_ms: Total time taken in milliseconds
        """
        self.logger.info(
            "Batch hash computation completed",
            batch_size=batch_size,
            successful=successful,
            failed=failed,
            success_rate=round((successful / batch_size) * 100, 2) if batch_size > 0 else 0,
            duration_ms=round(duration_ms, 2),
            avg_duration_ms=round(duration_ms / batch_size, 2) if batch_size > 0 else 0,
            operation="batch_hash_computation_complete"
        )
    
    def log_duplicate_check_start(self, content_hash: str, coffee_id: str) -> None:
        """
        Log the start of duplicate check for an image.
        
        Args:
            content_hash: Hash of the image being checked
            coffee_id: ID of the coffee the image belongs to
        """
        self.logger.debug(
            "Starting duplicate check",
            content_hash=content_hash,
            coffee_id=coffee_id,
            operation="duplicate_check_start"
        )
    
    def log_duplicate_found(self, content_hash: str, existing_image_id: str, 
                           coffee_id: str, duration_ms: float) -> None:
        """
        Log when a duplicate image is found.
        
        Args:
            content_hash: Hash of the duplicate image
            existing_image_id: ID of the existing image
            coffee_id: ID of the coffee
            duration_ms: Time taken for duplicate check
        """
        self.logger.info(
            "Duplicate image found",
            content_hash=content_hash,
            existing_image_id=existing_image_id,
            coffee_id=coffee_id,
            duration_ms=round(duration_ms, 2),
            operation="duplicate_found"
        )
    
    def log_no_duplicate_found(self, content_hash: str, coffee_id: str, 
                              duration_ms: float) -> None:
        """
        Log when no duplicate is found for an image.
        
        Args:
            content_hash: Hash of the image
            coffee_id: ID of the coffee
            duration_ms: Time taken for duplicate check
        """
        self.logger.debug(
            "No duplicate found",
            content_hash=content_hash,
            coffee_id=coffee_id,
            duration_ms=round(duration_ms, 2),
            operation="no_duplicate_found"
        )
    
    def log_deduplication_processing_start(self, coffee_id: str, image_count: int) -> None:
        """
        Log the start of deduplication processing for a coffee.
        
        Args:
            coffee_id: ID of the coffee being processed
            image_count: Number of images to process
        """
        self.logger.info(
            "Starting deduplication processing",
            coffee_id=coffee_id,
            image_count=image_count,
            operation="deduplication_processing_start"
        )
    
    def log_deduplication_processing_complete(self, coffee_id: str, total_images: int,
                                            new_images: int, duplicates: int,
                                            duration_ms: float) -> None:
        """
        Log completion of deduplication processing.
        
        Args:
            coffee_id: ID of the coffee processed
            total_images: Total number of images processed
            new_images: Number of new images
            duplicates: Number of duplicates found
            duration_ms: Total processing time in milliseconds
        """
        self.logger.info(
            "Deduplication processing completed",
            coffee_id=coffee_id,
            total_images=total_images,
            new_images=new_images,
            duplicates=duplicates,
            duplicate_rate=round((duplicates / total_images) * 100, 2) if total_images > 0 else 0,
            duration_ms=round(duration_ms, 2),
            avg_duration_ms=round(duration_ms / total_images, 2) if total_images > 0 else 0,
            operation="deduplication_processing_complete"
        )
    
    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Log performance metrics for image processing.
        
        Args:
            metrics: Dictionary containing performance metrics
        """
        self.logger.info(
            "Performance metrics recorded",
            metrics=metrics,
            operation="performance_metrics"
        )
    
    def log_cache_operation(self, operation: str, key: str, hit: bool = None, 
                           size: int = None) -> None:
        """
        Log cache operations for hash caching.
        
        Args:
            operation: Type of cache operation (get, set, clear)
            key: Cache key
            hit: Whether it was a cache hit (for get operations)
            size: Current cache size (for set/clear operations)
        """
        log_data = {
            "operation": f"cache_{operation}",
            "cache_key": key
        }
        
        if hit is not None:
            log_data["cache_hit"] = hit
        if size is not None:
            log_data["cache_size"] = size
        
        self.logger.debug("Cache operation", **log_data)
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None) -> None:
        """
        Log errors with context information.
        
        Args:
            error: Exception that occurred
            context: Additional context information
        """
        log_data = {
            "error": str(error),
            "error_type": type(error).__name__,
            "operation": "error"
        }
        
        if context:
            log_data.update(context)
        
        self.logger.error("Error occurred", **log_data)
    
    def log_system_health(self, status: str, details: Dict[str, Any] = None) -> None:
        """
        Log system health status.
        
        Args:
            status: Health status (healthy, degraded, unhealthy)
            details: Additional health details
        """
        log_data = {
            "status": status,
            "operation": "system_health"
        }
        
        if details:
            log_data.update(details)
        
        if status == "healthy":
            self.logger.info("System health check", **log_data)
        elif status == "degraded":
            self.logger.warning("System health degraded", **log_data)
        else:
            self.logger.error("System health unhealthy", **log_data)


def get_image_deduplication_logger(logger_name: str = "image_deduplication") -> ImageDeduplicationLogger:
    """
    Get a configured image deduplication logger.
    
    Args:
        logger_name: Name for the logger instance
        
    Returns:
        Configured ImageDeduplicationLogger instance
    """
    return ImageDeduplicationLogger(logger_name)


def configure_image_logging(level: str = "INFO", format_type: str = "json") -> None:
    """
    Configure logging for image deduplication operations.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_type: Log format (json, text)
    """
    # Set up basic logging configuration
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure structlog based on format type
    if format_type == "json":
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
