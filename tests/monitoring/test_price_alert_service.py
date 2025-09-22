"""
Tests for price alert service with Slack and Sentry integration.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from src.monitoring.price_alert_service import (
    PriceAlertService, 
    AlertThrottle, 
    SlackClient, 
    SentryClient
)
from src.monitoring.price_job_metrics import PriceDelta, PriceJobMetrics


class TestAlertThrottle:
    """Test alert throttling functionality."""
    
    def test_initialization(self):
        """Test throttle initialization."""
        throttle = AlertThrottle(throttle_window=300, max_alerts_per_window=5)
        assert throttle.throttle_window == 300
        assert throttle.max_alerts_per_window == 5
        assert throttle.alert_history == {}
    
    def test_should_throttle_new_alert(self):
        """Test throttling for new alert key."""
        throttle = AlertThrottle(max_alerts_per_window=3)
        assert throttle.should_throttle("new-alert-key") == False
    
    def test_should_throttle_within_limit(self):
        """Test throttling within limit."""
        throttle = AlertThrottle(max_alerts_per_window=3)
        
        # Record 2 alerts (within limit)
        throttle.record_alert("test-key")
        throttle.record_alert("test-key")
        
        assert throttle.should_throttle("test-key") == False
    
    def test_should_throttle_exceeds_limit(self):
        """Test throttling when limit exceeded."""
        throttle = AlertThrottle(max_alerts_per_window=2)
        
        # Record 3 alerts (exceeds limit)
        throttle.record_alert("test-key")
        throttle.record_alert("test-key")
        throttle.record_alert("test-key")
        
        assert throttle.should_throttle("test-key") == True


class TestSlackClient:
    """Test Slack client functionality."""
    
    def test_initialization(self):
        """Test Slack client initialization."""
        client = SlackClient("https://hooks.slack.com/test")
        assert client.webhook_url == "https://hooks.slack.com/test"
    
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        client = SlackClient("https://hooks.slack.com/test")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            message = {"text": "Test message"}
            result = await client.send_message(message)
            
            assert result == True
    
    @pytest.mark.asyncio
    async def test_send_message_failure(self):
        """Test message sending failure."""
        client = SlackClient("https://hooks.slack.com/test")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            message = {"text": "Test message"}
            result = await client.send_message(message)
            
            assert result == False
    
    @pytest.mark.asyncio
    async def test_send_message_exception(self):
        """Test message sending with exception."""
        client = SlackClient("https://hooks.slack.com/test")
        
        with patch('httpx.AsyncClient', side_effect=Exception("Network error")):
            message = {"text": "Test message"}
            result = await client.send_message(message)
            
            assert result == False


class TestSentryClient:
    """Test Sentry client functionality."""
    
    def test_initialization(self):
        """Test Sentry client initialization."""
        client = SentryClient("https://test@sentry.io/test")
        assert client.dsn == "https://test@sentry.io/test"
    
    def test_capture_exception(self):
        """Test exception capturing."""
        client = SentryClient("https://test@sentry.io/test")
        
        with patch('sentry_sdk.push_scope') as mock_scope:
            mock_scope.return_value.__enter__.return_value = None
            
            error = Exception("Test error")
            context = {"test": "context"}
            
            # Should not raise exception
            client.capture_exception(error, context)
    
    def test_capture_message(self):
        """Test message capturing."""
        client = SentryClient("https://test@sentry.io/test")
        
        with patch('sentry_sdk.push_scope') as mock_scope:
            mock_scope.return_value.__enter__.return_value = None
            
            # Should not raise exception
            client.capture_message("Test message", "info", {"test": "context"})


class TestPriceAlertService:
    """Test price alert service functionality."""
    
    def test_initialization(self):
        """Test alert service initialization."""
        service = PriceAlertService(
            slack_webhook_url="https://hooks.slack.com/test",
            sentry_dsn="https://test@sentry.io/test"
        )
        
        assert service.slack_client.webhook_url == "https://hooks.slack.com/test"
        assert service.sentry_client.dsn == "https://test@sentry.io/test"
        assert service.price_spike_threshold == 50.0
    
    def test_is_price_spike_true(self):
        """Test price spike detection for spike."""
        service = PriceAlertService("test", "test")
        
        delta = PriceDelta(
            variant_id="test",
            old_price=Decimal("25.00"),
            new_price=Decimal("40.00"),  # 60% increase
            currency="USD"
        )
        
        assert service._is_price_spike(delta) == True
    
    def test_is_price_spike_false(self):
        """Test price spike detection for non-spike."""
        service = PriceAlertService("test", "test")
        
        delta = PriceDelta(
            variant_id="test",
            old_price=Decimal("25.00"),
            new_price=Decimal("30.00"),  # 20% increase
            currency="USD"
        )
        
        assert service._is_price_spike(delta) == False
    
    def test_is_price_spike_zero_old_price(self):
        """Test price spike detection with zero old price."""
        service = PriceAlertService("test", "test")
        
        delta = PriceDelta(
            variant_id="test",
            old_price=Decimal("0.00"),
            new_price=Decimal("30.00"),
            currency="USD"
        )
        
        assert service._is_price_spike(delta) == False
    
    @pytest.mark.asyncio
    async def test_check_price_spike_with_spike(self):
        """Test price spike checking with actual spike."""
        service = PriceAlertService("test", "test")
        
        delta = PriceDelta(
            variant_id="test",
            old_price=Decimal("25.00"),
            new_price=Decimal("40.00"),  # 60% increase
            currency="USD",
            roaster_id="test-roaster"
        )
        
        with patch.object(service, '_send_price_spike_alert') as mock_send:
            await service.check_price_spike([delta])
            mock_send.assert_called_once_with(delta)
    
    @pytest.mark.asyncio
    async def test_check_price_spike_without_spike(self):
        """Test price spike checking without spike."""
        service = PriceAlertService("test", "test")
        
        delta = PriceDelta(
            variant_id="test",
            old_price=Decimal("25.00"),
            new_price=Decimal("30.00"),  # 20% increase
            currency="USD"
        )
        
        with patch.object(service, '_send_price_spike_alert') as mock_send:
            await service.check_price_spike([delta])
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_price_spike_alert(self):
        """Test sending price spike alert."""
        service = PriceAlertService("test", "test")
        
        delta = PriceDelta(
            variant_id="test-variant",
            old_price=Decimal("25.00"),
            new_price=Decimal("40.00"),
            currency="USD",
            roaster_id="test-roaster"
        )
        
        with patch.object(service.slack_client, 'send_message', return_value=True) as mock_slack:
            with patch.object(service.sentry_client, 'capture_message') as mock_sentry:
                await service._send_price_spike_alert(delta)
                
                # Verify Slack message was sent
                mock_slack.assert_called_once()
                call_args = mock_slack.call_args[0][0]
                assert "Price Spike Alert" in call_args["text"]
                assert "test-variant" in str(call_args["attachments"])
                
                # Verify Sentry message was captured
                mock_sentry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_job_failure_alert(self):
        """Test sending job failure alert."""
        service = PriceAlertService("test", "test")
        
        with patch.object(service.slack_client, 'send_message', return_value=True) as mock_slack:
            with patch.object(service.sentry_client, 'capture_exception') as mock_sentry:
                await service.send_job_failure_alert(
                    job_id="test-job",
                    error_type="network_error",
                    error_message="Connection timeout",
                    roaster_id="test-roaster"
                )
                
                # Verify Slack message was sent
                mock_slack.assert_called_once()
                call_args = mock_slack.call_args[0][0]
                assert "Price Job Failure" in call_args["text"]
                assert "test-job" in str(call_args["attachments"])
                
                # Verify Sentry exception was captured
                mock_sentry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_performance_alert(self):
        """Test sending performance alert."""
        service = PriceAlertService("test", "test")
        
        with patch.object(service.slack_client, 'send_message', return_value=True) as mock_slack:
            with patch.object(service.sentry_client, 'capture_message') as mock_sentry:
                await service.send_performance_alert(
                    metric_name="job_duration",
                    current_value=10.0,
                    threshold=5.0,
                    roaster_id="test-roaster"
                )
                
                # Verify Slack message was sent
                mock_slack.assert_called_once()
                call_args = mock_slack.call_args[0][0]
                assert "Performance Alert" in call_args["text"]
                assert "job_duration" in str(call_args["attachments"])
                
                # Verify Sentry message was captured
                mock_sentry.assert_called_once()
    
    def test_get_alert_status(self):
        """Test getting alert service status."""
        service = PriceAlertService("test", "test")
        status = service.get_alert_status()
        
        assert "throttle_status" in status
        assert "thresholds" in status
        assert "clients" in status
        assert status["clients"]["slack_configured"] == True
        assert status["clients"]["sentry_configured"] == True
