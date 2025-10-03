"""
Integration tests for Firecrawl budget management system.

This module tests:
- End-to-end budget workflows
- Integration between all budget components
- Real-world scenarios
- Error handling across components
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService
from src.fetcher.firecrawl_error_handler import FirecrawlErrorHandler
from src.fetcher.firecrawl_budget_exhaustion_handler import FirecrawlBudgetExhaustionHandler
from src.fetcher.firecrawl_budget_reporting_service import FirecrawlBudgetReportingService
from src.config.firecrawl_config import FirecrawlBudgetTracker, FirecrawlConfig


class TestFirecrawlBudgetIntegration:
    """Integration tests for Firecrawl budget management system."""
    
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
    
    @pytest.fixture
    def error_handler(self, budget_service):
        """Create FirecrawlErrorHandler instance."""
        return FirecrawlErrorHandler(budget_service)
    
    @pytest.fixture
    def exhaustion_handler(self, budget_service):
        """Create FirecrawlBudgetExhaustionHandler instance."""
        return FirecrawlBudgetExhaustionHandler(budget_service)
    
    @pytest.fixture
    def reporting_service(self, budget_service):
        """Create FirecrawlBudgetReportingService instance."""
        return FirecrawlBudgetReportingService(budget_service)
    
    @pytest.mark.asyncio
    async def test_complete_budget_workflow_healthy(self, budget_service, error_handler, exhaustion_handler, reporting_service):
        """Test complete budget workflow for healthy budget scenario."""
        roaster_id = "test_roaster"
        
        # Mock healthy budget status
        budget_service.get_roaster_budget_status = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'budget_limit': 1000,
            'used_budget': 200,
            'remaining_budget': 800,
            'usage_percentage': 20.0,
            'firecrawl_enabled': True,
            'status': 'healthy'
        })
        
        # Test budget check
        budget_available = await budget_service.check_budget_and_handle_exhaustion(roaster_id)
        assert budget_available is True
        
        # Test budget usage recording
        usage_recorded = await budget_service.record_budget_usage(roaster_id, 50)
        assert usage_recorded is True
        
        # Test exhaustion check
        exhaustion_result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        assert exhaustion_result['exhausted'] is False
        assert exhaustion_result['status'] == 'healthy'
        
        # Test graceful degradation (should not be needed)
        degradation_result = await exhaustion_handler.implement_graceful_degradation(roaster_id)
        assert degradation_result['success'] is True
        assert 'No degradation needed' in degradation_result['message']
        
        # Test budget report generation
        report = await reporting_service.generate_budget_report(roaster_id)
        assert report['report_type'] == 'roaster_specific'
        assert report['roaster_id'] == roaster_id
    
    @pytest.mark.asyncio
    async def test_complete_budget_workflow_warning(self, budget_service, error_handler, exhaustion_handler, reporting_service):
        """Test complete budget workflow for warning budget scenario."""
        roaster_id = "test_roaster"
        
        # Mock warning budget status
        budget_service.get_roaster_budget_status = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'budget_limit': 1000,
            'used_budget': 850,
            'remaining_budget': 150,
            'usage_percentage': 85.0,
            'firecrawl_enabled': True,
            'status': 'warning'
        })
        
        # Test budget check
        budget_available = await budget_service.check_budget_and_handle_exhaustion(roaster_id)
        assert budget_available is True
        
        # Test budget usage recording
        usage_recorded = await budget_service.record_budget_usage(roaster_id, 50)
        assert usage_recorded is True
        
        # Test exhaustion check
        exhaustion_result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        assert exhaustion_result['exhausted'] is False
        assert exhaustion_result['status'] == 'warning'
        assert 'monitor_usage' in exhaustion_result['recommendations']
        
        # Test graceful degradation (should not be needed)
        degradation_result = await exhaustion_handler.implement_graceful_degradation(roaster_id)
        assert degradation_result['success'] is True
        assert 'No degradation needed' in degradation_result['message']
        
        # Test budget report generation
        report = await reporting_service.generate_budget_report(roaster_id)
        assert report['report_type'] == 'roaster_specific'
        assert report['roaster_id'] == roaster_id
    
    @pytest.mark.asyncio
    async def test_complete_budget_workflow_exhausted(self, budget_service, error_handler, exhaustion_handler, reporting_service):
        """Test complete budget workflow for exhausted budget scenario."""
        roaster_id = "test_roaster"
        
        # Mock exhausted budget status
        budget_service._get_roaster_budget = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'budget_limit': 1000,
            'used_budget': 1000,
            'remaining_budget': 0,
            'usage_percentage': 100.0,
            'firecrawl_enabled': False,
            'status': 'exhausted'
        })
        budget_service.get_roaster_budget_status = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'budget_limit': 1000,
            'used_budget': 1000,
            'remaining_budget': 0,
            'usage_percentage': 100.0,
            'firecrawl_enabled': False,
            'status': 'exhausted'
        })
        
        # Test budget check
        budget_available = await budget_service.check_budget_and_handle_exhaustion(roaster_id)
        assert budget_available is False
        
        # Test budget usage recording (should fail)
        usage_recorded = await budget_service.record_budget_usage(roaster_id, 50)
        assert usage_recorded is False
        
        # Test exhaustion check
        exhaustion_result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        assert exhaustion_result['exhausted'] is True
        assert exhaustion_result['status'] == 'exhausted'
        assert 'disable_firecrawl' in exhaustion_result['recommendations']
        
        # Test graceful degradation (should be implemented)
        degradation_result = await exhaustion_handler.implement_graceful_degradation(roaster_id)
        assert degradation_result['success'] is True
        assert 'Graceful degradation implemented' in degradation_result['message']
        assert 'disable_firecrawl_fallback' in degradation_result['actions_taken']
        
        # Test budget report generation
        report = await reporting_service.generate_budget_report(roaster_id)
        assert report['report_type'] == 'roaster_specific'
        assert report['roaster_id'] == roaster_id
    
    @pytest.mark.asyncio
    async def test_error_handling_with_fallback(self, budget_service, error_handler):
        """Test error handling with fallback operations."""
        roaster_id = "test_roaster"
        
        # Mock successful budget check
        budget_service.check_budget_and_handle_exhaustion = AsyncMock(return_value=True)
        budget_service.record_budget_usage = AsyncMock(return_value=True)
        
        # Mock operation that fails
        async def failing_operation():
            raise Exception("Operation failed")
        
        # Mock fallback that succeeds
        async def successful_fallback():
            return "fallback_result"
        
        # Test error handling with fallback
        result = await error_handler.execute_with_fallback(
            roaster_id=roaster_id,
            operation_name="test_operation",
            operation_func=failing_operation,
            fallback_func=successful_fallback
        )
        
        assert result['success'] is True
        assert result['data'] == "fallback_result"
        assert result['fallback_used'] is True
    
    @pytest.mark.asyncio
    async def test_budget_reset_workflow(self, budget_service, reporting_service):
        """Test budget reset workflow."""
        roaster_id = "test_roaster"
        new_budget_limit = 2000
        
        # Mock successful budget reset
        budget_service.reset_roaster_budget = AsyncMock(return_value=True)
        budget_service.get_roaster_budget_status = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'budget_limit': new_budget_limit,
            'used_budget': 0,
            'remaining_budget': new_budget_limit,
            'usage_percentage': 0.0,
            'firecrawl_enabled': True,
            'status': 'healthy'
        })
        
        # Test budget reset
        reset_success = await budget_service.reset_roaster_budget(roaster_id, new_budget_limit)
        assert reset_success is True
        
        # Test budget status after reset
        status = await budget_service.get_roaster_budget_status(roaster_id)
        assert status['budget_limit'] == new_budget_limit
        assert status['used_budget'] == 0
        assert status['status'] == 'healthy'
        
        # Test report generation after reset
        report = await reporting_service.generate_budget_report(roaster_id)
        assert report['report_type'] == 'roaster_specific'
        assert report['roaster_id'] == roaster_id
    
    @pytest.mark.asyncio
    async def test_operations_dashboard_integration(self, budget_service, reporting_service):
        """Test operations dashboard data integration."""
        # Mock budget service methods
        budget_service.get_budget_report = Mock(return_value={
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'global_stats': {
                'total_budget_used': 500,
                'last_updated': datetime.now(timezone.utc).isoformat()
            },
            'roaster_budgets': {
                'roaster1': {
                    'used_budget': 200,
                    'budget_limit': 1000,
                    'remaining_budget': 800
                },
                'roaster2': {
                    'used_budget': 300,
                    'budget_limit': 1000,
                    'remaining_budget': 700
                }
            }
        })
        
        # Test dashboard data generation
        dashboard_data = await reporting_service.generate_operations_dashboard_data()
        
        assert 'timestamp' in dashboard_data
        assert 'budget_overview' in dashboard_data
        assert 'metrics_summary' in dashboard_data
        assert 'active_alerts' in dashboard_data
        assert 'system_health' in dashboard_data
        
        # Test system health assessment
        health = dashboard_data['system_health']
        assert 'status' in health
        assert 'critical_alerts' in health
        assert 'warning_alerts' in health
        assert 'total_alerts' in health
        assert 'recommendations' in health
    
    @pytest.mark.asyncio
    async def test_budget_exhaustion_event_tracking(self, budget_service, exhaustion_handler):
        """Test budget exhaustion event tracking."""
        roaster_id = "test_roaster"
        
        # Mock exhausted budget status
        budget_service.get_roaster_budget_status = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'budget_limit': 1000,
            'used_budget': 1000,
            'remaining_budget': 0,
            'usage_percentage': 100.0,
            'firecrawl_enabled': False,
            'status': 'exhausted'
        })
        
        # Test exhaustion check (should record event)
        exhaustion_result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        assert exhaustion_result['exhausted'] is True
        
        # Test that event was recorded
        events = exhaustion_handler.get_exhaustion_events()
        assert len(events) == 1
        assert events[0]['roaster_id'] == roaster_id
        assert events[0]['usage_percentage'] == 100.0
        assert events[0]['action_taken'] == 'firecrawl_disabled'
        
        # Test exhaustion statistics
        stats = exhaustion_handler.get_exhaustion_stats()
        assert stats['total_exhaustion_events'] == 1
        assert stats['recent_events_7_days'] == 1
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, budget_service, error_handler):
        """Test error recovery workflow."""
        roaster_id = "test_roaster"
        
        # Mock budget service with error recovery
        budget_service.check_budget_and_handle_exhaustion = AsyncMock(return_value=True)
        budget_service.record_budget_usage = AsyncMock(return_value=True)
        
        # Mock operation that fails initially but succeeds on retry
        call_count = 0
        async def retry_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return "operation_success"
        
        # Test error handling with retry
        result = await error_handler.execute_with_fallback(
            roaster_id=roaster_id,
            operation_name="retry_operation",
            operation_func=retry_operation
        )
        
        assert result['success'] is True
        assert result['data'] == "operation_success"
        assert result['attempts'] == 2  # Should have retried once
        assert result['fallback_used'] is False
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self, budget_service, exhaustion_handler, reporting_service):
        """Test integration with monitoring components."""
        roaster_id = "test_roaster"
        
        # Mock budget status
        budget_service.get_roaster_budget_status = AsyncMock(return_value={
            'roaster_id': roaster_id,
            'budget_limit': 1000,
            'used_budget': 200,
            'remaining_budget': 800,
            'usage_percentage': 20.0,
            'firecrawl_enabled': True,
            'status': 'healthy'
        })
        
        # Test exhaustion check (should record metrics)
        exhaustion_result = await exhaustion_handler.check_budget_exhaustion(roaster_id)
        assert exhaustion_result['exhausted'] is False
        
        # Test report generation (should include metrics)
        report = await reporting_service.generate_budget_report()  # Global report
        assert 'metrics_summary' in report
        assert 'alerts' in report
        
        # Test dashboard data (should include system health)
        dashboard_data = await reporting_service.generate_operations_dashboard_data()
        assert 'system_health' in dashboard_data
        
        health = dashboard_data['system_health']
        assert 'status' in health
        assert 'recommendations' in health
    
    def test_component_initialization(self, budget_service, error_handler, exhaustion_handler, reporting_service):
        """Test that all components are properly initialized."""
        # Test budget service initialization
        assert budget_service.budget_tracker is not None
        assert budget_service.metrics is not None
        assert budget_service.alert_manager is not None
        
        # Test error handler initialization
        assert error_handler.budget_service is not None
        assert error_handler.retry_config is not None
        
        # Test exhaustion handler initialization
        assert exhaustion_handler.budget_service is not None
        assert exhaustion_handler.metrics is not None
        assert exhaustion_handler.alert_manager is not None
        assert exhaustion_handler.thresholds is not None
        
        # Test reporting service initialization
        assert reporting_service.budget_service is not None
        assert reporting_service.metrics is not None
        assert reporting_service.alert_manager is not None
    
    def test_configuration_consistency(self, error_handler, exhaustion_handler):
        """Test that configuration is consistent across components."""
        # Test retry configuration
        retry_config = error_handler.retry_config
        assert retry_config['max_retries'] == 3
        assert retry_config['base_delay'] == 1.0
        assert retry_config['max_delay'] == 60.0
        assert retry_config['jitter'] is True
        
        # Test exhaustion thresholds
        thresholds = exhaustion_handler.thresholds
        assert thresholds['warning'] == 80.0
        assert thresholds['critical'] == 95.0
        assert thresholds['exhausted'] == 100.0
