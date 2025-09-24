"""
Image processing guard service for price-only runs.

This module provides guard functionality to prevent image processing
during price-only runs, ensuring fast, lightweight price updates.
"""

from typing import Callable, Any, Optional
from functools import wraps
from structlog import get_logger

logger = get_logger(__name__)


class ImageProcessingGuard:
    """
    Guard service to prevent image processing during price-only runs.
    
    Features:
    - Block image processing when metadata_only=True
    - Comprehensive logging for guard enforcement
    - Error handling for guard violations
    - Performance monitoring for guard overhead
    """
    
    def __init__(self, metadata_only: bool = False):
        """
        Initialize image processing guard.
        
        Args:
            metadata_only: Whether this is a metadata-only (price-only) run
        """
        self.metadata_only = metadata_only
        self.logger = get_logger(__name__)
        self.guard_stats = {
            'blocks_attempted': 0,
            'blocks_successful': 0,
            'blocks_failed': 0,
            'operations_skipped': 0
        }
    
    def check_image_processing_allowed(self, operation: str) -> bool:
        """
        Check if image processing is allowed for current operation.
        
        Args:
            operation: Name of the image processing operation
            
        Returns:
            True if image processing is allowed, False if blocked
        """
        if self.metadata_only:
            self.guard_stats['blocks_attempted'] += 1
            self.logger.warning(
                "Image processing blocked for price-only run",
                operation=operation,
                metadata_only=self.metadata_only,
                guard_stats=self.guard_stats
            )
            return False
        
        return True
    
    def guard_image_processing(self, operation: str, func: Callable, *args, **kwargs) -> Any:
        """
        Guard wrapper for image processing operations.
        
        Args:
            operation: Name of the image processing operation
            func: Function to guard
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result if allowed, None if blocked
        """
        if not self.check_image_processing_allowed(operation):
            self.guard_stats['operations_skipped'] += 1
            function_name = getattr(func, '__name__', 'unknown_function')
            self.logger.info(
                "Skipping image processing for price-only run",
                operation=operation,
                function_name=function_name,
                guard_stats=self.guard_stats
            )
            return None
        
        try:
            result = func(*args, **kwargs)
            self.guard_stats['blocks_successful'] += 1
            return result
        except Exception as e:
            self.guard_stats['blocks_failed'] += 1
            function_name = getattr(func, '__name__', 'unknown_function')
            self.logger.error(
                "Image processing operation failed",
                operation=operation,
                function_name=function_name,
                error=str(e),
                guard_stats=self.guard_stats
            )
            raise
    
    def get_guard_stats(self) -> dict:
        """
        Get current guard statistics.
        
        Returns:
            Dictionary with guard statistics
        """
        return self.guard_stats.copy()
    
    def reset_stats(self):
        """Reset guard statistics."""
        self.guard_stats = {
            'blocks_attempted': 0,
            'blocks_successful': 0,
            'blocks_failed': 0,
            'operations_skipped': 0
        }


def guard_image_operation(operation: str):
    """
    Decorator to guard image processing operations.
    
    Args:
        operation: Name of the image processing operation
        
    Returns:
        Decorated function with guard enforcement
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Check if the instance has a guard
            if hasattr(self, 'image_guard') and self.image_guard:
                return self.image_guard.guard_image_processing(
                    operation, func, self, *args, **kwargs
                )
            
            # If no guard, log warning and proceed
            logger.warning(
                "Image operation not guarded",
                operation=operation,
                function_name=func.__name__
            )
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


class ImageGuardError(Exception):
    """Exception raised when image guard violations occur."""
    pass


class ImageGuardViolationError(ImageGuardError):
    """Exception raised when image processing is attempted during price-only runs."""
    
    def __init__(self, operation: str, metadata_only: bool):
        self.operation = operation
        self.metadata_only = metadata_only
        super().__init__(
            f"Image processing blocked for operation '{operation}' "
            f"during price-only run (metadata_only={metadata_only})"
        )
