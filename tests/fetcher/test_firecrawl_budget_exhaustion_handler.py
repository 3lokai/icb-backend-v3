"""
Tests for Firecrawl budget exhaustion handler.

This module tests:
- Budget exhaustion detection
- Automatic fallback behavior
- Roaster flagging
- Graceful degradation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.fetcher.firecrawl_budget_exhaustion_handler import FirecrawlBudgetExhaustionHandler
from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService


class TestFirecrawlBudgetExhaustionHandler:
    """Test cases for FirecrawlBudgetExhaustionHandler."""
    
    @pytest.fixture
    def mock_budget_service(self):
        """Create mock budget service."""
        service = Mock(spec=FirecrawlBudgetManagementService)
        service.get_roaster_budget_status = AsyncMock()
        return service
    
    @pytest.fixture
    def exhaustion_handler(self, mock_budget_service):
        """Create FirecrawlBudgetExhaustionHandler instance."""
        return FirecrawlBudgetExhaustionHandler(mock_budget_service)
    
    @pytest.mark.asyncio
    async def test_check_budget_exhaustion_healthy(self, exhaustion_handler):
        """Test budget check when budget is healthy."""
        roaster_id = "test_roaster"
        
        # Mock healthy budget status
        exhaustion_handler.budget_service.get_roaster_budget_status.return_value = {
            'roaster_id': roaster_id,
            'usage_percentage': 50.0,
            'remaining_budget': 500,
            'budget_limit': 1000
        }
        
        result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        
        assert result['exhausted'] is False
        assert result['status'] == 'healthy'
        assert result['usage_percentage'] == 50.0
        assert 'continue_normal_operations' in result['recommendations']
    
    @pytest.mark.asyncio
    async def test_check_budget_exhaustion_warning(self, exhaustion_handler):
        """Test budget check when budget is at warning level."""
        roaster_id = "test_roaster"
        
        # Mock warning budget status
        exhaustion_handler.budget_service.get_roaster_budget_status.return_value = {
            'roaster_id': roaster_id,
            'usage_percentage': 85.0,
            'remaining_budget': 150,
            'budget_limit': 1000
        }
        
        result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        
        assert result['exhausted'] is False
        assert result['status'] == 'warning'
        assert result['usage_percentage'] == 85.0
        assert 'monitor_usage' in result['recommendations']
    
    @pytest.mark.asyncio
    async def test_check_budget_exhaustion_critical(self, exhaustion_handler):
        """Test budget check when budget is critical."""
        roaster_id = "test_roaster"
        
        # Mock critical budget status
        exhaustion_handler.budget_service.get_roaster_budget_status.return_value = {
            'roaster_id': roaster_id,
            'usage_percentage': 97.0,
            'remaining_budget': 30,
            'budget_limit': 1000
        }
        
        result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        
        assert result['exhausted'] is False
        assert result['status'] == 'critical'
        assert result['usage_percentage'] == 97.0
        assert 'monitor_closely' in result['recommendations']
    
    @pytest.mark.asyncio
    async def test_check_budget_exhaustion_exhausted(self, exhaustion_handler):
        """Test budget check when budget is exhausted."""
        roaster_id = "test_roaster"
        
        # Mock exhausted budget status
        exhaustion_handler.budget_service.get_roaster_budget_status.return_value = {
            'roaster_id': roaster_id,
            'usage_percentage': 100.0,
            'remaining_budget': 0,
            'budget_limit': 1000
        }
        
        result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        
        assert result['exhausted'] is True
        assert result['status'] == 'exhausted'
        assert result['usage_percentage'] == 100.0
        assert 'disable_firecrawl' in result['recommendations']
    
    @pytest.mark.asyncio
    async def test_check_budget_exhaustion_no_status(self, exhaustion_handler):
        """Test budget check when no status available."""
        roaster_id = "test_roaster"
        
        # Mock no budget status
        exhaustion_handler.budget_service.get_roaster_budget_status.return_value = None
        
        result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        
        assert result['exhausted'] is False
        assert result['status'] == 'unknown'
        assert 'Could not get budget status' in result['message']
    
    @pytest.mark.asyncio
    async def test_check_budget_exhaustion_error(self, exhaustion_handler):
        """Test budget check when error occurs."""
        roaster_id = "test_roaster"
        
        # Mock error in budget service
        exhaustion_handler.budget_service.get_roaster_budget_status.side_effect = Exception("Service error")
        
        result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        
        assert result['exhausted'] is False
        assert result['status'] == 'error'
        assert 'Error checking budget' in result['message']
    
    @pytest.mark.asyncio
    async def test_implement_graceful_degradation_exhausted(self, exhaustion_handler):
        """Test graceful degradation when budget is exhausted."""
        roaster_id = "test_roaster"
        
        # Mock exhausted budget status
        exhaustion_handler.budget_service.get_roaster_budget_status.return_value = {
            'roaster_id': roaster_id,
            'status': 'exhausted',
            'usage_percentage': 100.0,
            'remaining_budget': 0
        }
        
        result = await exhaustion_handler.implement_graceful_degradation(roaster_id)
        
        assert result['success'] is True
        assert 'Graceful degradation implemented' in result['message']
        assert 'disable_firecrawl_fallback' in result['actions_taken']
        assert 'enable_manual_processing' in result['actions_taken']
    
    @pytest.mark.asyncio
    async def test_implement_graceful_degradation_healthy(self, exhaustion_handler):
        """Test graceful degradation when budget is healthy."""
        roaster_id = "test_roaster"
        
        # Mock healthy budget status
        exhaustion_handler.budget_service.get_roaster_budget_status.return_value = {
            'roaster_id': roaster_id,
            'status': 'healthy',
            'usage_percentage': 50.0,
            'remaining_budget': 500
        }
        
        result = await exhaustion_handler.implement_graceful_degradation(roaster_id)
        
        assert result['success'] is True
        assert 'No degradation needed' in result['message']
    
    @pytest.mark.asyncio
    async def test_implement_graceful_degradation_no_status(self, exhaustion_handler):
        """Test graceful degradation when no budget status available."""
        roaster_id = "test_roaster"
        
        # Mock no budget status
        exhaustion_handler.budget_service.get_roaster_budget_status.return_value = None
        
        result = await exhaustion_handler.implement_graceful_degradation(roaster_id)
        
        assert result['success'] is False
        assert 'Could not get budget status' in result['message']
    
    @pytest.mark.asyncio
    async def test_implement_graceful_degradation_error(self, exhaustion_handler):
        """Test graceful degradation when error occurs."""
        roaster_id = "test_roaster"
        
        # Mock error in budget service
        exhaustion_handler.budget_service.get_roaster_budget_status.side_effect = Exception("Service error")
        
        result = await exhaustion_handler.implement_graceful_degradation(roaster_id)
        
        assert result['success'] is False
        assert 'Error implementing degradation' in result['message']
    
    def test_get_exhaustion_events(self, exhaustion_handler):
        """Test getting exhaustion events."""
        # Add some test events
        exhaustion_handler.exhaustion_events = [
            {
                'roaster_id': 'roaster1',
                'timestamp': datetime.now(timezone.utc),
                'usage_percentage': 100.0,
                'remaining_budget': 0,
                'action_taken': 'firecrawl_disabled'
            },
            {
                'roaster_id': 'roaster2',
                'timestamp': datetime.now(timezone.utc),
                'usage_percentage': 100.0,
                'remaining_budget': 0,
                'action_taken': 'firecrawl_disabled'
            }
        ]
        
        events = exhaustion_handler.get_exhaustion_events()
        
        assert len(events) == 2
        assert events[0]['roaster_id'] == 'roaster1'
        assert events[1]['roaster_id'] == 'roaster2'
        assert all('timestamp' in event for event in events)
        assert all('usage_percentage' in event for event in events)
    
    def test_get_exhaustion_stats(self, exhaustion_handler):
        """Test getting exhaustion statistics."""
        # Add some test events
        exhaustion_handler.exhaustion_events = [
            {
                'roaster_id': 'roaster1',
                'timestamp': datetime.now(timezone.utc),
                'usage_percentage': 100.0,
                'remaining_budget': 0,
                'action_taken': 'firecrawl_disabled'
            }
        ]
        
        stats = exhaustion_handler.get_exhaustion_stats()
        
        assert 'total_exhaustion_events' in stats
        assert 'recent_events_7_days' in stats
        assert 'thresholds' in stats
        assert 'timestamp' in stats
        
        assert stats['total_exhaustion_events'] == 1
        assert stats['recent_events_7_days'] == 1
        assert stats['thresholds']['warning'] == 80.0
        assert stats['thresholds']['critical'] == 95.0
        assert stats['thresholds']['exhausted'] == 100.0
    
    def test_thresholds_initialization(self, exhaustion_handler):
        """Test threshold initialization."""
        thresholds = exhaustion_handler.thresholds
        
        assert 'warning' in thresholds
        assert 'critical' in thresholds
        assert 'exhausted' in thresholds
        
        assert thresholds['warning'] == 80.0
        assert thresholds['critical'] == 95.0
        assert thresholds['exhausted'] == 100.0
    
    def test_exhaustion_events_initialization(self, exhaustion_handler):
        """Test exhaustion events initialization."""
        assert exhaustion_handler.exhaustion_events == []
        assert isinstance(exhaustion_handler.exhaustion_events, list)
    
    @pytest.mark.asyncio
    async def test_handle_exhaustion_records_event(self, exhaustion_handler):
        """Test that exhaustion handling records events."""
        roaster_id = "test_roaster"
        budget_status = {
            'roaster_id': roaster_id,
            'usage_percentage': 100.0,
            'remaining_budget': 0
        }
        
        # Mock the budget service methods
        with patch.object(exhaustion_handler.budget_service, 'get_roaster_budget_status') as mock_status:
            mock_status.return_value = budget_status
            
            await exhaustion_handler._handle_exhaustion(roaster_id, budget_status)
            
            # Check that event was recorded
            assert len(exhaustion_handler.exhaustion_events) == 1
            event = exhaustion_handler.exhaustion_events[0]
            assert event['roaster_id'] == roaster_id
            assert event['usage_percentage'] == 100.0
            assert event['action_taken'] == 'firecrawl_disabled'
    
    @pytest.mark.asyncio
    async def test_handle_critical_warning(self, exhaustion_handler):
        """Test critical warning handling."""
        roaster_id = "test_roaster"
        budget_status = {
            'roaster_id': roaster_id,
            'usage_percentage': 97.0,
            'remaining_budget': 30
        }
        
        await exhaustion_handler._handle_critical_warning(roaster_id, budget_status)
        
        # Should not raise any exceptions
        assert True
    
    @pytest.mark.asyncio
    async def test_handle_warning(self, exhaustion_handler):
        """Test warning handling."""
        roaster_id = "test_roaster"
        budget_status = {
            'roaster_id': roaster_id,
            'usage_percentage': 85.0,
            'remaining_budget': 150
        }
        
        await exhaustion_handler._handle_warning(roaster_id, budget_status)
        
        # Should not raise any exceptions
        assert True
