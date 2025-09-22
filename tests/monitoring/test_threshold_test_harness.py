"""
Tests for threshold test harness functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from src.monitoring.threshold_test_harness import ThresholdTestHarness
from src.monitoring.price_alert_service import PriceAlertService
from src.monitoring.price_job_metrics import PriceDelta, PriceJobMetrics


class TestThresholdTestHarness:
    """Test threshold test harness functionality."""
    
    def test_initialization(self):
        """Test test harness initialization."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        assert harness.alert_service == alert_service
        assert harness.test_results == []
        assert harness.mock_clients == {}
    
    @pytest.mark.asyncio
    async def test_price_spike_alert_success(self):
        """Test successful price spike alert test."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        # Let the harness handle its own mocking
        result = await harness.test_price_spike_alert()
        
        assert result == True
        assert len(harness.test_results) == 1
        assert harness.test_results[0]["test"] == "price_spike_alert"
        assert harness.test_results[0]["status"] == "PASS"
    
    @pytest.mark.asyncio
    async def test_price_spike_alert_failure(self):
        """Test failed price spike alert test."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        # Mock Slack client to fail sending message
        with patch.object(alert_service.slack_client, 'send_message', side_effect=Exception("Slack API error")):
            result = await harness.test_price_spike_alert()
            
            assert result == False
            assert len(harness.test_results) == 1
            assert harness.test_results[0]["test"] == "price_spike_alert"
            assert harness.test_results[0]["status"] == "FAIL"
    
    @pytest.mark.asyncio
    async def test_rate_limit_backoff_success(self):
        """Test successful rate limit backoff test."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        result = await harness.test_rate_limit_backoff()
        
        assert result == True
        assert len(harness.test_results) == 1
        assert harness.test_results[0]["test"] == "rate_limit_backoff"
        assert harness.test_results[0]["status"] == "PASS"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test successful circuit breaker test."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        result = await harness.test_circuit_breaker()
        
        assert result == True
        assert len(harness.test_results) == 1
        assert harness.test_results[0]["test"] == "circuit_breaker"
        assert harness.test_results[0]["status"] == "PASS"
    
    @pytest.mark.asyncio
    async def test_alert_throttling_success(self):
        """Test successful alert throttling test."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        with patch.object(alert_service.slack_client, 'send_message', return_value=True) as mock_send:
            result = await harness.test_alert_throttling()
            
            assert result == True
            assert len(harness.test_results) == 1
            assert harness.test_results[0]["test"] == "alert_throttling"
            assert harness.test_results[0]["status"] == "PASS"
            # Should be throttled to max_alerts_per_window
            assert mock_send.call_count <= alert_service.alert_throttle.max_alerts_per_window
    
    @pytest.mark.asyncio
    async def test_metrics_collection_success(self):
        """Test successful metrics collection test."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        result = await harness.test_metrics_collection()
        
        assert result == True
        assert len(harness.test_results) == 1
        assert harness.test_results[0]["test"] == "metrics_collection"
        assert harness.test_results[0]["status"] == "PASS"
    
    @pytest.mark.asyncio
    async def test_performance_alert_success(self):
        """Test successful performance alert test."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        # Let the harness handle its own mocking
        result = await harness.test_performance_alert()
        
        assert result == True
        assert len(harness.test_results) == 1
        assert harness.test_results[0]["test"] == "performance_alert"
        assert harness.test_results[0]["status"] == "PASS"
    
    @pytest.mark.asyncio
    async def test_run_all_tests(self):
        """Test running all tests."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        with patch.object(alert_service.slack_client, 'send_message', return_value=True):
            results = await harness.run_all_tests()
            
            assert "total_tests" in results
            assert "passed" in results
            assert "failed" in results
            assert "success_rate" in results
            assert "results" in results
            assert "test_details" in results
            
            assert results["total_tests"] == 6
            assert results["passed"] >= 0
            assert results["failed"] >= 0
            assert results["success_rate"] >= 0.0
    
    def test_get_test_results(self):
        """Test getting test results."""
        alert_service = PriceAlertService("test", "test")
        harness = ThresholdTestHarness(alert_service)
        
        # Add some test results
        harness.test_results = [
            {"test": "test1", "status": "PASS"},
            {"test": "test2", "status": "FAIL"}
        ]
        
        results = harness.get_test_results()
        assert len(results) == 2
        assert results[0]["test"] == "test1"
        assert results[1]["test"] == "test2"
