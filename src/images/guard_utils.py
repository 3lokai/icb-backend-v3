"""
Utility functions for image processing guards.

This module provides utility functions to support image processing guards
across the application.
"""

from typing import Dict, Any, Optional, List
from structlog import get_logger

from .processing_guard import ImageProcessingGuard, ImageGuardViolationError

logger = get_logger(__name__)


def create_image_guard(metadata_only: bool = False) -> ImageProcessingGuard:
    """
    Create an image processing guard instance.
    
    Args:
        metadata_only: Whether this is a metadata-only (price-only) run
        
    Returns:
        Configured ImageProcessingGuard instance
    """
    return ImageProcessingGuard(metadata_only=metadata_only)


def validate_image_processing_allowed(
    guard: ImageProcessingGuard, 
    operation: str
) -> bool:
    """
    Validate that image processing is allowed for the given operation.
    
    Args:
        guard: Image processing guard instance
        operation: Name of the image processing operation
        
    Returns:
        True if image processing is allowed
        
    Raises:
        ImageGuardViolationError: If image processing is not allowed
    """
    if not guard.check_image_processing_allowed(operation):
        raise ImageGuardViolationError(operation, guard.metadata_only)
    
    return True


def log_guard_enforcement(
    guard: ImageProcessingGuard,
    operation: str,
    allowed: bool,
    additional_context: Optional[Dict[str, Any]] = None
):
    """
    Log guard enforcement decisions.
    
    Args:
        guard: Image processing guard instance
        operation: Name of the image processing operation
        allowed: Whether the operation was allowed
        additional_context: Additional context for logging
    """
    context = {
        'operation': operation,
        'allowed': allowed,
        'metadata_only': guard.metadata_only,
        'guard_stats': guard.get_guard_stats()
    }
    
    if additional_context:
        context.update(additional_context)
    
    if allowed:
        logger.info("Image processing allowed", **context)
    else:
        logger.warning("Image processing blocked by guard", **context)


def get_guard_performance_metrics(guard: ImageProcessingGuard) -> Dict[str, Any]:
    """
    Get performance metrics for the image guard.
    
    Args:
        guard: Image processing guard instance
        
    Returns:
        Dictionary with performance metrics
    """
    stats = guard.get_guard_stats()
    
    # Calculate performance metrics
    total_operations = stats['blocks_attempted'] + stats['operations_skipped']
    success_rate = (
        stats['blocks_successful'] / total_operations 
        if total_operations > 0 else 0
    )
    
    return {
        'total_operations': total_operations,
        'success_rate': success_rate,
        'operations_skipped': stats['operations_skipped'],
        'blocks_attempted': stats['blocks_attempted'],
        'blocks_successful': stats['blocks_successful'],
        'blocks_failed': stats['blocks_failed']
    }


def create_guard_context(metadata_only: bool, operation: str) -> Dict[str, Any]:
    """
    Create context information for guard operations.
    
    Args:
        metadata_only: Whether this is a metadata-only run
        operation: Name of the image processing operation
        
    Returns:
        Dictionary with guard context information
    """
    return {
        'metadata_only': metadata_only,
        'operation': operation,
        'guard_type': 'price_only_image_guard',
        'enforcement_level': 'strict'
    }


def validate_guard_configuration(guard: ImageProcessingGuard) -> bool:
    """
    Validate that the guard is properly configured.
    
    Args:
        guard: Image processing guard instance
        
    Returns:
        True if guard is properly configured
        
    Raises:
        ValueError: If guard configuration is invalid
    """
    if not isinstance(guard, ImageProcessingGuard):
        raise ValueError("Guard must be an ImageProcessingGuard instance")
    
    if not hasattr(guard, 'metadata_only'):
        raise ValueError("Guard must have metadata_only attribute")
    
    if not isinstance(guard.metadata_only, bool):
        raise ValueError("metadata_only must be a boolean value")
    
    return True


def create_guard_error_context(
    operation: str,
    metadata_only: bool,
    error: Exception
) -> Dict[str, Any]:
    """
    Create error context for guard violations.
    
    Args:
        operation: Name of the image processing operation
        metadata_only: Whether this is a metadata-only run
        error: The error that occurred
        
    Returns:
        Dictionary with error context information
    """
    return {
        'operation': operation,
        'metadata_only': metadata_only,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'guard_violation': True
    }
