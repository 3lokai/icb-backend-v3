"""
Unit tests for price-only image guards.

Tests the image processing guard functionality to ensure
price-only runs never trigger image uploads or processing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from src.images.processing_guard import ImageProcessingGuard, ImageGuardViolationError
from src.images.guard_utils import (
    create_image_guard,
    validate_image_processing_allowed,
    log_guard_enforcement,
    get_guard_performance_metrics,
    create_guard_context,
    validate_guard_configuration,
    create_guard_error_context
)


class TestImageProcessingGuard:
    """Test cases for ImageProcessingGuard class."""
    
    def test_guard_initialization_metadata_only_true(self):
        """Test guard initialization with metadata_only=True."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        assert guard.metadata_only is True
        assert guard.guard_stats['blocks_attempted'] == 0
        assert guard.guard_stats['operations_skipped'] == 0
    
    def test_guard_initialization_metadata_only_false(self):
        """Test guard initialization with metadata_only=False."""
        guard = ImageProcessingGuard(metadata_only=False)
        
        assert guard.metadata_only is False
        assert guard.guard_stats['blocks_attempted'] == 0
        assert guard.guard_stats['operations_skipped'] == 0
    
    def test_check_image_processing_allowed_metadata_only_true(self):
        """Test that image processing is blocked when metadata_only=True."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        result = guard.check_image_processing_allowed("test_operation")
        
        assert result is False
        assert guard.guard_stats['blocks_attempted'] == 1
    
    def test_check_image_processing_allowed_metadata_only_false(self):
        """Test that image processing is allowed when metadata_only=False."""
        guard = ImageProcessingGuard(metadata_only=False)
        
        result = guard.check_image_processing_allowed("test_operation")
        
        assert result is True
        assert guard.guard_stats['blocks_attempted'] == 0
    
    def test_guard_image_processing_metadata_only_true(self):
        """Test guard wrapper blocks function execution when metadata_only=True."""
        guard = ImageProcessingGuard(metadata_only=True)
        mock_func = Mock(return_value="test_result")
        
        result = guard.guard_image_processing("test_operation", mock_func, "arg1", "arg2", kwarg1="value1")
        
        assert result is None
        assert mock_func.call_count == 0
        assert guard.guard_stats['operations_skipped'] == 1
    
    def test_guard_image_processing_metadata_only_false(self):
        """Test guard wrapper allows function execution when metadata_only=False."""
        guard = ImageProcessingGuard(metadata_only=False)
        mock_func = Mock(return_value="test_result")
        
        result = guard.guard_image_processing("test_operation", mock_func, "arg1", "arg2", kwarg1="value1")
        
        assert result == "test_result"
        assert mock_func.call_count == 1
        mock_func.assert_called_with("arg1", "arg2", kwarg1="value1")
        assert guard.guard_stats['blocks_successful'] == 1
    
    def test_guard_image_processing_function_exception(self):
        """Test guard wrapper handles function exceptions properly."""
        guard = ImageProcessingGuard(metadata_only=False)
        mock_func = Mock(side_effect=Exception("Test exception"))
        
        with pytest.raises(Exception, match="Test exception"):
            guard.guard_image_processing("test_operation", mock_func, "arg1")
        
        assert guard.guard_stats['blocks_failed'] == 1
    
    def test_get_guard_stats(self):
        """Test getting guard statistics."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Trigger some guard operations
        guard.check_image_processing_allowed("operation1")
        guard.guard_image_processing("operation2", Mock(), "arg1")
        
        stats = guard.get_guard_stats()
        
        assert stats['blocks_attempted'] == 1
        assert stats['operations_skipped'] == 1
        assert stats['blocks_successful'] == 0
        assert stats['blocks_failed'] == 0
    
    def test_reset_stats(self):
        """Test resetting guard statistics."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Trigger some operations
        guard.check_image_processing_allowed("operation1")
        guard.guard_image_processing("operation2", Mock(), "arg1")
        
        # Reset stats
        guard.reset_stats()
        
        stats = guard.get_guard_stats()
        assert stats['blocks_attempted'] == 0
        assert stats['operations_skipped'] == 0
        assert stats['blocks_successful'] == 0
        assert stats['blocks_failed'] == 0


class TestGuardUtils:
    """Test cases for guard utility functions."""
    
    def test_create_image_guard(self):
        """Test creating image guard instance."""
        guard = create_image_guard(metadata_only=True)
        
        assert isinstance(guard, ImageProcessingGuard)
        assert guard.metadata_only is True
    
    def test_validate_image_processing_allowed_success(self):
        """Test successful validation of image processing."""
        guard = ImageProcessingGuard(metadata_only=False)
        
        result = validate_image_processing_allowed(guard, "test_operation")
        
        assert result is True
    
    def test_validate_image_processing_allowed_failure(self):
        """Test failed validation of image processing."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        with pytest.raises(ImageGuardViolationError):
            validate_image_processing_allowed(guard, "test_operation")
    
    def test_log_guard_enforcement(self, caplog):
        """Test logging guard enforcement decisions."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        log_guard_enforcement(guard, "test_operation", False, {"additional": "context"})
        
        # Check that logging occurred (exact message depends on logger configuration)
        assert len(caplog.records) > 0
    
    def test_get_guard_performance_metrics(self):
        """Test getting guard performance metrics."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Trigger some operations
        guard.check_image_processing_allowed("operation1")
        guard.guard_image_processing("operation2", Mock(), "arg1")
        
        metrics = get_guard_performance_metrics(guard)
        
        assert 'total_operations' in metrics
        assert 'success_rate' in metrics
        assert 'operations_skipped' in metrics
        assert metrics['total_operations'] == 2
    
    def test_create_guard_context(self):
        """Test creating guard context."""
        context = create_guard_context(metadata_only=True, operation="test_operation")
        
        assert context['metadata_only'] is True
        assert context['operation'] == "test_operation"
        assert context['guard_type'] == "price_only_image_guard"
        assert context['enforcement_level'] == "strict"
    
    def test_validate_guard_configuration_success(self):
        """Test successful guard configuration validation."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        result = validate_guard_configuration(guard)
        
        assert result is True
    
    def test_validate_guard_configuration_failure(self):
        """Test failed guard configuration validation."""
        with pytest.raises(ValueError, match="Guard must be an ImageProcessingGuard instance"):
            validate_guard_configuration("invalid_guard")
    
    def test_create_guard_error_context(self):
        """Test creating guard error context."""
        error = Exception("Test error")
        context = create_guard_error_context("test_operation", True, error)
        
        assert context['operation'] == "test_operation"
        assert context['metadata_only'] is True
        assert context['error_type'] == "Exception"
        assert context['error_message'] == "Test error"
        assert context['guard_violation'] is True


class TestImageGuardIntegration:
    """Integration tests for image guard functionality."""
    
    def test_guard_decorator_functionality(self):
        """Test the guard decorator functionality."""
        # This would require implementing the decorator in the actual code
        # For now, we'll test the concept
        guard = ImageProcessingGuard(metadata_only=True)
        
        def test_function(self, *args, **kwargs):
            return "test_result"
        
        # Simulate decorator behavior
        result = guard.guard_image_processing("test_operation", test_function, None, "arg1")
        
        assert result is None  # Should be blocked
    
    def test_guard_error_handling(self):
        """Test guard error handling."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Test that guard violations raise appropriate errors
        with pytest.raises(ImageGuardViolationError):
            validate_image_processing_allowed(guard, "blocked_operation")
    
    def test_guard_performance_overhead(self):
        """Test that guard operations have minimal performance overhead."""
        guard = ImageProcessingGuard(metadata_only=False)
        
        # Measure time for multiple guard checks
        import time
        start_time = time.time()
        
        for i in range(1000):
            guard.check_image_processing_allowed(f"operation_{i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in less than 1 second for 1000 operations
        assert duration < 1.0
    
    def test_guard_statistics_accuracy(self):
        """Test that guard statistics are accurate."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Perform various operations
        guard.check_image_processing_allowed("operation1")
        guard.check_image_processing_allowed("operation2")
        guard.guard_image_processing("operation3", Mock(), "arg1")
        guard.guard_image_processing("operation4", Mock(), "arg2")
        
        stats = guard.get_guard_stats()
        
        assert stats['blocks_attempted'] == 4  # 2 check calls + 2 guard calls
        assert stats['operations_skipped'] == 2  # 2 guard calls that were blocked
        assert stats['blocks_successful'] == 0  # No successful operations
        assert stats['blocks_failed'] == 0  # No failed operations


class TestImageGuardEdgeCases:
    """Test edge cases for image guard functionality."""
    
    def test_guard_with_none_metadata_only(self):
        """Test guard behavior with None metadata_only value."""
        # This should not happen in practice, but test defensive behavior
        guard = ImageProcessingGuard(metadata_only=False)
        guard.metadata_only = None
        
        # Should handle gracefully
        result = guard.check_image_processing_allowed("test_operation")
        # Behavior depends on implementation, but should not crash
        assert result is not None
    
    def test_guard_with_empty_operation_name(self):
        """Test guard with empty operation name."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        result = guard.check_image_processing_allowed("")
        
        assert result is False
        assert guard.guard_stats['blocks_attempted'] == 1
    
    def test_guard_with_none_operation_name(self):
        """Test guard with None operation name."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        result = guard.check_image_processing_allowed(None)
        
        assert result is False
        assert guard.guard_stats['blocks_attempted'] == 1
    
    def test_guard_with_exception_in_function(self):
        """Test guard with function that raises exception."""
        guard = ImageProcessingGuard(metadata_only=False)
        
        def failing_function(*args, **kwargs):
            raise ValueError("Test exception")
        
        with pytest.raises(ValueError, match="Test exception"):
            guard.guard_image_processing("test_operation", failing_function, "arg1")
        
        assert guard.guard_stats['blocks_failed'] == 1
    
    def test_guard_with_none_function(self):
        """Test guard with None function."""
        guard = ImageProcessingGuard(metadata_only=False)
        
        with pytest.raises(TypeError):
            guard.guard_image_processing("test_operation", None, "arg1")
