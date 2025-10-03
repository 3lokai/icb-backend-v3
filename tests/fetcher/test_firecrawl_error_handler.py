"""
Tests for Firecrawl error handler.

This module tests:
- Error handling and retry logic
- Fallback behavior
- Budget exhaustion handling
- Integration with budget service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.fetcher.firecrawl_error_handler import FirecrawlErrorHandler
from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService


class TestFirecrawlErrorHandler:
    """Test cases for FirecrawlErrorHandler."""
    
    @pytest.fixture
    def mock_budget_service(self):
        """Create mock budget service."""
        service = Mock(spec=FirecrawlBudgetManagementService)
        service.check_budget_and_handle_exhaustion = AsyncMock(return_value=True)
        service.record_budget_usage = AsyncMock(return_value=True)
        return service
    
    @pytest.fixture
    def error_handler(self, mock_budget_service):
        """Create FirecrawlErrorHandler instance."""
        return FirecrawlErrorHandler(mock_budget_service)
    
    @pytest.fixture
    def mock_operation_func(self):
        """Create mock operation function."""
        return AsyncMock(return_value="operation_result")
    
    @pytest.fixture
    def mock_fallback_func(self):
        """Create mock fallback function."""
        return AsyncMock(return_value="fallback_result")
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_success(self, error_handler, mock_operation_func):
        """Test successful operation execution."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        result = await error_handler.execute_with_fallback(
            roaster_id, operation_name, mock_operation_func
        )
        
        assert result['success'] is True
        assert result['data'] == "operation_result"
        assert result['fallback_used'] is False
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_primary_fails_fallback_succeeds(
        self, error_handler, mock_operation_func, mock_fallback_func
    ):
        """Test fallback execution when primary operation fails."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        # Make primary operation fail
        mock_operation_func.side_effect = Exception("Primary operation failed")
        
        result = await error_handler.execute_with_fallback(
            roaster_id, operation_name, mock_operation_func, mock_fallback_func
        )
        
        assert result['success'] is True
        assert result['data'] == "fallback_result"
        assert result['fallback_used'] is True
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_both_fail(self, error_handler, mock_operation_func, mock_fallback_func):
        """Test when both primary and fallback operations fail."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        # Make both operations fail
        mock_operation_func.side_effect = Exception("Primary operation failed")
        mock_fallback_func.side_effect = Exception("Fallback operation failed")
        
        result = await error_handler.execute_with_fallback(
            roaster_id, operation_name, mock_operation_func, mock_fallback_func
        )
        
        assert result['success'] is False
        assert result['fallback_used'] is True
        assert "Both primary and fallback operations failed" in result['message']
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_budget_exhausted(self, error_handler, mock_operation_func):
        """Test operation when budget is exhausted."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        # Mock budget exhaustion
        error_handler.budget_service.check_budget_and_handle_exhaustion.return_value = False
        
        result = await error_handler.execute_with_fallback(
            roaster_id, operation_name, mock_operation_func
        )
        
        assert result['success'] is False
        assert result['error'] == 'budget_exhausted'
        assert "Budget exhausted" in result['message']
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, error_handler, mock_operation_func):
        """Test successful operation with retry."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        result = await error_handler._execute_with_retry(
            roaster_id, operation_name, mock_operation_func
        )
        
        assert result['success'] is True
        assert result['data'] == "operation_result"
        assert result['attempts'] == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_failure_then_success(self, error_handler, mock_operation_func):
        """Test retry logic with eventual success."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        # Make first attempt fail, second succeed
        mock_operation_func.side_effect = [Exception("First attempt failed"), "operation_result"]
        
        result = await error_handler._execute_with_retry(
            roaster_id, operation_name, mock_operation_func
        )
        
        assert result['success'] is True
        assert result['data'] == "operation_result"
        assert result['attempts'] == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_budget_error_no_retry(self, error_handler, mock_operation_func):
        """Test that budget errors don't trigger retries."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        # Make operation fail with budget error
        mock_operation_func.side_effect = Exception("Budget exhausted")
        
        result = await error_handler._execute_with_retry(
            roaster_id, operation_name, mock_operation_func
        )
        
        assert result['success'] is False
        assert result['attempts'] == 1  # Should not retry
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_max_retries_exceeded(self, error_handler, mock_operation_func):
        """Test retry logic when max retries exceeded."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        # Make all attempts fail
        mock_operation_func.side_effect = Exception("Operation failed")
        
        result = await error_handler._execute_with_retry(
            roaster_id, operation_name, mock_operation_func
        )
        
        assert result['success'] is False
        assert result['attempts'] == 4  # 1 initial + 3 retries
    
    @pytest.mark.asyncio
    async def test_handle_budget_exhaustion_success(self, error_handler):
        """Test successful budget exhaustion handling."""
        roaster_id = "test_roaster"
        
        # Mock budget status
        error_handler.budget_service.get_roaster_budget_status = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'remaining_budget': 0,
            'usage_percentage': 100.0
        })
        
        result = await error_handler.handle_budget_exhaustion(roaster_id)
        
        assert result['success'] is True
        assert "Budget exhaustion handled" in result['message']
    
    @pytest.mark.asyncio
    async def test_handle_budget_exhaustion_not_exhausted(self, error_handler):
        """Test budget exhaustion handling when budget not actually exhausted."""
        roaster_id = "test_roaster"
        
        # Mock budget status with remaining budget
        error_handler.budget_service.get_roaster_budget_status = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'remaining_budget': 100,
            'usage_percentage': 90.0
        })
        
        result = await error_handler.handle_budget_exhaustion(roaster_id)
        
        assert result['success'] is True
        assert "Budget not actually exhausted" in result['message']
    
    @pytest.mark.asyncio
    async def test_handle_budget_exhaustion_no_status(self, error_handler):
        """Test budget exhaustion handling when no status available."""
        roaster_id = "test_roaster"
        
        # Mock no budget status
        error_handler.budget_service.get_roaster_budget_status = AsyncMock(return_value=None)
        
        result = await error_handler.handle_budget_exhaustion(roaster_id)
        
        assert result['success'] is False
        assert "budget_status_unavailable" in result['error']
    
    def test_calculate_retry_delay(self, error_handler):
        """Test retry delay calculation."""
        # Test exponential backoff
        delay1 = error_handler._calculate_retry_delay(0)
        delay2 = error_handler._calculate_retry_delay(1)
        delay3 = error_handler._calculate_retry_delay(2)
        
        assert delay1 > 0
        assert delay2 > delay1
        assert delay3 > delay2
        
        # Test max delay limit
        delay_max = error_handler._calculate_retry_delay(10)
        assert delay_max <= error_handler.retry_config['max_delay']
    
    def test_retry_config_initialization(self, error_handler):
        """Test retry configuration initialization."""
        config = error_handler.retry_config
        
        assert 'max_retries' in config
        assert 'base_delay' in config
        assert 'max_delay' in config
        assert 'jitter' in config
        
        assert config['max_retries'] == 3
        assert config['base_delay'] == 1.0
        assert config['max_delay'] == 60.0
        assert config['jitter'] is True
    
    def test_get_error_stats(self, error_handler):
        """Test error statistics retrieval."""
        stats = error_handler.get_error_stats()
        
        assert 'retry_config' in stats
        assert 'timestamp' in stats
        assert stats['retry_config'] == error_handler.retry_config
    
    @pytest.mark.asyncio
    async def test_execute_fallback_success(self, error_handler, mock_fallback_func):
        """Test successful fallback execution."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        result = await error_handler._execute_fallback(
            roaster_id, operation_name, mock_fallback_func
        )
        
        assert result['success'] is True
        assert result['data'] == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_execute_fallback_failure(self, error_handler, mock_fallback_func):
        """Test fallback execution failure."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        # Make fallback fail
        mock_fallback_func.side_effect = Exception("Fallback failed")
        
        result = await error_handler._execute_fallback(
            roaster_id, operation_name, mock_fallback_func
        )
        
        assert result['success'] is False
        assert "Fallback failed" in result['error']
    
    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, error_handler, mock_operation_func):
        """Test handling of unexpected errors."""
        roaster_id = "test_roaster"
        operation_name = "test_operation"
        
        # Make budget service raise unexpected error to trigger outer try-catch
        error_handler.budget_service.check_budget_and_handle_exhaustion = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        
        result = await error_handler.execute_with_fallback(
            roaster_id, operation_name, mock_operation_func
        )
        
        assert result['success'] is False
        assert result['error'] == 'unexpected_error'
        assert "Unexpected error" in result['message']
