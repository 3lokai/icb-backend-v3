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
        
        # Verify initial metrics structure
        assert 'timestamp' in metrics
        assert 'metrics' in metrics
        assert 'health' in metrics
        
        # Verify metrics content
        assert metrics['metrics']['overview']['total_operations'] == 0
        assert metrics['metrics']['overview']['successful_operations'] == 0
        assert metrics['metrics']['overview']['failed_operations'] == 0
        assert metrics['metrics']['discovery']['total_urls_discovered'] == 0
        assert metrics['metrics']['budget']['total_budget_used'] == 0
        assert metrics['metrics']['performance']['average_operation_time_seconds'] == 0.0
        assert metrics['metrics']['last_operation_time'] is None
        assert len(metrics['metrics']['errors']) == 0
        assert len(metrics['metrics']['roaster_breakdown']) == 0
    
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
        assert metrics['metrics']['overview']['total_operations'] == 1
        assert metrics['metrics']['overview']['successful_operations'] == 1
        assert metrics['metrics']['overview']['failed_operations'] == 0
        assert metrics['metrics']['discovery']['total_urls_discovered'] == 5
        assert metrics['metrics']['budget']['total_budget_used'] == 50
        assert metrics['metrics']['performance']['average_operation_time_seconds'] == 2.5
        assert metrics['metrics']['roaster_breakdown']['roaster_1']['total_operations'] == 1
        assert metrics['metrics']['roaster_breakdown']['roaster_1']['successful_operations'] == 1
    
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
        assert metrics['metrics']['overview']['total_operations'] == 1
        assert metrics['metrics']['overview']['successful_operations'] == 0
        assert metrics['metrics']['overview']['failed_operations'] == 1
        assert metrics['metrics']['discovery']['total_urls_discovered'] == 0
        assert metrics['metrics']['budget']['total_budget_used'] == 0  # Failed operations don't consume budget
        assert metrics['metrics']['errors']['API_ERROR'] == 1
        assert metrics['metrics']['roaster_breakdown']['roaster_1']['total_operations'] == 1
        assert metrics['metrics']['roaster_breakdown']['roaster_1']['failed_operations'] == 1
    
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
        assert metrics['metrics']['overview']['total_operations'] == 3
        assert metrics['metrics']['overview']['successful_operations'] == 2
        assert metrics['metrics']['overview']['failed_operations'] == 1
        assert metrics['metrics']['discovery']['total_urls_discovered'] == 8
        assert metrics['metrics']['budget']['total_budget_used'] == 80  # Only successful operations consume budget (50 + 30)
        assert metrics['metrics']['performance']['average_operation_time_seconds'] == 1.6  # (2.5 + 1.8 + 0.5) / 3
        assert metrics['metrics']['roaster_breakdown']['roaster_1']['total_operations'] == 2
        assert metrics['metrics']['roaster_breakdown']['roaster_2']['total_operations'] == 1
        assert metrics['metrics']['roaster_breakdown']['roaster_1']['failed_operations'] == 1
        assert metrics['metrics']['roaster_breakdown']['roaster_2']['failed_operations'] == 0
        assert metrics['metrics']['errors']['TIMEOUT_ERROR'] == 1
    
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
        assert metrics['metrics']['overview']['total_operations'] == 0
        assert metrics['metrics']['overview']['successful_operations'] == 0
        assert metrics['metrics']['overview']['failed_operations'] == 0
        assert metrics['metrics']['discovery']['total_urls_discovered'] == 0
        assert metrics['metrics']['budget']['total_budget_used'] == 0
        assert metrics['metrics']['performance']['average_operation_time_seconds'] == 0.0
        assert metrics['metrics']['last_operation_time'] is None
        assert len(metrics['metrics']['errors']) == 0
        assert len(metrics['metrics']['roaster_breakdown']) == 0
    
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
        assert health_status['status'] == 'healthy'
        assert 'Normal operation' in health_status['message']
        assert health_status['total_operations'] == 1
        assert health_status['failure_rate_percent'] == 0.0
        assert 'last_operation_time' in health_status
    
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
        
        # Verify unhealthy status (100% failure rate)
        assert health_status['status'] == 'unhealthy'
        assert 'High failure rate' in health_status['message']
        assert health_status['failure_rate_percent'] == 100.0
    
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
        
        # Verify healthy status (no failures, budget not checked in health status)
        assert health_status['status'] == 'healthy'
        assert 'Normal operation' in health_status['message']
    
    def test_alert_manager_initialization(self, firecrawl_alert_manager):
        """Test alert manager initialization."""
        assert firecrawl_alert_manager.metrics is not None
        assert firecrawl_alert_manager.active_alerts == []
        assert 'failure_rate_percent' in firecrawl_alert_manager.alert_thresholds
        assert 'budget_usage_percent' in firecrawl_alert_manager.alert_thresholds
        assert 'operation_time_seconds' in firecrawl_alert_manager.alert_thresholds
    
    def test_check_alerts_no_alerts(self, firecrawl_alert_manager):
        """Test checking alerts with no alerts."""
        # Record successful operations
        firecrawl_alert_manager.metrics.record_map_operation(
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
            firecrawl_alert_manager.metrics.record_map_operation(
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
        firecrawl_alert_manager.metrics.record_map_operation(
            roaster_id="roaster_1",
            operation_type="map",
            success=True,
            urls_discovered=5,
            budget_used=900,  # High budget usage
            operation_time=2.5
        )
        
        # Set budget limit in metrics
        firecrawl_alert_manager.metrics.metrics['budget_limit'] = 1000
        
        alerts = firecrawl_alert_manager.check_alerts()
        
        # Verify budget near exhaustion alert
        assert len(alerts) > 0
        assert any(alert['type'] == 'budget_near_exhaustion' for alert in alerts)
        assert any(alert['severity'] == 'warning' for alert in alerts)
    
    def test_check_alerts_no_urls_discovered(self, firecrawl_alert_manager):
        """Test checking alerts with no URLs discovered."""
        # Record operations with no URLs discovered
        for i in range(10):  # 10 operations
            firecrawl_alert_manager.metrics.record_map_operation(
                roaster_id=f"roaster_{i}",
                operation_type="map",
                success=True,
                urls_discovered=0,  # No URLs discovered
                budget_used=10,
                operation_time=1.0
            )
        
        # Set last operation time to more than 60 minutes ago
        firecrawl_alert_manager.metrics.metrics['last_map_operation_time'] = (
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
            firecrawl_alert_manager.metrics.record_map_operation(
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
            firecrawl_alert_manager.metrics.record_map_operation(
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
        assert 'failure_rate_percent' in thresholds
        assert 'budget_usage_percent' in thresholds
        assert 'operation_time_seconds' in thresholds
        
        # Verify threshold values
        assert thresholds['failure_rate_percent'] == 25.0
        assert thresholds['budget_usage_percent'] == 80.0
        assert thresholds['operation_time_seconds'] == 60.0
    
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
        assert 'timestamp' in metrics
        assert 'metrics' in metrics
        assert 'health' in metrics
        assert 'overview' in metrics['metrics']
        assert 'discovery' in metrics['metrics']
        assert 'budget' in metrics['metrics']
        assert 'performance' in metrics['metrics']
    
    def test_health_status_format(self, firecrawl_metrics):
        """Test health status format."""
        health_status = firecrawl_metrics.get_health_status()
        
        # Verify health status format
        assert isinstance(health_status, dict)
        assert 'status' in health_status
        assert 'message' in health_status
        assert 'last_operation_time' in health_status
        
        # Verify status values
        assert health_status['status'] in ['healthy', 'degraded', 'unhealthy', 'unknown']
    
    def test_alert_format(self, firecrawl_alert_manager):
        """Test alert format."""
        # Record operations with high failure rate
        for i in range(25):  # 25 operations
            firecrawl_alert_manager.metrics.record_map_operation(
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
            assert 'threshold' in alert
            assert 'current_value' in alert
            
            # Verify alert types
            assert alert['type'] in ['high_failure_rate', 'budget_near_exhaustion', 'no_urls_discovered']
            
            # Verify severity levels
            assert alert['severity'] in ['critical', 'warning', 'info']
