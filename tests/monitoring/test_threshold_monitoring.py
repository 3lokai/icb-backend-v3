"""
Tests for threshold monitoring service.

This module tests the ThresholdMonitoringService with comprehensive
threshold checking and alert processing.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.monitoring.threshold_monitoring import (
    ThresholdMonitoringService,
    MonitoringThreshold
)
from src.monitoring.alert_service import AlertSeverity, ThresholdBreach
from src.monitoring.pipeline_metrics import PipelineMetrics
from src.monitoring.database_metrics import DatabaseMetricsService


class TestMonitoringThreshold:
    """Test monitoring threshold configuration."""
    
    def test_threshold_creation(self):
        """Test creating monitoring threshold."""
        threshold = MonitoringThreshold(
            name="test_threshold",
            metric_name="test_metric",
            threshold_value=50.0,
            comparison_type="greater_than",
            severity=AlertSeverity.WARNING,
            component="test_component",
            description="Test threshold",
            cooldown_minutes=5
        )
        
        assert threshold.name == "test_threshold"
        assert threshold.metric_name == "test_metric"
        assert threshold.threshold_value == 50.0
        assert threshold.comparison_type == "greater_than"
        assert threshold.severity == AlertSeverity.WARNING
        assert threshold.component == "test_component"
        assert threshold.description == "Test threshold"
        assert threshold.cooldown_minutes == 5


class TestThresholdMonitoringService:
    """Test threshold monitoring service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline_metrics = Mock(spec=PipelineMetrics)
        self.database_metrics = Mock(spec=DatabaseMetricsService)
        self.alert_service = Mock()
        
        self.monitoring_service = ThresholdMonitoringService(
            pipeline_metrics=self.pipeline_metrics,
            database_metrics=self.database_metrics,
            alert_service=self.alert_service
        )
    
    @pytest.mark.asyncio
    async def test_check_all_thresholds(self):
        """Test checking all configured thresholds."""
        with patch.object(self.monitoring_service, '_get_current_review_rate') as mock_review, \
             patch.object(self.monitoring_service, '_get_current_rpc_error_rate') as mock_rpc, \
             patch.object(self.monitoring_service, '_get_current_system_health') as mock_health, \
             patch.object(self.monitoring_service, '_get_current_fetch_latency') as mock_latency, \
             patch.object(self.monitoring_service, '_get_current_validation_error_rate') as mock_validation, \
             patch.object(self.monitoring_service, '_get_current_database_failures') as mock_db, \
             patch.object(self.monitoring_service, '_get_current_memory_usage') as mock_memory, \
             patch.object(self.monitoring_service, '_get_current_disk_usage') as mock_disk:
            
            # Set up mock values that should not breach thresholds
            mock_review.return_value = 45.0
            mock_rpc.return_value = 5.0
            mock_health.return_value = 85.0
            mock_latency.return_value = 15.0
            mock_validation.return_value = 8.0
            mock_db.return_value = 2.0
            mock_memory.return_value = 65.0
            mock_disk.return_value = 45.0
            
            breaches = await self.monitoring_service.check_all_thresholds()
            
            # Should return empty list since all values are within thresholds
            assert isinstance(breaches, list)
            assert len(breaches) == 0
    
    @pytest.mark.asyncio
    async def test_check_review_rate_spike(self):
        """Test checking review rate spike threshold."""
        # Mock high review rate that should trigger breach
        with patch.object(self.monitoring_service, '_get_current_review_rate') as mock_review, \
             patch.object(self.monitoring_service, '_get_baseline_rate') as mock_baseline:
            mock_review.return_value = 75.0  # High review rate
            mock_baseline.return_value = 30.0  # Lower baseline rate (150% increase)
            
            breach = await self.monitoring_service._check_review_rate_spike()
            
            # Should return a breach since 150% increase is > 50% threshold
            assert breach is not None
            assert breach.rule_name == "review_rate_spike"
            assert breach.current_value == 75.0
            assert breach.severity == AlertSeverity.WARNING
    
    @pytest.mark.asyncio
    async def test_check_rpc_error_rate(self):
        """Test checking RPC error rate threshold."""
        # Mock high RPC error rate that should trigger breach
        with patch.object(self.monitoring_service, '_get_current_rpc_error_rate') as mock_rpc:
            mock_rpc.return_value = 15.0  # High error rate
            
            breach = await self.monitoring_service._check_rpc_error_rate()
            
            # Should return a breach since 15% is > 10% threshold
            assert breach is not None
            assert breach.rule_name == "rpc_error_rate"
            assert breach.current_value == 15.0
            assert breach.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_check_system_health(self):
        """Test checking system health threshold."""
        # Mock low system health that should trigger breach
        with patch.object(self.monitoring_service, '_get_current_system_health') as mock_health:
            mock_health.return_value = 25.0  # Low health score
            
            breach = await self.monitoring_service._check_system_health()
            
            # Should return a breach since 25% is < 30% threshold
            assert breach is not None
            assert breach.rule_name == "system_health_degradation"
            assert breach.current_value == 25.0
            assert breach.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_check_fetch_latency(self):
        """Test checking fetch latency threshold."""
        # Mock high fetch latency that should trigger breach
        with patch.object(self.monitoring_service, '_get_current_fetch_latency') as mock_latency:
            mock_latency.return_value = 90.0  # High latency
            
            breach = await self.monitoring_service._check_fetch_latency()
            
            # Should return a breach since 90s is > 60s threshold
            assert breach is not None
            assert breach.rule_name == "fetch_latency_exceeded"
            assert breach.current_value == 90.0
            assert breach.severity == AlertSeverity.WARNING
    
    @pytest.mark.asyncio
    async def test_check_validation_error_rate(self):
        """Test checking validation error rate threshold."""
        # Mock high validation error rate that should trigger breach
        with patch.object(self.monitoring_service, '_get_current_validation_error_rate') as mock_validation:
            mock_validation.return_value = 25.0  # High error rate
            
            breach = await self.monitoring_service._check_validation_error_rate()
            
            # Should return a breach since 25% is > 20% threshold
            assert breach is not None
            assert breach.rule_name == "validation_error_rate"
            assert breach.current_value == 25.0
            assert breach.severity == AlertSeverity.WARNING
    
    @pytest.mark.asyncio
    async def test_check_database_connections(self):
        """Test checking database connection failures threshold."""
        # Mock high database failures that should trigger breach
        with patch.object(self.monitoring_service, '_get_current_database_failures') as mock_db:
            mock_db.return_value = 8.0  # High failure count
            
            breach = await self.monitoring_service._check_database_connections()
            
            # Should return a breach since 8 is > 5 threshold
            assert breach is not None
            assert breach.rule_name == "database_connection_failures"
            assert breach.current_value == 8.0
            assert breach.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_check_memory_usage(self):
        """Test checking memory usage threshold."""
        # Mock high memory usage that should trigger breach
        with patch.object(self.monitoring_service, '_get_current_memory_usage') as mock_memory:
            mock_memory.return_value = 90.0  # High memory usage
            
            breach = await self.monitoring_service._check_memory_usage()
            
            # Should return a breach since 90% is > 85% threshold
            assert breach is not None
            assert breach.rule_name == "memory_usage_high"
            assert breach.current_value == 90.0
            assert breach.severity == AlertSeverity.WARNING
    
    @pytest.mark.asyncio
    async def test_check_disk_usage(self):
        """Test checking disk usage threshold."""
        # Mock high disk usage that should trigger breach
        with patch.object(self.monitoring_service, '_get_current_disk_usage') as mock_disk:
            mock_disk.return_value = 95.0  # High disk usage
            
            breach = await self.monitoring_service._check_disk_usage()
            
            # Should return a breach since 95% is > 90% threshold
            assert breach is not None
            assert breach.rule_name == "disk_usage_high"
            assert breach.current_value == 95.0
            assert breach.severity == AlertSeverity.CRITICAL
    
    def test_baseline_rate_calculation(self):
        """Test baseline rate calculation."""
        # Test initial baseline
        baseline = self.monitoring_service._get_baseline_rate("test_metric", 50.0)
        assert baseline == 50.0
        
        # Test exponential moving average
        baseline = self.monitoring_service._get_baseline_rate("test_metric", 60.0)
        assert baseline != 50.0  # Should be updated
        assert baseline > 50.0  # Should be higher than original
    
    def test_cooldown_functionality(self):
        """Test alert cooldown functionality."""
        # Use an existing threshold name
        threshold_name = "review_rate_spike"
        
        # Test initial state
        assert not self.monitoring_service._is_in_cooldown(threshold_name)
        
        # Record cooldown
        self.monitoring_service._record_cooldown(threshold_name)
        
        # Should be in cooldown
        assert self.monitoring_service._is_in_cooldown(threshold_name)
    
    @pytest.mark.asyncio
    async def test_process_threshold_breaches(self):
        """Test processing threshold breaches."""
        # Create mock breaches
        breach1 = ThresholdBreach(
            rule_name="test_rule_1",
            metric_name="test_metric_1",
            current_value=100.0,
            threshold=50.0,
            severity=AlertSeverity.WARNING,
            component="test",
            timestamp=time.time(),
            exceeded_by_percent=100.0
        )
        
        breach2 = ThresholdBreach(
            rule_name="test_rule_2",
            metric_name="test_metric_2",
            current_value=200.0,
            threshold=100.0,
            severity=AlertSeverity.CRITICAL,
            component="test",
            timestamp=time.time(),
            exceeded_by_percent=100.0
        )
        
        breaches = [breach1, breach2]
        
        # Mock alert service
        self.alert_service.process_threshold_breaches = AsyncMock()
        
        # Process breaches
        await self.monitoring_service.process_threshold_breaches(breaches)
        
        # Verify alert service was called twice (once for each breach)
        assert self.alert_service.process_threshold_breaches.call_count == 2
        # Verify it was called with individual breaches
        self.alert_service.process_threshold_breaches.assert_any_call([breach1])
        self.alert_service.process_threshold_breaches.assert_any_call([breach2])
    
    def test_get_monitoring_status(self):
        """Test getting monitoring service status."""
        status = self.monitoring_service.get_monitoring_status()
        
        assert "thresholds_configured" in status
        assert "active_cooldowns" in status
        assert "baseline_metrics" in status
        assert "historical_data_points" in status
        assert "thresholds" in status
        
        # Verify structure
        assert isinstance(status["thresholds_configured"], int)
        assert isinstance(status["active_cooldowns"], int)
        assert isinstance(status["baseline_metrics"], int)
        assert isinstance(status["historical_data_points"], int)
        assert isinstance(status["thresholds"], dict)
        
        # Verify thresholds configuration
        assert len(status["thresholds"]) > 0
        for name, config in status["thresholds"].items():
            assert "threshold_value" in config
            assert "severity" in config
            assert "component" in config
            assert "cooldown_minutes" in config


class TestMockDataMethods:
    """Test mock data methods for testing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline_metrics = Mock(spec=PipelineMetrics)
        self.database_metrics = Mock(spec=DatabaseMetricsService)
        self.alert_service = Mock()
        
        self.monitoring_service = ThresholdMonitoringService(
            pipeline_metrics=self.pipeline_metrics,
            database_metrics=self.database_metrics,
            alert_service=self.alert_service
        )
    
    @pytest.mark.asyncio
    async def test_mock_data_methods(self):
        """Test all mock data methods return expected values."""
        # Test review rate
        review_rate = await self.monitoring_service._get_current_review_rate()
        assert review_rate == 45.0
        
        # Test RPC error rate
        rpc_rate = await self.monitoring_service._get_current_rpc_error_rate()
        assert rpc_rate == 5.0
        
        # Test system health
        health = await self.monitoring_service._get_current_system_health()
        assert health == 85.0
        
        # Test fetch latency
        latency = await self.monitoring_service._get_current_fetch_latency()
        assert latency == 15.0
        
        # Test validation error rate
        validation_rate = await self.monitoring_service._get_current_validation_error_rate()
        assert validation_rate == 8.0
        
        # Test database failures
        db_failures = await self.monitoring_service._get_current_database_failures()
        assert db_failures == 2.0
        
        # Test memory usage
        memory = await self.monitoring_service._get_current_memory_usage()
        assert memory == 65.0
        
        # Test disk usage
        disk = await self.monitoring_service._get_current_disk_usage()
        assert disk == 45.0


class TestThresholdScenarios:
    """Test various threshold breach scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline_metrics = Mock(spec=PipelineMetrics)
        self.database_metrics = Mock(spec=DatabaseMetricsService)
        self.alert_service = Mock()
        
        self.monitoring_service = ThresholdMonitoringService(
            pipeline_metrics=self.pipeline_metrics,
            database_metrics=self.database_metrics,
            alert_service=self.alert_service
        )
    
    @pytest.mark.asyncio
    async def test_critical_system_failure_scenario(self):
        """Test critical system failure scenario."""
        # Mock critical system health
        with patch.object(self.monitoring_service, '_get_current_system_health') as mock_health:
            mock_health.return_value = 15.0  # Very low health
            
            breach = await self.monitoring_service._check_system_health()
            
            assert breach is not None
            assert breach.severity == AlertSeverity.CRITICAL
            assert breach.current_value == 15.0
            assert breach.threshold == 30.0
    
    @pytest.mark.asyncio
    async def test_high_review_rate_spike_scenario(self):
        """Test high review rate spike scenario."""
        # Mock high review rate
        with patch.object(self.monitoring_service, '_get_current_review_rate') as mock_review, \
             patch.object(self.monitoring_service, '_get_baseline_rate') as mock_baseline:
            mock_review.return_value = 90.0  # Very high review rate
            mock_baseline.return_value = 30.0  # Lower baseline rate (200% increase)
            
            breach = await self.monitoring_service._check_review_rate_spike()
            
            assert breach is not None
            assert breach.severity == AlertSeverity.WARNING
            assert breach.current_value == 90.0
    
    @pytest.mark.asyncio
    async def test_database_crisis_scenario(self):
        """Test database crisis scenario."""
        # Mock high database failures
        with patch.object(self.monitoring_service, '_get_current_database_failures') as mock_db:
            mock_db.return_value = 15.0  # Very high failure count
            
            breach = await self.monitoring_service._check_database_connections()
            
            assert breach is not None
            assert breach.severity == AlertSeverity.CRITICAL
            assert breach.current_value == 15.0
            assert breach.threshold == 5.0
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_scenario(self):
        """Test resource exhaustion scenario."""
        # Mock high memory and disk usage
        with patch.object(self.monitoring_service, '_get_current_memory_usage') as mock_memory, \
             patch.object(self.monitoring_service, '_get_current_disk_usage') as mock_disk:
            
            mock_memory.return_value = 95.0  # Very high memory usage
            mock_disk.return_value = 98.0  # Very high disk usage
            
            memory_breach = await self.monitoring_service._check_memory_usage()
            disk_breach = await self.monitoring_service._check_disk_usage()
            
            assert memory_breach is not None
            assert memory_breach.severity == AlertSeverity.WARNING
            assert memory_breach.current_value == 95.0
            
            assert disk_breach is not None
            assert disk_breach.severity == AlertSeverity.CRITICAL
            assert disk_breach.current_value == 98.0


if __name__ == "__main__":
    pytest.main([__file__])
