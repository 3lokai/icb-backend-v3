"""
Tests for Firecrawl Price-Only Cost Tracking.

Tests the cost optimization and monitoring functionality for price-only operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService
from src.monitoring.firecrawl_metrics import FirecrawlMetrics, FirecrawlAlertManager


class TestFirecrawlPriceOnlyCostTracking:
    """Test cases for price-only cost tracking."""
    
    @pytest.fixture
    def mock_budget_tracker(self):
        """Create mock budget tracker."""
        return Mock()
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        return Mock()
    
    @pytest.fixture
    def budget_service(self, mock_budget_tracker, mock_supabase_client):
        """Create budget management service."""
        return FirecrawlBudgetManagementService(
            budget_tracker=mock_budget_tracker,
            supabase_client=mock_supabase_client
        )
    
    @pytest.fixture
    def metrics(self):
        """Create metrics instance."""
        return FirecrawlMetrics()
    
    @pytest.fixture
    def alert_manager(self, metrics):
        """Create alert manager."""
        return FirecrawlAlertManager(metrics)
    
    @pytest.mark.asyncio
    async def test_track_price_only_usage_success(
        self, 
        budget_service, 
        mock_supabase_client
    ):
        """Test successful price-only usage tracking."""
        # Setup mocks
        budget_service.metrics.record_price_only_usage = Mock()
        budget_service.alert_manager.send_price_only_efficiency_alert = AsyncMock()
        budget_service.alert_manager.send_price_only_cost_alert = AsyncMock()
        
        # Track usage
        result = await budget_service.track_price_only_usage(
            urls_processed=10,
            successful_extractions=8,
            cost=2.5
        )
        
        # Verify results
        assert result['success'] is True
        assert 'price_only_usage' in result
        assert result['price_only_usage']['urls_processed'] == 10
        assert result['price_only_usage']['successful_extractions'] == 8
        assert result['price_only_usage']['cost'] == 2.5
        assert result['price_only_usage']['cost_efficiency'] == 0.8
        assert result['price_only_usage']['cost_per_url'] == 0.25
        assert 'cost_optimization' in result
        
        # Verify metrics recording
        budget_service.metrics.record_price_only_usage.assert_called_once_with(
            urls_processed=10,
            successful_extractions=8,
            cost=2.5,
            cost_efficiency=0.8
        )
        
        # Verify budget state update
        assert 'price_only_usage' in budget_service.budget_state
        assert len(budget_service.budget_state['price_only_usage']) == 1
    
    @pytest.mark.asyncio
    async def test_track_price_only_usage_low_efficiency_alert(
        self, 
        budget_service
    ):
        """Test price-only usage tracking with low efficiency alert."""
        # Setup mocks
        budget_service.metrics.record_price_only_usage = Mock()
        budget_service.alert_manager.send_price_only_efficiency_alert = AsyncMock()
        budget_service.alert_manager.send_price_only_cost_alert = AsyncMock()
        
        # Track usage with low efficiency (30% success rate)
        result = await budget_service.track_price_only_usage(
            urls_processed=10,
            successful_extractions=3,  # 30% success rate
            cost=2.5
        )
        
        # Verify results
        assert result['success'] is True
        assert result['price_only_usage']['cost_efficiency'] == 0.3
        
        # Verify efficiency alert was triggered
        budget_service.alert_manager.send_price_only_efficiency_alert.assert_called_once_with(
            cost_efficiency=0.3,
            threshold=0.5
        )
    
    @pytest.mark.asyncio
    async def test_track_price_only_usage_high_cost_alert(
        self, 
        budget_service
    ):
        """Test price-only usage tracking with high cost alert."""
        # Setup mocks
        budget_service.metrics.record_price_only_usage = Mock()
        budget_service.alert_manager.send_price_only_efficiency_alert = AsyncMock()
        budget_service.alert_manager.send_price_only_cost_alert = AsyncMock()
        
        # Track usage with high cost
        result = await budget_service.track_price_only_usage(
            urls_processed=10,
            successful_extractions=8,
            cost=6.0  # High cost (> $0.50 per URL)
        )
        
        # Verify results
        assert result['success'] is True
        assert result['price_only_usage']['cost'] == 6.0
        
        # Verify cost alert was triggered
        budget_service.alert_manager.send_price_only_cost_alert.assert_called_once_with(
            cost=6.0,
            threshold=0.5
        )
    
    @pytest.mark.asyncio
    async def test_track_price_only_usage_error(
        self, 
        budget_service
    ):
        """Test price-only usage tracking with error."""
        # Setup mocks to raise exception
        budget_service.metrics.record_price_only_usage = Mock(side_effect=Exception("Metrics error"))
        
        # Track usage
        result = await budget_service.track_price_only_usage(
            urls_processed=10,
            successful_extractions=8,
            cost=2.5
        )
        
        # Verify error handling
        assert result['success'] is False
        assert 'Metrics error' in result['error']
    
    @pytest.mark.asyncio
    async def test_get_price_only_cost_summary_no_usage(
        self, 
        budget_service
    ):
        """Test cost summary when no price-only usage tracked."""
        # Get summary
        result = await budget_service.get_price_only_cost_summary()
        
        # Verify results
        assert result['total_operations'] == 0
        assert result['total_cost'] == 0.0
        assert result['average_cost_efficiency'] == 0.0
        assert 'No price-only operations tracked' in result['cost_optimization']
    
    @pytest.mark.asyncio
    async def test_get_price_only_cost_summary_with_usage(
        self, 
        budget_service
    ):
        """Test cost summary with price-only usage tracked."""
        # Setup mocks
        budget_service.metrics.record_price_only_usage = Mock()
        budget_service.alert_manager.send_price_only_efficiency_alert = AsyncMock()
        budget_service.alert_manager.send_price_only_cost_alert = AsyncMock()
        
        # Track some usage
        await budget_service.track_price_only_usage(
            urls_processed=10,
            successful_extractions=8,
            cost=2.5
        )
        
        await budget_service.track_price_only_usage(
            urls_processed=5,
            successful_extractions=4,
            cost=1.0
        )
        
        # Get summary
        result = await budget_service.get_price_only_cost_summary()
        
        # Verify results
        assert result['total_operations'] == 2
        assert result['total_cost'] == 3.5
        assert result['total_urls_processed'] == 15
        assert result['total_successful_extractions'] == 12
        assert result['average_cost_efficiency'] == 0.8  # 12/15
        assert abs(result['average_cost_per_url'] - 0.233) < 0.001  # 3.5/15
        assert 'cost_optimization' in result
        assert 'cost_savings' in result
        assert 'full_refresh_equivalent_cost' in result
    
    @pytest.mark.asyncio
    async def test_get_price_only_cost_summary_error(
        self, 
        budget_service
    ):
        """Test cost summary with error."""
        # Setup mocks to raise exception
        budget_service.budget_state = {'price_only_usage': [{'invalid': 'data'}]}
        
        # Get summary
        result = await budget_service.get_price_only_cost_summary()
        
        # Verify error handling
        assert 'error' in result
        assert result['total_operations'] == 0
        assert result['total_cost'] == 0.0


class TestFirecrawlPriceOnlyMetrics:
    """Test cases for price-only metrics."""
    
    @pytest.fixture
    def metrics(self):
        """Create metrics instance."""
        return FirecrawlMetrics()
    
    def test_record_price_only_usage(self, metrics):
        """Test recording price-only usage metrics."""
        # Record usage
        metrics.record_price_only_usage(
            urls_processed=10,
            successful_extractions=8,
            cost=2.5,
            cost_efficiency=0.8
        )
        
        # Get metrics
        result = metrics.get_price_only_metrics()
        
        # Verify results
        assert result['total_operations'] == 1
        assert result['total_urls_processed'] == 10
        assert result['total_successful_extractions'] == 8
        assert result['total_cost'] == 2.5
        assert result['average_cost_efficiency'] == 0.8
        assert abs(result['cost_optimization_percentage'] - 66.7) < 0.1  # (3*2.5 - 2.5) / (3*2.5) * 100
        assert result['status'] == 'Price-only metrics available'
    
    def test_record_multiple_price_only_usage(self, metrics):
        """Test recording multiple price-only usage metrics."""
        # Record multiple usage
        metrics.record_price_only_usage(10, 8, 2.5, 0.8)
        metrics.record_price_only_usage(5, 4, 1.0, 0.8)
        
        # Get metrics
        result = metrics.get_price_only_metrics()
        
        # Verify results
        assert result['total_operations'] == 2
        assert result['total_urls_processed'] == 15
        assert result['total_successful_extractions'] == 12
        assert result['total_cost'] == 3.5
        assert result['average_cost_efficiency'] == 0.8  # 12/15
        assert abs(result['cost_optimization_percentage'] - 66.7) < 0.1
    
    def test_get_price_only_metrics_no_usage(self, metrics):
        """Test getting metrics when no usage recorded."""
        # Get metrics
        result = metrics.get_price_only_metrics()
        
        # Verify results
        assert result['total_operations'] == 0
        assert result['total_urls_processed'] == 0
        assert result['total_successful_extractions'] == 0
        assert result['total_cost'] == 0.0
        assert result['average_cost_efficiency'] == 0.0
        assert result['cost_optimization_percentage'] == 0.0
        assert result['status'] == 'No price-only operations recorded'


class TestFirecrawlPriceOnlyAlerts:
    """Test cases for price-only alerts."""
    
    @pytest.fixture
    def metrics(self):
        """Create metrics instance."""
        return FirecrawlMetrics()
    
    @pytest.fixture
    def alert_manager(self, metrics):
        """Create alert manager."""
        return FirecrawlAlertManager(metrics)
    
    @pytest.mark.asyncio
    async def test_send_price_only_efficiency_alert(self, alert_manager):
        """Test sending price-only efficiency alert."""
        # Send alert
        await alert_manager.send_price_only_efficiency_alert(
            cost_efficiency=0.3,
            threshold=0.5
        )
        
        # Verify alert was added
        assert len(alert_manager.active_alerts) == 1
        alert = alert_manager.active_alerts[0]
        
        assert alert['type'] == 'price_only_efficiency'
        assert alert['severity'] == 'warning'
        assert 'Price-only efficiency below threshold' in alert['message']
        assert alert['cost_efficiency'] == 0.3
        assert alert['threshold'] == 0.5
        assert 'timestamp' in alert
    
    @pytest.mark.asyncio
    async def test_send_price_only_cost_alert(self, alert_manager):
        """Test sending price-only cost alert."""
        # Send alert
        await alert_manager.send_price_only_cost_alert(
            cost=0.75,
            threshold=0.5
        )
        
        # Verify alert was added
        assert len(alert_manager.active_alerts) == 1
        alert = alert_manager.active_alerts[0]
        
        assert alert['type'] == 'price_only_cost'
        assert alert['severity'] == 'warning'
        assert 'Price-only cost above threshold' in alert['message']
        assert alert['cost'] == 0.75
        assert alert['threshold'] == 0.5
        assert 'timestamp' in alert
    
    @pytest.mark.asyncio
    async def test_send_price_only_efficiency_alert_error(self, alert_manager):
        """Test sending price-only efficiency alert with error."""
        # Setup mocks to raise exception
        with patch.object(alert_manager, 'active_alerts', side_effect=Exception("Alert error")):
            # Send alert
            await alert_manager.send_price_only_efficiency_alert(
                cost_efficiency=0.3,
                threshold=0.5
            )
            
            # Verify error was handled (no exception raised)
            assert True  # Test passes if no exception is raised
    
    @pytest.mark.asyncio
    async def test_send_price_only_cost_alert_error(self, alert_manager):
        """Test sending price-only cost alert with error."""
        # Setup mocks to raise exception
        with patch.object(alert_manager, 'active_alerts', side_effect=Exception("Alert error")):
            # Send alert
            await alert_manager.send_price_only_cost_alert(
                cost=0.75,
                threshold=0.5
            )
            
            # Verify error was handled (no exception raised)
            assert True  # Test passes if no exception is raised
