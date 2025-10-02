"""
Monitoring and metrics tests for Firecrawl operations.

Tests:
- Metrics collection
- Alert management
- Health status monitoring
- Performance metrics
- Budget tracking
- Error monitoring
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta

from src.monitoring.firecrawl_metrics import FirecrawlMetrics, FirecrawlAlertManager
from src.fetcher.firecrawl_client import FirecrawlClient
from src.fetcher.firecrawl_map_service import FirecrawlMapService
from src.config.firecrawl_config import FirecrawlConfig


class TestFirecrawlMonitoring:
    """Test Firecrawl monitoring functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock Firecrawl configuration."""
        return FirecrawlConfig(
            api_key="test_api_key_1234567890",
            base_url="https://api.firecrawl.dev",
            budget_limit=1000,
            max_pages=50,
            include_subdomains=False,
            sitemap_only=False,
            coffee_keywords=['coffee', 'bean', 'roast'],
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
            enable_monitoring=True,
            log_level="INFO"
        )
    
    @pytest.fixture
    def firecrawl_metrics(self):
        """Create a FirecrawlMetrics instance."""
        return FirecrawlMetrics()
    
    @pytest.fixture
    def firecrawl_alert_manager(self, firecrawl_metrics):
        """Create a FirecrawlAlertManager instance."""
        return FirecrawlAlertManager(firecrawl_metrics)
    
    def test_metrics_initialization(self, firecrawl_metrics):
        """Test metrics initialization."""
        metrics = firecrawl_metrics.export_metrics()
        
        # Verify initial metrics
        assert metrics['total_requests'] == 0
        assert metrics['successful_map_operations'] == 0
        assert metrics['failed_map_operations'] == 0
        assert metrics['total_urls_discovered'] == 0
        assert metrics['total_budget_used'] == 0
        assert metrics['average_map_time_seconds'] == 0.0
        assert metrics['last_map_operation_time'] is None
        assert len(metrics['error_types']) == 0
        assert len(metrics['roaster_map_counts']) == 0
        assert len(metrics['roaster_map_failures']) == 0
        assert 'last_reset_time' in metrics
    
    def test_record_successful_operation(self, firecrawl_metrics):
        """Test recording successful operation."""
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=50,
            operation_time=2.5
        )
        
        metrics = firecrawl_metrics.export_metrics()
        
        # Verify metrics
        assert metrics['total_requests'] == 1
        assert metrics['successful_map_operations'] == 1
        assert metrics['failed_map_operations'] == 0
        assert metrics['total_urls_discovered'] == 5
        assert metrics['total_budget_used'] == 50
        assert metrics['average_map_time_seconds'] == 2.5
        assert metrics['roaster_map_counts']['roaster_1'] == 1
        assert metrics['roaster_map_failures']['roaster_1'] == 0
    
    def test_record_failed_operation(self, firecrawl_metrics):
        """Test recording failed operation."""
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=False,
            urls_discovered=0,
            budget_used=10,
            operation_time=1.0,
            error_type="API_ERROR"
        )
        
        metrics = firecrawl_metrics.export_metrics()
        
        # Verify metrics
        assert metrics['total_requests'] == 1
        assert metrics['successful_map_operations'] == 0
        assert metrics['failed_map_operations'] == 1
        assert metrics['total_urls_discovered'] == 0
        assert metrics['total_budget_used'] == 10
        assert metrics['error_types']['API_ERROR'] == 1
        assert metrics['roaster_map_counts']['roaster_1'] == 1
        assert metrics['roaster_map_failures']['roaster_1'] == 1
    
    def test_record_multiple_operations(self, firecrawl_metrics):
        """Test recording multiple operations."""
        # Record multiple operations
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=50,
            operation_time=2.5
        )
        
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_2",
            operation_type="map",
            success=True,
            urls_discovered=3,
            budget_used=30,
            operation_time=1.8
        )
        
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=False,
            urls_discovered=0,
            budget_used=10,
            operation_time=0.5,
            error_type="TIMEOUT_ERROR"
        )
        
        metrics = firecrawl_metrics.export_metrics()
        
        # Verify metrics
        assert metrics['total_requests'] == 3
        assert metrics['successful_map_operations'] == 2
        assert metrics['failed_map_operations'] == 1
        assert metrics['total_urls_discovered'] == 8
        assert metrics['total_budget_used'] == 90
        assert metrics['average_map_time_seconds'] == 2.15  # (2.5 + 1.8) / 2
        assert metrics['roaster_map_counts']['roaster_1'] == 2
        assert metrics['roaster_map_counts']['roaster_2'] == 1
        assert metrics['roaster_map_failures']['roaster_1'] == 1
        assert metrics['roaster_map_failures']['roaster_2'] == 0
        assert metrics['error_types']['TIMEOUT_ERROR'] == 1
    
    def test_reset_metrics(self, firecrawl_metrics):
        """Test metrics reset."""
        # Record some operations
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=50,
            operation_time=2.5
        )
        
        # Reset metrics
        firecrawl_metrics.reset_metrics()
        
        metrics = firecrawl_metrics.export_metrics()
        
        # Verify metrics are reset
        assert metrics['total_requests'] == 0
        assert metrics['successful_map_operations'] == 0
        assert metrics['failed_map_operations'] == 0
        assert metrics['total_urls_discovered'] == 0
        assert metrics['total_budget_used'] == 0
        assert metrics['average_map_time_seconds'] == 0.0
        assert metrics['last_map_operation_time'] is None
        assert len(metrics['error_types']) == 0
        assert len(metrics['roaster_map_counts']) == 0
        assert len(metrics['roaster_map_failures']) == 0
    
    def test_health_status_healthy(self, firecrawl_metrics):
        """Test healthy status."""
        # Record successful operations
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=50,
            operation_time=2.5
        )
        
        health_status = firecrawl_metrics.get_health_status()
        
        # Verify healthy status
        assert health_status['service'] == 'Firecrawl'
        assert health_status['status'] == 'healthy'
        assert 'All Firecrawl services operating normally.' in health_status['message']
        assert 'timestamp' in health_status
        assert 'metrics_summary' in health_status
    
    def test_health_status_degraded(self, firecrawl_metrics):
        """Test degraded status."""
        # Record operations with high failure rate
        for i in range(25):  # 25 operations
            firecrawl_metrics.record_map_operation(
                roaster_id=f"roaster_{i}",
                operation_type="map",
                success=False,
                urls_discovered=0,
                budget_used=10,
                operation_time=1.0,
                error_type="API_ERROR"
            )
        
        health_status = firecrawl_metrics.get_health_status()
        
        # Verify degraded status
        assert health_status['service'] == 'Firecrawl'
        assert health_status['status'] == 'degraded'
        assert 'High rate of failed map operations.' in health_status['message']
    
    def test_health_status_warning(self, firecrawl_metrics):
        """Test warning status."""
        # Record operations with high budget usage
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=900,  # High budget usage
            operation_time=2.5
        )
        
        # Set budget limit in metrics
        firecrawl_metrics.metrics['budget_limit'] = 1000
        
        health_status = firecrawl_metrics.get_health_status()
        
        # Verify warning status
        assert health_status['service'] == 'Firecrawl'
        assert health_status['status'] == 'warning'
        assert 'Approaching Firecrawl budget limit.' in health_status['message']
    
    def test_alert_manager_initialization(self, firecrawl_alert_manager):
        """Test alert manager initialization."""
        assert firecrawl_alert_manager.metrics_service is not None
        assert firecrawl_alert_manager.active_alerts == []
        assert 'high_failure_rate' in firecrawl_alert_manager.alert_thresholds
        assert 'budget_near_exhaustion' in firecrawl_alert_manager.alert_thresholds
        assert 'no_urls_discovered' in firecrawl_alert_manager.alert_thresholds
    
    def test_check_alerts_no_alerts(self, firecrawl_alert_manager):
        """Test checking alerts with no alerts."""
        # Record successful operations
        firecrawl_alert_manager.metrics_service.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=50,
            operation_time=2.5
        )
        
        alerts = firecrawl_alert_manager.check_alerts()
        
        # Verify no alerts
        assert len(alerts) == 0
        assert len(firecrawl_alert_manager.active_alerts) == 0
    
    def test_check_alerts_high_failure_rate(self, firecrawl_alert_manager):
        """Test checking alerts with high failure rate."""
        # Record operations with high failure rate
        for i in range(25):  # 25 operations
            firecrawl_alert_manager.metrics_service.record_map_operation(
                roaster_id=f"roaster_{i}",
                operation_type="map",
                success=False,
                urls_discovered=0,
                budget_used=10,
                operation_time=1.0,
                error_type="API_ERROR"
            )
        
        alerts = firecrawl_alert_manager.check_alerts()
        
        # Verify high failure rate alert
        assert len(alerts) > 0
        assert any(alert['type'] == 'high_failure_rate' for alert in alerts)
        assert any(alert['severity'] == 'critical' for alert in alerts)
    
    def test_check_alerts_budget_near_exhaustion(self, firecrawl_alert_manager):
        """Test checking alerts with budget near exhaustion."""
        # Record operations with high budget usage
        firecrawl_alert_manager.metrics_service.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=900,  # High budget usage
            operation_time=2.5
        )
        
        # Set budget limit in metrics
        firecrawl_alert_manager.metrics_service.metrics['budget_limit'] = 1000
        
        alerts = firecrawl_alert_manager.check_alerts()
        
        # Verify budget near exhaustion alert
        assert len(alerts) > 0
        assert any(alert['type'] == 'budget_near_exhaustion' for alert in alerts)
        assert any(alert['severity'] == 'warning' for alert in alerts)
    
    def test_check_alerts_no_urls_discovered(self, firecrawl_alert_manager):
        """Test checking alerts with no URLs discovered."""
        # Record operations with no URLs discovered
        for i in range(10):  # 10 operations
            firecrawl_alert_manager.metrics_service.record_map_operation(
                roaster_id=f"roaster_{i}",
                operation_type="map",
                success=True,
                urls_discovered=0,  # No URLs discovered
                budget_used=10,
                operation_time=1.0
            )
        
        # Set last operation time to more than 60 minutes ago
        firecrawl_alert_manager.metrics_service.metrics['last_map_operation_time'] = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        
        alerts = firecrawl_alert_manager.check_alerts()
        
        # Verify no URLs discovered alert
        assert len(alerts) > 0
        assert any(alert['type'] == 'no_urls_discovered' for alert in alerts)
        assert any(alert['severity'] == 'warning' for alert in alerts)
    
    def test_get_active_alerts(self, firecrawl_alert_manager):
        """Test getting active alerts."""
        # Record operations with high failure rate
        for i in range(25):  # 25 operations
            firecrawl_alert_manager.metrics_service.record_map_operation(
                roaster_id=f"roaster_{i}",
                operation_type="map",
                success=False,
                urls_discovered=0,
                budget_used=10,
                operation_time=1.0,
                error_type="API_ERROR"
            )
        
        # Check alerts
        firecrawl_alert_manager.check_alerts()
        
        # Get active alerts
        active_alerts = firecrawl_alert_manager.get_active_alerts()
        
        # Verify active alerts
        assert len(active_alerts) > 0
        assert any(alert['type'] == 'high_failure_rate' for alert in active_alerts)
    
    def test_clear_alerts(self, firecrawl_alert_manager):
        """Test clearing alerts."""
        # Record operations with high failure rate
        for i in range(25):  # 25 operations
            firecrawl_alert_manager.metrics_service.record_map_operation(
                roaster_id=f"roaster_{i}",
                operation_type="map",
                success=False,
                urls_discovered=0,
                budget_used=10,
                operation_time=1.0,
                error_type="API_ERROR"
            )
        
        # Check alerts
        firecrawl_alert_manager.check_alerts()
        
        # Clear alerts
        firecrawl_alert_manager.clear_alerts()
        
        # Verify alerts are cleared
        assert len(firecrawl_alert_manager.active_alerts) == 0
    
    def test_alert_thresholds_configuration(self, firecrawl_alert_manager):
        """Test alert thresholds configuration."""
        thresholds = firecrawl_alert_manager.alert_thresholds
        
        # Verify threshold configuration
        assert 'high_failure_rate' in thresholds
        assert 'budget_near_exhaustion' in thresholds
        assert 'no_urls_discovered' in thresholds
        
        # Verify threshold values
        assert thresholds['high_failure_rate']['threshold'] == 0.2
        assert thresholds['high_failure_rate']['min_requests'] == 20
        assert thresholds['budget_near_exhaustion']['threshold'] == 0.9
        assert thresholds['no_urls_discovered']['time_window_minutes'] == 60
        assert thresholds['no_urls_discovered']['min_requests'] == 5
    
    def test_metrics_export_format(self, firecrawl_metrics):
        """Test metrics export format."""
        # Record some operations
        firecrawl_metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=50,
            operation_time=2.5
        )
        
        metrics = firecrawl_metrics.export_metrics()
        
        # Verify metrics format
        assert isinstance(metrics, dict)
        assert 'total_requests' in metrics
        assert 'successful_map_operations' in metrics
        assert 'failed_map_operations' in metrics
        assert 'total_urls_discovered' in metrics
        assert 'total_budget_used' in metrics
        assert 'average_map_time_seconds' in metrics
        assert 'last_map_operation_time' in metrics
        assert 'error_types' in metrics
        assert 'roaster_map_counts' in metrics
        assert 'roaster_map_failures' in metrics
        assert 'last_reset_time' in metrics
    
    def test_health_status_format(self, firecrawl_metrics):
        """Test health status format."""
        health_status = firecrawl_metrics.get_health_status()
        
        # Verify health status format
        assert isinstance(health_status, dict)
        assert 'service' in health_status
        assert 'status' in health_status
        assert 'message' in health_status
        assert 'timestamp' in health_status
        assert 'metrics_summary' in health_status
        
        # Verify service name
        assert health_status['service'] == 'Firecrawl'
        
        # Verify status values
        assert health_status['status'] in ['healthy', 'degraded', 'warning']
    
    def test_alert_format(self, firecrawl_alert_manager):
        """Test alert format."""
        # Record operations with high failure rate
        for i in range(25):  # 25 operations
            firecrawl_alert_manager.metrics_service.record_map_operation(
                roaster_id=f"roaster_{i}",
                operation_type="map",
                success=False,
                urls_discovered=0,
                budget_used=10,
                operation_time=1.0,
                error_type="API_ERROR"
            )
        
        alerts = firecrawl_alert_manager.check_alerts()
        
        # Verify alert format
        assert len(alerts) > 0
        for alert in alerts:
            assert isinstance(alert, dict)
            assert 'type' in alert
            assert 'severity' in alert
            assert 'message' in alert
            assert 'timestamp' in alert
            
            # Verify alert types
            assert alert['type'] in ['high_failure_rate', 'budget_near_exhaustion', 'no_urls_discovered', 'health_status_degraded']
            
            # Verify severity levels
            assert alert['severity'] in ['critical', 'warning', 'info']
