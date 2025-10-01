"""
Comprehensive alert service with threshold monitoring and Slack integration.

This module extends the existing PriceAlertService with comprehensive alerting
capabilities for review rate spikes, RPC errors, and system failures.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .price_alert_service import PriceAlertService, AlertThrottle, SlackClient
from .sentry_integration import SentryIntegration
from .pipeline_metrics import PipelineMetrics


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Alert rule configuration."""

    name: str
    metric_name: str
    threshold: float
    severity: AlertSeverity
    component: str
    description: str
    cooldown_minutes: int = 5


@dataclass
class ThresholdBreach:
    """Threshold breach event."""

    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    component: str
    timestamp: float
    exceeded_by_percent: float


class ThresholdMonitor:
    """Monitor thresholds and detect breaches."""

    def __init__(self, metrics: PipelineMetrics):
        """Initialize threshold monitor."""
        self.metrics = metrics
        # metric_name -> [(timestamp, value)]
        self.historical_data: Dict[str, List[Tuple[float, float]]] = {}
        # metric_name -> baseline_value
        self.baseline_data: Dict[str, float] = {}

        # Default alert rules
        self.alert_rules = {
            "review_rate_spike": AlertRule(
                name="review_rate_spike",
                metric_name="review_rate_percent",
                threshold=50.0,  # 50% increase
                severity=AlertSeverity.WARNING,
                component="normalizer",
                description="Review rate spike detected",
            ),
            "rpc_error_rate": AlertRule(
                name="rpc_error_rate",
                metric_name="rpc_error_percentage",
                threshold=10.0,  # 10% error rate
                severity=AlertSeverity.CRITICAL,
                component="database",
                description="RPC error rate exceeded",
            ),
            "system_failure": AlertRule(
                name="system_failure",
                metric_name="system_health_score",
                threshold=30.0,  # Below 30% health
                severity=AlertSeverity.CRITICAL,
                component="system",
                description="System health degraded",
            ),
            "fetch_latency": AlertRule(
                name="fetch_latency",
                metric_name="fetch_latency_seconds",
                threshold=60.0,  # 60 seconds
                severity=AlertSeverity.WARNING,
                component="fetcher",
                description="Fetch latency exceeded",
            ),
            "validation_error_rate": AlertRule(
                name="validation_error_rate",
                metric_name="validation_error_percentage",
                threshold=20.0,  # 20% error rate
                severity=AlertSeverity.WARNING,
                component="validator",
                description="Validation error rate high",
            ),
        }

    def update_metric_value(self, metric_name: str, value: float):
        """Update metric value and check for threshold breaches."""
        timestamp = time.time()

        # Store historical data (keep last 100 points)
        if metric_name not in self.historical_data:
            self.historical_data[metric_name] = []

        self.historical_data[metric_name].append((timestamp, value))

        # Keep only last 100 points
        if len(self.historical_data[metric_name]) > 100:
            self.historical_data[metric_name] = self.historical_data[
                metric_name
            ][-100:]

        # Update baseline if needed
        if metric_name not in self.baseline_data:
            self.baseline_data[metric_name] = value

        # Check for breaches
        breaches = []
        for rule_name, rule in self.alert_rules.items():
            if rule.metric_name == metric_name:
                breach = self._check_threshold_breach(rule, value)
                if breach:
                    breaches.append(breach)

        return breaches

    def _check_threshold_breach(
        self, rule: AlertRule, current_value: float
    ) -> Optional[ThresholdBreach]:
        """Check if current value breaches the rule threshold."""
        if rule.metric_name == "review_rate_percent":
            # For review rate, check for spike vs baseline
            baseline = self.baseline_data.get(rule.metric_name, current_value)
            if baseline > 0:
                increase_percent = (
                    (current_value - baseline) / baseline
                ) * 100
                if increase_percent > rule.threshold:
                    return ThresholdBreach(
                        rule_name=rule.name,
                        metric_name=rule.metric_name,
                        current_value=current_value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        component=rule.component,
                        timestamp=time.time(),
                        exceeded_by_percent=increase_percent,
                    )
        else:
            # For other metrics, check direct threshold
            if current_value > rule.threshold:
                exceeded_by = (
                    ((current_value - rule.threshold) / rule.threshold) * 100
                    if rule.threshold > 0
                    else 0
                )
                return ThresholdBreach(
                    rule_name=rule.name,
                    metric_name=rule.metric_name,
                    current_value=current_value,
                    threshold=rule.threshold,
                    severity=rule.severity,
                    component=rule.component,
                    timestamp=time.time(),
                    exceeded_by_percent=exceeded_by,
                )

        return None

    def get_metric_history(
        self, metric_name: str, hours: int = 24
    ) -> List[Tuple[float, float]]:
        """Get metric history for the last N hours."""
        if metric_name not in self.historical_data:
            return []

        cutoff_time = time.time() - (hours * 3600)
        return [
            (timestamp, value)
            for timestamp, value in self.historical_data[metric_name]
            if timestamp >= cutoff_time
        ]

    def get_baseline_value(self, metric_name: str) -> float:
        """Get baseline value for a metric."""
        return self.baseline_data.get(metric_name, 0.0)


class ComprehensiveAlertService:
    """Comprehensive alert service with threshold monitoring and Slack integration."""

    def __init__(
        self,
        slack_webhook_url: str,
        sentry_dsn: str,
        metrics: Optional[PipelineMetrics] = None,
    ):
        """Initialize comprehensive alert service."""
        self.slack_client = SlackClient(slack_webhook_url)
        self.sentry_integration = SentryIntegration(sentry_dsn)
        self.metrics = metrics or PipelineMetrics()
        self.threshold_monitor = ThresholdMonitor(self.metrics)

        # Integrate with existing B.3 PriceAlertService for price monitoring
        self.price_alert_service = PriceAlertService(
            slack_webhook_url=slack_webhook_url,
            sentry_dsn=sentry_dsn,
            metrics=self.metrics,
        )

        # Alert throttling
        self.alert_throttle = AlertThrottle(
            throttle_window=300, max_alerts_per_window=10
        )

        # Alert cooldown tracking
        self.alert_cooldowns: Dict[str, float] = {}
        self.cooldown_minutes = 5

    async def check_thresholds(self) -> List[ThresholdBreach]:
        """Check all thresholds and return breaches."""
        breaches = []

        # Check review rate spike
        review_rate = self._get_review_rate()
        if review_rate is not None:
            review_breaches = self.threshold_monitor.update_metric_value(
                "review_rate_percent", review_rate
            )
            breaches.extend(review_breaches)

        # Check RPC error rate
        rpc_error_rate = self._get_rpc_error_rate()
        if rpc_error_rate is not None:
            rpc_breaches = self.threshold_monitor.update_metric_value(
                "rpc_error_percentage", rpc_error_rate
            )
            breaches.extend(rpc_breaches)

        # Check system health
        system_health = self._get_system_health()
        if system_health is not None:
            health_breaches = self.threshold_monitor.update_metric_value(
                "system_health_score", system_health
            )
            breaches.extend(health_breaches)

        # Check fetch latency
        fetch_latency = self._get_avg_fetch_latency()
        if fetch_latency is not None:
            latency_breaches = self.threshold_monitor.update_metric_value(
                "fetch_latency_seconds", fetch_latency
            )
            breaches.extend(latency_breaches)

        # Check validation error rate
        validation_error_rate = self._get_validation_error_rate()
        if validation_error_rate is not None:
            validation_breaches = self.threshold_monitor.update_metric_value(
                "validation_error_percentage", validation_error_rate
            )
            breaches.extend(validation_breaches)

        return breaches

    async def check_price_alerts(self, price_deltas: List[Any] = None) -> List[Dict[str, Any]]:
        """Check for price spikes using existing B.3 PriceAlertService."""
        price_alerts = []

        # Use existing price alert service to check for price spikes
        # This leverages the existing B.3 infrastructure
        try:
            # Get price deltas from metrics if not provided
            if price_deltas is None:
                # Get recent price deltas from metrics
                price_deltas = self.metrics.get_recent_price_deltas() if hasattr(self.metrics, 'get_recent_price_deltas') else []
            
            # Check for price spikes using the existing service
            if price_deltas:
                await self.price_alert_service.check_price_spike(price_deltas)
                price_alerts.append(
                    {
                        "type": "price_spike",
                        "service": "B.3_PriceAlertService",
                        "status": "checked",
                        "deltas_processed": len(price_deltas)
                    }
                )
        except Exception as e:
            # Log error but don't fail the entire check
            self.sentry_integration.capture_exception(e)

        return price_alerts

    async def check_all_alerts(self) -> Dict[str, Any]:
        """Check all types of alerts: thresholds, price spikes, and system health."""
        results = {
            "threshold_breaches": [],
            "price_alerts": [],
            "system_alerts": []
        }
        
        # Check threshold breaches
        threshold_breaches = await self.check_thresholds()
        results["threshold_breaches"] = threshold_breaches
        
        # Process threshold breaches
        if threshold_breaches:
            await self.process_threshold_breaches(threshold_breaches)
        
        # Check price alerts
        price_alerts = await self.check_price_alerts()
        results["price_alerts"] = price_alerts
        
        return results

    async def process_threshold_breaches(
        self, breaches: List[ThresholdBreach]
    ):
        """Process threshold breaches and send alerts."""
        for breach in breaches:
            # Check cooldown
            if self._is_in_cooldown(breach.rule_name):
                continue

            # Send Slack alert
            await self._send_threshold_alert(breach)

            # Send to Sentry
            self.sentry_integration.capture_threshold_breach(
                metric_name=breach.metric_name,
                current_value=breach.current_value,
                threshold=breach.threshold,
                component=breach.component,
                severity=breach.severity.value,
            )

            # Record cooldown
            self._record_cooldown(breach.rule_name)

    async def _send_threshold_alert(self, breach: ThresholdBreach):
        """Send threshold breach alert to Slack."""
        alert_key = f"threshold_{breach.rule_name}"

        if self.alert_throttle.should_throttle(alert_key):
            return

        # Determine color based on severity
        color = (
            "good"
            if breach.severity == AlertSeverity.INFO
            else (
                "warning"
                if breach.severity == AlertSeverity.WARNING
                else "danger"
            )
        )

        # Create alert message
        message = {
            "text": f"🚨 {breach.severity.value.upper()} Alert: {breach.rule_name}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Metric",
                            "value": breach.metric_name,
                            "short": True,
                        },
                        {
                            "title": "Component",
                            "value": breach.component,
                            "short": True,
                        },
                        {
                            "title": "Current Value",
                            "value": f"{breach.current_value:.2f}",
                            "short": True,
                        },
                        {
                            "title": "Threshold",
                            "value": f"{breach.threshold:.2f}",
                            "short": True,
                        },
                        {
                            "title": "Exceeded By",
                            "value": f"{breach.exceeded_by_percent:.1f}%",
                            "short": True,
                        },
                        {
                            "title": "Severity",
                            "value": breach.severity.value.upper(),
                            "short": True,
                        },
                    ],
                    "footer": "Coffee Scraper Monitoring",
                    "ts": int(breach.timestamp),
                }
            ],
        }

        # Send to Slack
        success = await self.slack_client.send_message(message)
        if success:
            self.alert_throttle.record_alert(alert_key)

    def _is_in_cooldown(self, rule_name: str) -> bool:
        """Check if alert is in cooldown period."""
        if rule_name not in self.alert_cooldowns:
            return False

        return (time.time() - self.alert_cooldowns[rule_name]) < (
            self.cooldown_minutes * 60
        )

    def _record_cooldown(self, rule_name: str):
        """Record alert cooldown."""
        self.alert_cooldowns[rule_name] = time.time()

    def _get_review_rate(self) -> Optional[float]:
        """Get current review rate percentage."""
        # This would typically query the database for recent review rates
        # For now, return a mock value
        return 45.0  # Mock value

    def _get_rpc_error_rate(self) -> Optional[float]:
        """Get current RPC error rate percentage."""
        # This would typically calculate from metrics
        # For now, return a mock value
        return 5.0  # Mock value

    def _get_system_health(self) -> Optional[float]:
        """Get current system health score."""
        # This would typically calculate from various health indicators
        # For now, return a mock value
        return 85.0  # Mock value

    def _get_avg_fetch_latency(self) -> Optional[float]:
        """Get average fetch latency in seconds."""
        # This would typically calculate from metrics
        # For now, return a mock value
        return 15.0  # Mock value

    def _get_validation_error_rate(self) -> Optional[float]:
        """Get current validation error rate percentage."""
        # This would typically calculate from metrics
        # For now, return a mock value
        return 8.0  # Mock value

    async def send_system_failure_alert(
        self,
        component: str,
        failure_type: str,
        error_message: str,
        system_state: Dict[str, Any] = None,
    ):
        """Send system failure alert."""
        alert_key = f"system_failure_{component}"

        if self.alert_throttle.should_throttle(alert_key):
            return

        message = {
            "text": "🚨 CRITICAL: System Failure",
            "attachments": [
                {
                    "color": "danger",
                    "fields": [
                        {
                            "title": "Component",
                            "value": component,
                            "short": True,
                        },
                        {
                            "title": "Failure Type",
                            "value": failure_type,
                            "short": True,
                        },
                        {
                            "title": "Error Message",
                            "value": error_message[:500],
                            "short": False,
                        },
                    ],
                    "footer": "Coffee Scraper Monitoring",
                    "ts": int(time.time()),
                }
            ],
        }

        # Add system state if provided
        if system_state:
            message["attachments"][0]["fields"].append(
                {
                    "title": "System State",
                    "value": str(system_state)[:500],
                    "short": False,
                }
            )

        # Send to Slack
        success = await self.slack_client.send_message(message)
        if success:
            self.alert_throttle.record_alert(alert_key)

        # Send to Sentry
        self.sentry_integration.capture_system_failure(
            error=Exception(f"System failure: {error_message}"),
            component=component,
            failure_type=failure_type,
            system_state=system_state,
        )

    async def send_review_rate_spike_alert(
        self,
        roaster_id: str,
        platform: str,
        current_rate: float,
        baseline_rate: float,
        increase_percent: float,
    ):
        """Send review rate spike alert."""
        alert_key = f"review_spike_{roaster_id}_{platform}"

        if self.alert_throttle.should_throttle(alert_key):
            return

        message = {
            "text": "📈 Review Rate Spike Alert",
            "attachments": [
                {
                    "color": "warning",
                    "fields": [
                        {
                            "title": "Roaster",
                            "value": roaster_id,
                            "short": True,
                        },
                        {
                            "title": "Platform",
                            "value": platform,
                            "short": True,
                        },
                        {
                            "title": "Current Rate",
                            "value": f"{current_rate:.1f}%",
                            "short": True,
                        },
                        {
                            "title": "Baseline Rate",
                            "value": f"{baseline_rate:.1f}%",
                            "short": True,
                        },
                        {
                            "title": "Increase",
                            "value": f"{increase_percent:.1f}%",
                            "short": True,
                        },
                    ],
                    "footer": "Coffee Scraper Monitoring",
                    "ts": int(time.time()),
                }
            ],
        }

        # Send to Slack
        success = await self.slack_client.send_message(message)
        if success:
            self.alert_throttle.record_alert(alert_key)

        # Send to Sentry
        self.sentry_integration.capture_threshold_breach(
            metric_name="review_rate_percent",
            current_value=current_rate,
            threshold=baseline_rate,
            component="normalizer",
            severity="warning",
        )

    def get_alert_status(self) -> Dict[str, Any]:
        """Get comprehensive alert service status."""
        return {
            "threshold_monitor": {
                "active_rules": len(self.threshold_monitor.alert_rules),
                "historical_data_points": sum(
                    len(data)
                    for data in self.threshold_monitor.historical_data.values()
                ),
                "baseline_metrics": len(self.threshold_monitor.baseline_data),
            },
            "price_alert_service": {
                "integrated": True,
                "status": self.price_alert_service.get_alert_status() if hasattr(self.price_alert_service, 'get_alert_status') else {"status": "active"},
                "price_spike_threshold": getattr(self.price_alert_service, 'price_spike_threshold', 50.0),
                "job_failure_threshold": getattr(self.price_alert_service, 'job_failure_threshold', 10.0),
            },
            "alert_throttle": {
                "active_alerts": len(self.alert_throttle.alert_history),
                "throttle_window": self.alert_throttle.throttle_window,
                "max_alerts_per_window": self.alert_throttle.max_alerts_per_window,
            },
            "cooldowns": {
                "active_cooldowns": len(self.alert_cooldowns),
                "cooldown_minutes": self.cooldown_minutes,
            },
            "clients": {
                "slack_configured": bool(self.slack_client.webhook_url),
                "sentry_configured": bool(self.sentry_integration.dsn),
            },
            "sentry_status": self.sentry_integration.get_integration_status(),
        }
