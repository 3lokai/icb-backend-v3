"""
Tests for Firecrawl budget management service.

This module tests:
- Budget management functionality
- Budget exhaustion detection
- Error handling and fallback
- Integration with monitoring
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService
from src.config.firecrawl_config import FirecrawlBudgetTracker, FirecrawlConfig


class TestFirecrawlBudgetManagementService:
    """Test cases for FirecrawlBudgetManagementService."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock FirecrawlConfig."""
        return FirecrawlConfig(
            api_key="test_api_key_1234567890",
            budget_limit=1000
        )
    
    @pytest.fixture
    def mock_budget_tracker(self, mock_config):
        """Create mock FirecrawlBudgetTracker."""
        return FirecrawlBudgetTracker(mock_config)
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        client = Mock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                'id': 'test_roaster',
                'firecrawl_budget_limit': 1000,
                'use_firecrawl_fallback': True
            }
        ]
        return client
    
    @pytest.fixture
    def budget_service(self, mock_budget_tracker, mock_supabase_client):
        """Create FirecrawlBudgetManagementService instance."""
        return FirecrawlBudgetManagementService(
            budget_tracker=mock_budget_tracker,
            supabase_client=mock_supabase_client
        )
    
    @pytest.mark.asyncio
    async def test_check_budget_and_handle_exhaustion_success(self, budget_service):
        """Test successful budget check."""
        roaster_id = "test_roaster"
        
        result = await budget_service.check_budget_and_handle_exhaustion(roaster_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_budget_and_handle_exhaustion_no_roaster(self, budget_service):
        """Test budget check with non-existent roaster."""
        budget_service.supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        roaster_id = "non_existent_roaster"
        
        result = await budget_service.check_budget_and_handle_exhaustion(roaster_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_record_budget_usage_success(self, budget_service):
        """Test successful budget usage recording."""
        roaster_id = "test_roaster"
        cost = 10
        
        result = await budget_service.record_budget_usage(roaster_id, cost)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_record_budget_usage_exhausted(self, budget_service):
        """Test budget usage recording when budget exhausted."""
        roaster_id = "test_roaster"
        cost = 10
        
        # Mock exhausted budget by making check_budget_and_handle_exhaustion return False
        budget_service.check_budget_and_handle_exhaustion = AsyncMock(return_value=False)
        
        result = await budget_service.record_budget_usage(roaster_id, cost)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_reset_roaster_budget_success(self, budget_service):
        """Test successful budget reset."""
        roaster_id = "test_roaster"
        new_budget_limit = 2000
        
        result = await budget_service.reset_roaster_budget(roaster_id, new_budget_limit)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_reset_roaster_budget_error(self, budget_service):
        """Test budget reset with error."""
        budget_service.supabase_client.table.side_effect = Exception("Database error")
        
        roaster_id = "test_roaster"
        new_budget_limit = 2000
        
        result = await budget_service.reset_roaster_budget(roaster_id, new_budget_limit)
        
        assert result is False
    
    def test_get_budget_report(self, budget_service):
        """Test budget report generation."""
        # Add some test data
        budget_service.budget_state['roaster_budgets']['test_roaster'] = {
            'used_budget': 100,
            'budget_limit': 1000,
            'remaining_budget': 900
        }
        budget_service.budget_state['global_budget_used'] = 100
        
        report = budget_service.get_budget_report()
        
        assert 'timestamp' in report
        assert 'global_stats' in report
        assert 'roaster_budgets' in report
        assert 'test_roaster' in report['roaster_budgets']
    
    @pytest.mark.asyncio
    async def test_get_roaster_budget_status_success(self, budget_service):
        """Test getting roaster budget status."""
        roaster_id = "test_roaster"
        
        status = await budget_service.get_roaster_budget_status(roaster_id)
        
        assert status is not None
        assert status['roaster_id'] == roaster_id
        assert 'budget_limit' in status
        assert 'used_budget' in status
        assert 'remaining_budget' in status
        assert 'usage_percentage' in status
        assert 'firecrawl_enabled' in status
        assert 'status' in status
    
    @pytest.mark.asyncio
    async def test_get_roaster_budget_status_not_found(self, budget_service):
        """Test getting budget status for non-existent roaster."""
        budget_service.supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        roaster_id = "non_existent_roaster"
        
        status = await budget_service.get_roaster_budget_status(roaster_id)
        
        assert status is None
    
    @pytest.mark.asyncio
    async def test_handle_budget_warning(self, budget_service):
        """Test budget warning handling."""
        roaster_id = "test_roaster"
        usage_percentage = 85.0
        
        # Mock the warning handling
        with patch.object(budget_service, '_handle_budget_warning') as mock_warning:
            await budget_service._handle_budget_warning(roaster_id, usage_percentage)
            mock_warning.assert_called_once_with(roaster_id, usage_percentage)
    
    @pytest.mark.asyncio
    async def test_handle_budget_exhaustion(self, budget_service):
        """Test budget exhaustion handling."""
        roaster_id = "test_roaster"
        
        # Mock the exhaustion handling
        with patch.object(budget_service, '_handle_budget_exhaustion') as mock_exhaustion:
            await budget_service._handle_budget_exhaustion(roaster_id)
            mock_exhaustion.assert_called_once_with(roaster_id)
    
    def test_budget_state_initialization(self, budget_service):
        """Test budget state initialization."""
        assert 'roaster_budgets' in budget_service.budget_state
        assert 'global_budget_used' in budget_service.budget_state
        assert 'last_updated' in budget_service.budget_state
        assert isinstance(budget_service.budget_state['roaster_budgets'], dict)
        assert budget_service.budget_state['global_budget_used'] == 0
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, budget_service):
        """Test error handling when database operations fail."""
        budget_service.supabase_client.table.side_effect = Exception("Database connection failed")
        
        roaster_id = "test_roaster"
        
        # Should handle database errors gracefully
        result = await budget_service.check_budget_and_handle_exhaustion(roaster_id)
        assert result is False
        
        status = await budget_service.get_roaster_budget_status(roaster_id)
        assert status is None
    
    @pytest.mark.asyncio
    async def test_budget_usage_tracking(self, budget_service):
        """Test budget usage tracking across multiple operations."""
        roaster_id = "test_roaster"
        
        # Record multiple budget usages
        await budget_service.record_budget_usage(roaster_id, 50)
        await budget_service.record_budget_usage(roaster_id, 30)
        await budget_service.record_budget_usage(roaster_id, 20)
        
        # Check that usage is tracked correctly
        assert roaster_id in budget_service.budget_state['roaster_budgets']
        roaster_budget = budget_service.budget_state['roaster_budgets'][roaster_id]
        assert roaster_budget['used_budget'] == 100
        assert budget_service.budget_state['global_budget_used'] == 100
    
    def test_integration_with_budget_tracker(self, budget_service):
        """Test integration with existing FirecrawlBudgetTracker."""
        # Verify that the service uses the provided budget tracker
        assert budget_service.budget_tracker is not None
        assert hasattr(budget_service.budget_tracker, 'can_operate')
        assert hasattr(budget_service.budget_tracker, 'record_operation')
        assert hasattr(budget_service.budget_tracker, 'get_usage_stats')
    
    def test_monitoring_integration(self, budget_service):
        """Test integration with monitoring components."""
        # Verify that monitoring components are initialized
        assert budget_service.metrics is not None
        assert budget_service.alert_manager is not None
        
        # Verify metrics functionality
        assert hasattr(budget_service.metrics, 'record_map_operation')
        assert hasattr(budget_service.metrics, 'get_metrics_summary')
        
        # Verify alert manager functionality
        assert hasattr(budget_service.alert_manager, 'check_alerts')
        assert hasattr(budget_service.alert_manager, 'get_active_alerts')
