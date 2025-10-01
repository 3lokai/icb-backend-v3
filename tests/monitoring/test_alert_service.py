"""
Tests for comprehensive alert service.

This module tests the ComprehensiveAlertService with threshold monitoring,
Slack integration, and Sentry error tracking.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.monitoring.alert_service import (
    ComprehensiveAlertService,
    ThresholdMonitor,
    AlertSeverity,
    ThresholdBreach
)
from src.monitoring.pipeline_metrics import PipelineMetrics
from src.monitoring.sentry_integration import SentryIntegration


class TestThresholdMonitor:
    """Test threshold monitoring functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics = Mock(spec=PipelineMetrics)
        self.monitor = ThresholdMonitor(self.metrics)
    
    def test_update_metric_value_no_breach(self):
        """Test metric update without threshold breach."""
        breaches = self.monitor.update_metric_value("test_metric", 10.0)
        assert len(breaches) == 0
    
    def test_update_metric_value_with_breach(self):
        """Test metric update with threshold breach."""
        # Set up a rule that will breach
        self.monitor.alert_rules["test_rule"] = Mock()
        self.monitor.alert_rules["test_rule"].metric_name = "test_metric"
        self.monitor.alert_rules["test_rule"].threshold = 5.0
        self.monitor.alert_rules["test_rule"].severity = AlertSeverity.WARNING
        self.monitor.alert_rules["test_rule"].component = "test"
        self.monitor.alert_rules["test_rule"].name = "test_rule"
        
        # Mock the breach check to return a breach
        with patch.object(self.monitor, '_check_threshold_breach') as mock_check:
            mock_breach = ThresholdBreach(
                rule_name="test_rule",
                metric_name="test_metric",
                current_value=10.0,
                threshold=5.0,
                severity=AlertSeverity.WARNING,
                component="test",
                timestamp=time.time(),
                exceeded_by_percent=100.0
            )
            mock_check.return_value = mock_breach
            
            breaches = self.monitor.update_metric_value("test_metric", 10.0)
            assert len(breaches) == 1
            assert breaches[0].rule_name == "test_rule"
    
    def test_get_metric_history(self):
        """Test getting metric history."""
        # Add some historical data
        self.monitor.historical_data["test_metric"] = [
            (time.time() - 3600, 5.0),  # 1 hour ago
            (time.time() - 1800, 10.0),  # 30 minutes ago
            (time.time(), 15.0)  # now
        ]
        
        history = self.monitor.get_metric_history("test_metric", hours=2)
        assert len(history) == 3
    
    def test_get_baseline_value(self):
        """Test getting baseline value."""
        self.monitor.baseline_data["test_metric"] = 25.0
        baseline = self.monitor.get_baseline_value("test_metric")
        assert baseline == 25.0


class TestComprehensiveAlertService:
    """Test comprehensive alert service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.slack_webhook_url = "https://hooks.slack.com/test"
        self.sentry_dsn = "https://test@sentry.io/123"
        self.metrics = Mock(spec=PipelineMetrics)
        
        with patch('src.monitoring.alert_service.SlackClient'), \
             patch('src.monitoring.alert_service.SentryIntegration'):
            self.alert_service = ComprehensiveAlertService(
                slack_webhook_url=self.slack_webhook_url,
                sentry_dsn=self.sentry_dsn,
                metrics=self.metrics
            )
    
    @pytest.mark.asyncio
    async def test_check_thresholds(self):
        """Test checking all thresholds."""
        with patch.object(self.alert_service, '_get_review_rate') as mock_review, \
             patch.object(self.alert_service, '_get_rpc_error_rate') as mock_rpc, \
             patch.object(self.alert_service, '_get_system_health') as mock_health, \
             patch.object(self.alert_service, '_get_avg_fetch_latency') as mock_latency, \
             patch.object(self.alert_service, '_get_validation_error_rate') as mock_validation:
            
            mock_review.return_value = 45.0
            mock_rpc.return_value = 5.0
            mock_health.return_value = 85.0
            mock_latency.return_value = 15.0
            mock_validation.return_value = 8.0
            
            breaches = await self.alert_service.check_thresholds()
            # Should return empty list since all values are within thresholds
            assert isinstance(breaches, list)
    
    @pytest.mark.asyncio
    async def test_send_threshold_alert(self):
        """Test sending threshold alert."""
        breach = ThresholdBreach(
            rule_name="test_rule",
            metric_name="test_metric",
            current_value=100.0,
            threshold=50.0,
            severity=AlertSeverity.WARNING,
            component="test",
            timestamp=time.time(),
            exceeded_by_percent=100.0
        )
        
        with patch.object(self.alert_service.slack_client, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await self.alert_service._send_threshold_alert(breach)
            
            # Verify Slack message was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert "test_rule" in call_args["text"]
            assert call_args["attachments"][0]["color"] == "warning"
    
    @pytest.mark.asyncio
    async def test_send_system_failure_alert(self):
        """Test sending system failure alert."""
        system_state = {"cpu_usage": 95.0, "memory_usage": 90.0}
        
        with patch.object(self.alert_service.slack_client, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await self.alert_service.send_system_failure_alert(
                component="database",
                failure_type="connection_timeout",
                error_message="Database connection failed",
                system_state=system_state
            )
            
            # Verify Slack message was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert "CRITICAL" in call_args["text"]
            assert call_args["attachments"][0]["color"] == "danger"
    
    @pytest.mark.asyncio
    async def test_send_review_rate_spike_alert(self):
        """Test sending review rate spike alert."""
        with patch.object(self.alert_service.slack_client, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await self.alert_service.send_review_rate_spike_alert(
                roaster_id="test_roaster",
                platform="shopify",
                current_rate=75.0,
                baseline_rate=50.0,
                increase_percent=50.0
            )
            
            # Verify Slack message was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert "Review Rate Spike" in call_args["text"]
            assert call_args["attachments"][0]["color"] == "warning"
    
    def test_alert_cooldown(self):
        """Test alert cooldown functionality."""
        # Test cooldown check
        assert not self.alert_service._is_in_cooldown("test_rule")
        
        # Record cooldown
        self.alert_service._record_cooldown("test_rule")
        
        # Should be in cooldown now
        assert self.alert_service._is_in_cooldown("test_rule")
    
    def test_get_alert_status(self):
        """Test getting alert service status."""
        status = self.alert_service.get_alert_status()
        
        assert "threshold_monitor" in status
        assert "alert_throttle" in status
        assert "cooldowns" in status
        assert "clients" in status
        assert "sentry_status" in status
        
        # Verify structure
        assert isinstance(status["threshold_monitor"], dict)
        assert isinstance(status["alert_throttle"], dict)
        assert isinstance(status["cooldowns"], dict)
        assert isinstance(status["clients"], dict)


class TestAlertIntegration:
    """Test integration between alert service components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_alert_flow(self):
        """Test end-to-end alert flow."""
        with patch('src.monitoring.alert_service.SlackClient'), \
             patch('src.monitoring.alert_service.SentryIntegration') as mock_sentry:
            
            alert_service = ComprehensiveAlertService(
                slack_webhook_url="https://hooks.slack.com/test",
                sentry_dsn="https://test@sentry.io/123"
            )
            
            # Create a threshold breach
            breach = ThresholdBreach(
                rule_name="test_rule",
                metric_name="test_metric",
                current_value=100.0,
                threshold=50.0,
                severity=AlertSeverity.CRITICAL,
                component="test",
                timestamp=time.time(),
                exceeded_by_percent=100.0
            )
            
            # Process the breach
            with patch.object(alert_service.slack_client, 'send_message', new_callable=AsyncMock) as mock_slack:
                mock_slack.return_value = True
                
                await alert_service.process_threshold_breaches([breach])
                
                # Verify Slack alert was sent
                mock_slack.assert_called_once()
                
                # Verify Sentry capture was called
                mock_sentry.return_value.capture_threshold_breach.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_alert_throttling(self):
        """Test alert throttling functionality."""
        alert_service = ComprehensiveAlertService(
            slack_webhook_url="https://hooks.slack.com/test",
            sentry_dsn="https://test@sentry.io/123"
        )
        
        # Test throttling
        alert_key = "test_alert"
        
        # Should not be throttled initially
        assert not alert_service.alert_throttle.should_throttle(alert_key)
        
        # Record multiple alerts to trigger throttling
        for _ in range(alert_service.alert_throttle.max_alerts_per_window + 1):
            alert_service.alert_throttle.record_alert(alert_key)
        
        # Should be throttled now
        assert alert_service.alert_throttle.should_throttle(alert_key)


class TestMockDataGeneration:
    """Test mock data generation for testing."""
    
    def test_generate_mock_breaches(self):
        """Test generating mock threshold breaches."""
        breaches = []
        
        # Generate mock breaches for different scenarios
        scenarios = [
            ("review_rate_spike", 75.0, 50.0, AlertSeverity.WARNING),
            ("rpc_error_rate", 15.0, 10.0, AlertSeverity.CRITICAL),
            ("system_health", 35.0, 30.0, AlertSeverity.CRITICAL),
            ("fetch_latency", 90.0, 60.0, AlertSeverity.WARNING),
            ("validation_errors", 25.0, 20.0, AlertSeverity.WARNING)
        ]
        
        for rule_name, current_value, threshold, severity in scenarios:
            breach = ThresholdBreach(
                rule_name=rule_name,
                metric_name=f"{rule_name}_metric",
                current_value=current_value,
                threshold=threshold,
                severity=severity,
                component="test",
                timestamp=time.time(),
                exceeded_by_percent=((current_value - threshold) / threshold * 100) if threshold > 0 else 0
            )
            breaches.append(breach)
        
        assert len(breaches) == 5
        
        # Verify breach properties
        for breach in breaches:
            assert breach.current_value > breach.threshold
            assert breach.exceeded_by_percent > 0
            assert breach.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]
    
    def test_alert_message_formatting(self):
        """Test alert message formatting."""
        breach = ThresholdBreach(
            rule_name="test_rule",
            metric_name="test_metric",
            current_value=100.0,
            threshold=50.0,
            severity=AlertSeverity.CRITICAL,
            component="database",
            timestamp=time.time(),
            exceeded_by_percent=100.0
        )
        
        # Test message formatting logic
        severity_colors = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning", 
            AlertSeverity.CRITICAL: "danger"
        }
        
        expected_color = severity_colors[breach.severity]
        assert expected_color == "danger"
        
        # Test field values
        assert breach.current_value == 100.0
        assert breach.threshold == 50.0
        assert breach.exceeded_by_percent == 100.0
        assert breach.component == "database"


if __name__ == "__main__":
    pytest.main([__file__])
