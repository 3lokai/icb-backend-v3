"""
Type checking utilities for validator components.
"""
from typing import Any, Type, TypeVar
from ..config.imagekit_config import ImageKitConfig

T = TypeVar('T')

def assert_type(value: Any, expected_type: Type[T], context: str = "") -> T:
    """
    Assert that a value is of the expected type.
    
    Args:
        value: Value to check
        expected_type: Expected type
        context: Context for error message
        
    Returns:
        The value if it's the correct type
        
    Raises:
        TypeError: If value is not of expected type
    """
    if not isinstance(value, expected_type):
        raise TypeError(
            f"{context}: Expected {expected_type.__name__}, got {type(value).__name__}"
        )
    return value

def assert_imagekit_config(value: Any, context: str = "") -> ImageKitConfig:
    """Assert that a value is an ImageKitConfig instance."""
    return assert_type(value, ImageKitConfig, context)
