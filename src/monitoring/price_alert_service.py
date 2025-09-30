"""
Price alert service with Slack and Sentry integration.

This module provides comprehensive alerting capabilities for price spikes,
job failures, and system anomalies with intelligent throttling.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal

from .price_job_metrics import PriceDelta, PriceJobMetrics


@dataclass
class AlertThrottle:
    """Alert throttling to prevent spam."""
    
    def __init__(self, throttle_window: int = 300, max_alerts_per_window: int = 5):
        """Initialize alert throttle."""
        self.throttle_window = throttle_window  # 5 minutes
        self.max_alerts_per_window = max_alerts_per_window
        self.alert_history: Dict[str, List[float]] = {}
    
    def should_throttle(self, alert_key: str) -> bool:
        """Check if alert should be throttled."""
        now = time.time()
        if alert_key not in self.alert_history:
            self.alert_history[alert_key] = []
        
        # Clean old alerts outside throttle window
        self.alert_history[alert_key] = [
            timestamp for timestamp in self.alert_history[alert_key]
            if now - timestamp < self.throttle_window
        ]
        
        # Check if we've exceeded the limit
        return len(self.alert_history[alert_key]) >= self.max_alerts_per_window
    
    def record_alert(self, alert_key: str):
        """Record alert timestamp."""
        now = time.time()
        if alert_key not in self.alert_history:
            self.alert_history[alert_key] = []
        self.alert_history[alert_key].append(now)


class SlackClient:
    """Slack webhook client for sending alerts."""
    
    def __init__(self, webhook_url: str):
        """Initialize Slack client."""
        self.webhook_url = webhook_url
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to Slack webhook."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=message,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Slack message: {e}")
            return False


class SentryClient:
    """Sentry client for error tracking."""
    
    def __init__(self, dsn: str):
        """Initialize Sentry client."""
        self.dsn = dsn
        self._initialize_sentry()
    
    def _initialize_sentry(self):
        """Initialize Sentry SDK."""
        try:
            import sentry_sdk
            from sentry_sdk.integrations.asyncio import AsyncioIntegration
            from sentry_sdk.integrations.httpx import HttpxIntegration
            
            sentry_sdk.init(
                dsn=self.dsn,
                integrations=[
                    AsyncioIntegration(),
                    HttpxIntegration(),
                ],
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1,
            )
        except ImportError:
            print("Warning: Sentry SDK not available")
        except Exception as e:
            print(f"Warning: Failed to initialize Sentry: {e}")
    
    def capture_exception(self, error: Exception, context: Dict[str, Any] = None):
        """Capture exception with context."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                if context:
                    scope.set_context("alert_context", context)
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture exception: {e}")
    
    def capture_message(self, message: str, level: str = "info", context: Dict[str, Any] = None):
        """Capture message with context."""
        try:
            import sentry_sdk
            # Use new Sentry SDK v2+ API
            with sentry_sdk.new_scope() as scope:
                if context:
                    scope.set_context("alert_context", context)
                sentry_sdk.capture_message(message, level=level)
        except Exception as e:
            print(f"Failed to capture message: {e}")


class PriceAlertService:
    """Price alert service with comprehensive monitoring and alerting."""
    
    def __init__(
        self,
        slack_webhook_url: str,
        sentry_dsn: str,
        metrics: Optional[PriceJobMetrics] = None
    ):
        """Initialize price alert service."""
        self.slack_client = SlackClient(slack_webhook_url)
        self.sentry_client = SentryClient(sentry_dsn)
        self.alert_throttle = AlertThrottle()
        self.metrics = metrics or PriceJobMetrics()
        
        # Alert thresholds
        self.price_spike_threshold = 50.0  # 50% price increase
        self.job_failure_threshold = 10.0  # 10% failure rate
        self.performance_degradation_threshold = 2.0  # 2x baseline
    
    async def check_price_spike(self, price_deltas: List[PriceDelta]) -> None:
        """Check for price spikes and send alerts."""
        for delta in price_deltas:
            if self._is_price_spike(delta):
                await self._send_price_spike_alert(delta)
    
    def _is_price_spike(self, delta: PriceDelta) -> bool:
        """Determine if price change constitutes a spike."""
        if delta.old_price == 0:
            return False
        
        increase_pct = delta.price_change_percentage
        return increase_pct > self.price_spike_threshold
    
    async def _send_price_spike_alert(self, delta: PriceDelta) -> None:
        """Send Slack alert for price spike."""
        alert_key = f"price_spike_{delta.variant_id}"
        
        if self.alert_throttle.should_throttle(alert_key):
            return
        
        # Record metrics
        self.metrics.record_price_spike_alert(delta.roaster_id, delta.variant_id)
        
        # Create alert message
        message = {
            "text": "🚨 Price Spike Alert",
            "attachments": [{
                "color": "danger",
                "fields": [
                    {"title": "Variant ID", "value": delta.variant_id, "short": True},
                    {"title": "Roaster", "value": delta.roaster_id, "short": True},
                    {"title": "Old Price", "value": f"${delta.old_price:.2f}", "short": True},
                    {"title": "New Price", "value": f"${delta.new_price:.2f}", "short": True},
                    {"title": "Increase", "value": f"{delta.price_change_percentage:.1f}%", "short": True},
                    {"title": "Currency", "value": delta.currency, "short": True}
                ],
                "footer": "Coffee Scraper Monitoring",
                "ts": int(delta.timestamp)
            }]
        }
        
        # Send to Slack
        success = await self.slack_client.send_message(message)
        if success:
            self.alert_throttle.record_alert(alert_key)
        
        # Send to Sentry
        self.sentry_client.capture_message(
            f"Price spike detected: {delta.variant_id} increased by {delta.price_change_percentage:.1f}%",
            level="warning",
            context=delta.to_dict()
        )
    
    async def send_job_failure_alert(
        self,
        job_id: str,
        error_type: str,
        error_message: str,
        roaster_id: str
    ) -> None:
        """Send alert for job failure."""
        alert_key = f"job_failure_{roaster_id}"
        
        if self.alert_throttle.should_throttle(alert_key):
            return
        
        message = {
            "text": "⚠️ Price Job Failure",
            "attachments": [{
                "color": "warning",
                "fields": [
                    {"title": "Job ID", "value": job_id, "short": True},
                    {"title": "Roaster", "value": roaster_id, "short": True},
                    {"title": "Error Type", "value": error_type, "short": True},
                    {"title": "Error Message", "value": error_message[:500], "short": False}
                ],
                "footer": "Coffee Scraper Monitoring",
                "ts": int(time.time())
            }]
        }
        
        # Send to Slack
        success = await self.slack_client.send_message(message)
        if success:
            self.alert_throttle.record_alert(alert_key)
        
        # Send to Sentry
        self.sentry_client.capture_exception(
            Exception(f"Job failure: {error_message}"),
            context={
                "job_id": job_id,
                "roaster_id": roaster_id,
                "error_type": error_type
            }
        )
    
    async def send_performance_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        roaster_id: str
    ) -> None:
        """Send performance degradation alert."""
        alert_key = f"performance_{roaster_id}_{metric_name}"
        
        if self.alert_throttle.should_throttle(alert_key):
            return
        
        message = {
            "text": "📊 Performance Alert",
            "attachments": [{
                "color": "warning",
                "fields": [
                    {"title": "Metric", "value": metric_name, "short": True},
                    {"title": "Roaster", "value": roaster_id, "short": True},
                    {"title": "Current Value", "value": f"{current_value:.2f}", "short": True},
                    {"title": "Threshold", "value": f"{threshold:.2f}", "short": True},
                    {"title": "Exceeded By", "value": f"{((current_value - threshold) / threshold * 100):.1f}%", "short": True}
                ],
                "footer": "Coffee Scraper Monitoring",
                "ts": int(time.time())
            }]
        }
        
        # Send to Slack
        success = await self.slack_client.send_message(message)
        if success:
            self.alert_throttle.record_alert(alert_key)
        
        # Send to Sentry
        self.sentry_client.capture_message(
            f"Performance threshold exceeded: {metric_name} = {current_value:.2f} (threshold: {threshold:.2f})",
            level="warning",
            context={
                "metric_name": metric_name,
                "current_value": current_value,
                "threshold": threshold,
                "roaster_id": roaster_id
            }
        )
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert service status."""
        return {
            "throttle_status": {
                "active_alerts": len(self.alert_throttle.alert_history),
                "throttle_window": self.alert_throttle.throttle_window,
                "max_alerts_per_window": self.alert_throttle.max_alerts_per_window
            },
            "thresholds": {
                "price_spike_threshold": self.price_spike_threshold,
                "job_failure_threshold": self.job_failure_threshold,
                "performance_degradation_threshold": self.performance_degradation_threshold
            },
            "clients": {
                "slack_configured": bool(self.slack_client.webhook_url),
                "sentry_configured": bool(self.sentry_client.dsn)
            }
        }
