"""
Tests for PlatformMonitoringService - platform monitoring and analytics.

Tests the monitoring functionality for Story A.6: Platform-Based Fetcher Selection with Automatic Fallback.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from src.monitoring.platform_monitoring_service import PlatformMonitoringService


class TestPlatformMonitoringService:
    """Test cases for PlatformMonitoringService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = Mock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        return mock_client
    
    @pytest.fixture
    def monitoring_service(self, mock_supabase_client):
        """Create a PlatformMonitoringService instance."""
        return PlatformMonitoringService(supabase_client=mock_supabase_client)
    
    def test_initialization_with_supabase_client(self, mock_supabase_client):
        """Test service initialization with provided Supabase client."""
        service = PlatformMonitoringService(supabase_client=mock_supabase_client)
        assert service.supabase_client == mock_supabase_client
    
    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_ANON_KEY': 'test-key'})
    @patch('src.monitoring.platform_monitoring_service.create_client')
    def test_initialization_without_supabase_client(self, mock_create_client):
        """Test service initialization without provided Supabase client."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        service = PlatformMonitoringService()
        
        assert service.supabase_client == mock_client
        mock_create_client.assert_called_once_with('https://test.supabase.co', 'test-key')
    
    def test_initialization_missing_environment_variables(self):
        """Test service initialization with missing environment variables."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required"):
                PlatformMonitoringService()
    
    @pytest.mark.asyncio
    async def test_get_platform_distribution_success(self, monitoring_service, mock_supabase_client):
        """Test successful platform distribution retrieval."""
        # Mock the response
        mock_data = [
            {
                "platform": "shopify",
                "roaster_count": 15,
                "percentage": 60.0,
                "active_roasters": 12,
                "inactive_roasters": 3,
                "firecrawl_enabled": 8,
                "avg_firecrawl_budget": 10.5
            },
            {
                "platform": "woocommerce",
                "roaster_count": 8,
                "percentage": 32.0,
                "active_roasters": 7,
                "inactive_roasters": 1,
                "firecrawl_enabled": 5,
                "avg_firecrawl_budget": 8.0
            },
            {
                "platform": "other",
                "roaster_count": 2,
                "percentage": 8.0,
                "active_roasters": 1,
                "inactive_roasters": 1,
                "firecrawl_enabled": 2,
                "avg_firecrawl_budget": 15.0
            }
        ]
        
        mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        
        result = await monitoring_service.get_platform_distribution()
        
        assert len(result) == 3
        assert result[0]["platform"] == "shopify"
        assert result[0]["roaster_count"] == 15
        assert result[0]["percentage"] == 60.0
        assert result[1]["platform"] == "woocommerce"
        assert result[2]["platform"] == "other"
    
    @pytest.mark.asyncio
    async def test_get_platform_distribution_failure(self, monitoring_service, mock_supabase_client):
        """Test platform distribution retrieval failure."""
        # Mock the response to raise an exception
        mock_supabase_client.table.return_value.select.return_value.execute.side_effect = Exception("Database error")
        
        result = await monitoring_service.get_platform_distribution()
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_platform_usage_stats_success(self, monitoring_service, mock_supabase_client):
        """Test successful platform usage stats retrieval."""
        # Mock the response
        mock_data = [
            {
                "platform": "shopify",
                "total_roasters": 15,
                "total_coffees": 150,
                "total_variants": 300,
                "total_prices": 1500,
                "avg_coffee_rating": 4.2,
                "active_coffees": 140,
                "inactive_coffees": 10,
                "in_stock_variants": 280,
                "out_of_stock_variants": 20,
                "avg_price": 16.99
            },
            {
                "platform": "woocommerce",
                "total_roasters": 8,
                "total_coffees": 80,
                "total_variants": 160,
                "total_prices": 800,
                "avg_coffee_rating": 4.0,
                "active_coffees": 75,
                "inactive_coffees": 5,
                "in_stock_variants": 150,
                "out_of_stock_variants": 10,
                "avg_price": 14.99
            }
        ]
        
        mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        
        result = await monitoring_service.get_platform_usage_stats()
        
        assert len(result) == 2
        assert result[0]["platform"] == "shopify"
        assert result[0]["total_roasters"] == 15
        assert result[0]["total_coffees"] == 150
        assert result[0]["avg_coffee_rating"] == 4.2
        assert result[1]["platform"] == "woocommerce"
        assert result[1]["total_roasters"] == 8
    
    @pytest.mark.asyncio
    async def test_get_firecrawl_usage_tracking_success(self, monitoring_service, mock_supabase_client):
        """Test successful Firecrawl usage tracking retrieval."""
        # Mock the response
        mock_data = [
            {
                "platform": "shopify",
                "total_roasters": 15,
                "firecrawl_enabled_count": 8,
                "firecrawl_enabled_percentage": 53.33,
                "avg_budget_limit": 10.5,
                "min_budget_limit": 5.0,
                "max_budget_limit": 20.0,
                "total_budget_allocated": 157.5,
                "active_firecrawl_roasters": 7
            },
            {
                "platform": "woocommerce",
                "total_roasters": 8,
                "firecrawl_enabled_count": 5,
                "firecrawl_enabled_percentage": 62.5,
                "avg_budget_limit": 8.0,
                "min_budget_limit": 5.0,
                "max_budget_limit": 15.0,
                "total_budget_allocated": 64.0,
                "active_firecrawl_roasters": 4
            }
        ]
        
        mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        
        result = await monitoring_service.get_firecrawl_usage_tracking()
        
        assert len(result) == 2
        assert result[0]["platform"] == "shopify"
        assert result[0]["firecrawl_enabled_count"] == 8
        assert result[0]["firecrawl_enabled_percentage"] == 53.33
        assert result[1]["platform"] == "woocommerce"
        assert result[1]["firecrawl_enabled_count"] == 5
    
    @pytest.mark.asyncio
    async def test_get_platform_performance_metrics_success(self, monitoring_service, mock_supabase_client):
        """Test successful platform performance metrics retrieval."""
        # Mock the response
        mock_data = [
            {
                "platform": "shopify",
                "roaster_count": 15,
                "coffee_count": 150,
                "avg_coffees_per_roaster": 10.0,
                "variant_count": 300,
                "avg_variants_per_coffee": 2.0,
                "price_count": 1500,
                "avg_prices_per_variant": 5.0,
                "avg_rating": 4.2,
                "rated_coffees": 120,
                "rating_coverage_percentage": 80.0
            },
            {
                "platform": "woocommerce",
                "roaster_count": 8,
                "coffee_count": 80,
                "avg_coffees_per_roaster": 10.0,
                "variant_count": 160,
                "avg_variants_per_coffee": 2.0,
                "price_count": 800,
                "avg_prices_per_variant": 5.0,
                "avg_rating": 4.0,
                "rated_coffees": 60,
                "rating_coverage_percentage": 75.0
            }
        ]
        
        mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        
        result = await monitoring_service.get_platform_performance_metrics()
        
        assert len(result) == 2
        assert result[0]["platform"] == "shopify"
        assert result[0]["avg_coffees_per_roaster"] == 10.0
        assert result[0]["rating_coverage_percentage"] == 80.0
        assert result[1]["platform"] == "woocommerce"
        assert result[1]["avg_coffees_per_roaster"] == 10.0
    
    @pytest.mark.asyncio
    async def test_get_recent_platform_activity_success(self, monitoring_service, mock_supabase_client):
        """Test successful recent platform activity retrieval."""
        # Mock the response
        mock_data = [
            {
                "platform": "shopify",
                "total_roasters": 15,
                "updated_last_7_days": 5,
                "updated_last_30_days": 12,
                "created_last_7_days": 1,
                "created_last_30_days": 3,
                "currently_active": 12,
                "currently_inactive": 3
            },
            {
                "platform": "woocommerce",
                "total_roasters": 8,
                "updated_last_7_days": 3,
                "updated_last_30_days": 6,
                "created_last_7_days": 0,
                "created_last_30_days": 1,
                "currently_active": 7,
                "currently_inactive": 1
            }
        ]
        
        mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        
        result = await monitoring_service.get_recent_platform_activity()
        
        assert len(result) == 2
        assert result[0]["platform"] == "shopify"
        assert result[0]["updated_last_7_days"] == 5
        assert result[0]["currently_active"] == 12
        assert result[1]["platform"] == "woocommerce"
        assert result[1]["updated_last_7_days"] == 3
    
    @pytest.mark.asyncio
    async def test_get_platform_health_dashboard_success(self, monitoring_service, mock_supabase_client):
        """Test successful platform health dashboard retrieval."""
        # Mock the response
        mock_data = [
            {
                "platform": "shopify",
                "total_roasters": 15,
                "active_roasters": 12,
                "inactive_roasters": 3,
                "active_percentage": 80.0,
                "firecrawl_enabled": 8,
                "firecrawl_percentage": 53.33,
                "avg_budget_limit": 10.5,
                "total_coffees": 150,
                "active_coffees": 140,
                "avg_rating": 4.2,
                "rated_coffees": 120,
                "activity_status": "Recent"
            },
            {
                "platform": "woocommerce",
                "total_roasters": 8,
                "active_roasters": 7,
                "inactive_roasters": 1,
                "active_percentage": 87.5,
                "firecrawl_enabled": 5,
                "firecrawl_percentage": 62.5,
                "avg_budget_limit": 8.0,
                "total_coffees": 80,
                "active_coffees": 75,
                "avg_rating": 4.0,
                "rated_coffees": 60,
                "activity_status": "Recent"
            }
        ]
        
        mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        
        result = await monitoring_service.get_platform_health_dashboard()
        
        assert len(result) == 2
        assert result[0]["platform"] == "shopify"
        assert result[0]["active_percentage"] == 80.0
        assert result[0]["activity_status"] == "Recent"
        assert result[1]["platform"] == "woocommerce"
        assert result[1]["active_percentage"] == 87.5
    
    @pytest.mark.asyncio
    async def test_get_platform_summary_report_success(self, monitoring_service, mock_supabase_client):
        """Test successful platform summary report generation."""
        # Mock all the individual methods
        with patch.object(monitoring_service, 'get_platform_distribution') as mock_dist, \
             patch.object(monitoring_service, 'get_platform_usage_stats') as mock_usage, \
             patch.object(monitoring_service, 'get_firecrawl_usage_tracking') as mock_firecrawl, \
             patch.object(monitoring_service, 'get_platform_performance_metrics') as mock_perf, \
             patch.object(monitoring_service, 'get_recent_platform_activity') as mock_activity, \
             patch.object(monitoring_service, 'get_platform_health_dashboard') as mock_health:
            
            # Mock the responses
            mock_dist.return_value = [{"platform": "shopify", "roaster_count": 15}]
            mock_usage.return_value = [{"platform": "shopify", "total_coffees": 150}]
            mock_firecrawl.return_value = [{"platform": "shopify", "firecrawl_enabled_count": 8}]
            mock_perf.return_value = [{"platform": "shopify", "avg_rating": 4.2}]
            mock_activity.return_value = [{"platform": "shopify", "updated_last_7_days": 5}]
            mock_health.return_value = [{"platform": "shopify", "activity_status": "Recent"}]
            
            result = await monitoring_service.get_platform_summary_report()
            
            assert "generated_at" in result
            assert "total_roasters" in result
            assert "total_coffees" in result
            assert "total_firecrawl_enabled" in result
            assert "firecrawl_percentage" in result
            assert "platform_distribution" in result
            assert "platform_usage_stats" in result
            assert "firecrawl_usage_tracking" in result
            assert "platform_performance_metrics" in result
            assert "recent_platform_activity" in result
            assert "platform_health_dashboard" in result
    
    @pytest.mark.asyncio
    async def test_get_platform_alerts_success(self, monitoring_service, mock_supabase_client):
        """Test successful platform alerts generation."""
        # Mock the health dashboard data
        mock_health_data = [
            {
                "platform": "shopify",
                "active_percentage": 45.0,  # Low activity
                "activity_status": "Recent",
                "avg_rating": 4.2
            },
            {
                "platform": "woocommerce",
                "active_percentage": 80.0,
                "activity_status": "Stale",  # Stale activity
                "avg_rating": 2.5  # Low rating
            },
            {
                "platform": "other",
                "active_percentage": 90.0,
                "activity_status": "Recent",
                "avg_rating": 4.5
            }
        ]
        
        with patch.object(monitoring_service, 'get_platform_health_dashboard', return_value=mock_health_data):
            result = await monitoring_service.get_platform_alerts()
            
            assert len(result) == 3  # Three alerts generated
            
            # Check low activity alert
            low_activity_alert = next(alert for alert in result if alert["alert_type"] == "low_activity")
            assert low_activity_alert["platform"] == "shopify"
            assert low_activity_alert["severity"] == "warning"
            assert low_activity_alert["value"] == 45.0
            
            # Check stale activity alert
            stale_activity_alert = next(alert for alert in result if alert["alert_type"] == "stale_activity")
            assert stale_activity_alert["platform"] == "woocommerce"
            assert stale_activity_alert["severity"] == "critical"
            assert stale_activity_alert["value"] == "Stale"
            
            # Check low rating alert
            low_rating_alert = next(alert for alert in result if alert["alert_type"] == "low_rating")
            assert low_rating_alert["platform"] == "woocommerce"
            assert low_rating_alert["severity"] == "warning"
            assert low_rating_alert["value"] == 2.5
    
    @pytest.mark.asyncio
    async def test_get_platform_alerts_no_alerts(self, monitoring_service, mock_supabase_client):
        """Test platform alerts when no alerts are needed."""
        # Mock the health dashboard data with healthy metrics
        mock_health_data = [
            {
                "platform": "shopify",
                "active_percentage": 85.0,  # High activity
                "activity_status": "Recent",
                "avg_rating": 4.5  # High rating
            },
            {
                "platform": "woocommerce",
                "active_percentage": 90.0,  # High activity
                "activity_status": "Recent",
                "avg_rating": 4.2  # High rating
            }
        ]
        
        with patch.object(monitoring_service, 'get_platform_health_dashboard', return_value=mock_health_data):
            result = await monitoring_service.get_platform_alerts()
            
            assert len(result) == 0  # No alerts generated
    
    @pytest.mark.asyncio
    async def test_close_service(self, monitoring_service):
        """Test service cleanup."""
        # The service doesn't need explicit cleanup, but we can test the method
        await monitoring_service.close()
        # Should not raise any exceptions
