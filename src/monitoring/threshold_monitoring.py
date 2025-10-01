"""
Threshold monitoring service using G.1 infrastructure.

This module provides comprehensive threshold monitoring for review rate spikes,
RPC errors, and system failures using the existing PipelineMetrics and DatabaseMetrics.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .pipeline_metrics import PipelineMetrics, MetricsCollector
from .database_metrics import DatabaseMetricsService
from .alert_service import (
    ComprehensiveAlertService,
    ThresholdBreach,
    AlertSeverity,
)


@dataclass
class MonitoringThreshold:
    """Monitoring threshold configuration."""

    name: str
    metric_name: str
    threshold_value: float
    comparison_type: str  # "greater_than", "less_than", "equals"
    severity: AlertSeverity
    component: str
    description: str
    cooldown_minutes: int = 5


class ThresholdMonitoringService:
    """Service for monitoring thresholds and triggering alerts."""

    def __init__(
        self,
        pipeline_metrics: PipelineMetrics,
        database_metrics: DatabaseMetricsService,
        alert_service: ComprehensiveAlertService,
    ):
        """Initialize threshold monitoring service."""
        self.pipeline_metrics = pipeline_metrics
        self.database_metrics = database_metrics
        self.alert_service = alert_service

        # Threshold configurations
        self.thresholds = {
            "review_rate_spike": MonitoringThreshold(
                name="review_rate_spike",
                metric_name="review_rate_percent",
                threshold_value=50.0,  # 50% increase
                comparison_type="greater_than",
                severity=AlertSeverity.WARNING,
                component="normalizer",
                description="Review rate spike detected (>50% increase)",
                cooldown_minutes=10,
            ),
            "rpc_error_rate": MonitoringThreshold(
                name="rpc_error_rate",
                metric_name="rpc_error_percentage",
                threshold_value=10.0,  # 10% error rate
                comparison_type="greater_than",
                severity=AlertSeverity.CRITICAL,
                component="database",
                description="RPC error rate exceeded (>10%)",
                cooldown_minutes=5,
            ),
            "system_health_degradation": MonitoringThreshold(
                name="system_health_degradation",
                metric_name="system_health_score",
                threshold_value=30.0,  # Below 30% health
                comparison_type="less_than",
                severity=AlertSeverity.CRITICAL,
                component="system",
                description="System health degraded (<30%)",
                cooldown_minutes=5,
            ),
            "fetch_latency_exceeded": MonitoringThreshold(
                name="fetch_latency_exceeded",
                metric_name="fetch_latency_seconds",
                threshold_value=60.0,  # 60 seconds
                comparison_type="greater_than",
                severity=AlertSeverity.WARNING,
                component="fetcher",
                description="Fetch latency exceeded (>60s)",
                cooldown_minutes=15,
            ),
            "validation_error_rate": MonitoringThreshold(
                name="validation_error_rate",
                metric_name="validation_error_percentage",
                threshold_value=20.0,  # 20% error rate
                comparison_type="greater_than",
                severity=AlertSeverity.WARNING,
                component="validator",
                description="Validation error rate high (>20%)",
                cooldown_minutes=10,
            ),
            "database_connection_failures": MonitoringThreshold(
                name="database_connection_failures",
                metric_name="database_connection_failures",
                threshold_value=5.0,  # 5 failures
                comparison_type="greater_than",
                severity=AlertSeverity.CRITICAL,
                component="database",
                description="Database connection failures (>5)",
                cooldown_minutes=5,
            ),
            "memory_usage_high": MonitoringThreshold(
                name="memory_usage_high",
                metric_name="memory_usage_percent",
                threshold_value=85.0,  # 85% memory usage
                comparison_type="greater_than",
                severity=AlertSeverity.WARNING,
                component="system",
                description="High memory usage (>85%)",
                cooldown_minutes=30,
            ),
            "disk_usage_high": MonitoringThreshold(
                name="disk_usage_high",
                metric_name="disk_usage_percent",
                threshold_value=90.0,  # 90% disk usage
                comparison_type="greater_than",
                severity=AlertSeverity.CRITICAL,
                component="system",
                description="High disk usage (>90%)",
                cooldown_minutes=15,
            ),
        }

        # Historical data for trend analysis
        self.historical_data: Dict[str, List[Tuple[float, float]]] = {}
        self.baseline_data: Dict[str, float] = {}

        # Alert cooldown tracking
        self.alert_cooldowns: Dict[str, float] = {}

    async def check_all_thresholds(self) -> List[ThresholdBreach]:
        """Check all configured thresholds and return breaches."""
        breaches = []

        # Check review rate spike
        review_rate_breach = await self._check_review_rate_spike()
        if review_rate_breach:
            breaches.append(review_rate_breach)

        # Check RPC error rate
        rpc_error_breach = await self._check_rpc_error_rate()
        if rpc_error_breach:
            breaches.append(rpc_error_breach)

        # Check system health
        health_breach = await self._check_system_health()
        if health_breach:
            breaches.append(health_breach)

        # Check fetch latency
        latency_breach = await self._check_fetch_latency()
        if latency_breach:
            breaches.append(latency_breach)

        # Check validation error rate
        validation_breach = await self._check_validation_error_rate()
        if validation_breach:
            breaches.append(validation_breach)

        # Check database connection failures
        db_breach = await self._check_database_connections()
        if db_breach:
            breaches.append(db_breach)

        # Check system resources
        memory_breach = await self._check_memory_usage()
        if memory_breach:
            breaches.append(memory_breach)

        disk_breach = await self._check_disk_usage()
        if disk_breach:
            breaches.append(disk_breach)

        return breaches

    async def _check_review_rate_spike(self) -> Optional[ThresholdBreach]:
        """Check for review rate spike."""
        threshold = self.thresholds["review_rate_spike"]

        # Get current review rate (mock implementation)
        current_rate = await self._get_current_review_rate()
        if current_rate is None:
            return None

        # Get baseline rate
        baseline_rate = self._get_baseline_rate(
            "review_rate_percent", current_rate
        )

        # Calculate increase percentage
        if baseline_rate > 0:
            increase_percent = (
                (current_rate - baseline_rate) / baseline_rate
            ) * 100

            if increase_percent > threshold.threshold_value:
                return ThresholdBreach(
                    rule_name=threshold.name,
                    metric_name=threshold.metric_name,
                    current_value=current_rate,
                    threshold=threshold.threshold_value,
                    severity=threshold.severity,
                    component=threshold.component,
                    timestamp=time.time(),
                    exceeded_by_percent=increase_percent,
                )

        return None

    async def _check_rpc_error_rate(self) -> Optional[ThresholdBreach]:
        """Check RPC error rate."""
        threshold = self.thresholds["rpc_error_rate"]

        # Get current RPC error rate (mock implementation)
        current_rate = await self._get_current_rpc_error_rate()
        if current_rate is None:
            return None

        if current_rate > threshold.threshold_value:
            exceeded_by = (
                (current_rate - threshold.threshold_value)
                / threshold.threshold_value
            ) * 100
            return ThresholdBreach(
                rule_name=threshold.name,
                metric_name=threshold.metric_name,
                current_value=current_rate,
                threshold=threshold.threshold_value,
                severity=threshold.severity,
                component=threshold.component,
                timestamp=time.time(),
                exceeded_by_percent=exceeded_by,
            )

        return None

    async def _check_system_health(self) -> Optional[ThresholdBreach]:
        """Check system health score."""
        threshold = self.thresholds["system_health_degradation"]

        # Get current system health (mock implementation)
        current_health = await self._get_current_system_health()
        if current_health is None:
            return None

        if current_health < threshold.threshold_value:
            exceeded_by = (
                (threshold.threshold_value - current_health)
                / threshold.threshold_value
            ) * 100
            return ThresholdBreach(
                rule_name=threshold.name,
                metric_name=threshold.metric_name,
                current_value=current_health,
                threshold=threshold.threshold_value,
                severity=threshold.severity,
                component=threshold.component,
                timestamp=time.time(),
                exceeded_by_percent=exceeded_by,
            )

        return None

    async def _check_fetch_latency(self) -> Optional[ThresholdBreach]:
        """Check fetch latency."""
        threshold = self.thresholds["fetch_latency_exceeded"]

        # Get current fetch latency (mock implementation)
        current_latency = await self._get_current_fetch_latency()
        if current_latency is None:
            return None

        if current_latency > threshold.threshold_value:
            exceeded_by = (
                (current_latency - threshold.threshold_value)
                / threshold.threshold_value
            ) * 100
            return ThresholdBreach(
                rule_name=threshold.name,
                metric_name=threshold.metric_name,
                current_value=current_latency,
                threshold=threshold.threshold_value,
                severity=threshold.severity,
                component=threshold.component,
                timestamp=time.time(),
                exceeded_by_percent=exceeded_by,
            )

        return None

    async def _check_validation_error_rate(self) -> Optional[ThresholdBreach]:
        """Check validation error rate."""
        threshold = self.thresholds["validation_error_rate"]

        # Get current validation error rate (mock implementation)
        current_rate = await self._get_current_validation_error_rate()
        if current_rate is None:
            return None

        if current_rate > threshold.threshold_value:
            exceeded_by = (
                (current_rate - threshold.threshold_value)
                / threshold.threshold_value
            ) * 100
            return ThresholdBreach(
                rule_name=threshold.name,
                metric_name=threshold.metric_name,
                current_value=current_rate,
                threshold=threshold.threshold_value,
                severity=threshold.severity,
                component=threshold.component,
                timestamp=time.time(),
                exceeded_by_percent=exceeded_by,
            )

        return None

    async def _check_database_connections(self) -> Optional[ThresholdBreach]:
        """Check database connection failures."""
        threshold = self.thresholds["database_connection_failures"]

        # Get current connection failures (mock implementation)
        current_failures = await self._get_current_database_failures()
        if current_failures is None:
            return None

        if current_failures > threshold.threshold_value:
            exceeded_by = (
                (current_failures - threshold.threshold_value)
                / threshold.threshold_value
            ) * 100
            return ThresholdBreach(
                rule_name=threshold.name,
                metric_name=threshold.metric_name,
                current_value=current_failures,
                threshold=threshold.threshold_value,
                severity=threshold.severity,
                component=threshold.component,
                timestamp=time.time(),
                exceeded_by_percent=exceeded_by,
            )

        return None

    async def _check_memory_usage(self) -> Optional[ThresholdBreach]:
        """Check memory usage."""
        threshold = self.thresholds["memory_usage_high"]

        # Get current memory usage (mock implementation)
        current_usage = await self._get_current_memory_usage()
        if current_usage is None:
            return None

        if current_usage > threshold.threshold_value:
            exceeded_by = (
                (current_usage - threshold.threshold_value)
                / threshold.threshold_value
            ) * 100
            return ThresholdBreach(
                rule_name=threshold.name,
                metric_name=threshold.metric_name,
                current_value=current_usage,
                threshold=threshold.threshold_value,
                severity=threshold.severity,
                component=threshold.component,
                timestamp=time.time(),
                exceeded_by_percent=exceeded_by,
            )

        return None

    async def _check_disk_usage(self) -> Optional[ThresholdBreach]:
        """Check disk usage."""
        threshold = self.thresholds["disk_usage_high"]

        # Get current disk usage (mock implementation)
        current_usage = await self._get_current_disk_usage()
        if current_usage is None:
            return None

        if current_usage > threshold.threshold_value:
            exceeded_by = (
                (current_usage - threshold.threshold_value)
                / threshold.threshold_value
            ) * 100
            return ThresholdBreach(
                rule_name=threshold.name,
                metric_name=threshold.metric_name,
                current_value=current_usage,
                threshold=threshold.threshold_value,
                severity=threshold.severity,
                component=threshold.component,
                timestamp=time.time(),
                exceeded_by_percent=exceeded_by,
            )

        return None

    # Mock data methods - these would typically query real metrics
    async def _get_current_review_rate(self) -> Optional[float]:
        """Get current review rate percentage."""
        # Mock implementation - would typically query database
        return 45.0

    async def _get_current_rpc_error_rate(self) -> Optional[float]:
        """Get current RPC error rate percentage."""
        # Mock implementation - would typically calculate from metrics
        return 5.0

    async def _get_current_system_health(self) -> Optional[float]:
        """Get current system health score."""
        # Mock implementation - would typically calculate from various indicators
        return 85.0

    async def _get_current_fetch_latency(self) -> Optional[float]:
        """Get current average fetch latency in seconds."""
        # Mock implementation - would typically calculate from metrics
        return 15.0

    async def _get_current_validation_error_rate(self) -> Optional[float]:
        """Get current validation error rate percentage."""
        # Mock implementation - would typically calculate from metrics
        return 8.0

    async def _get_current_database_failures(self) -> Optional[float]:
        """Get current database connection failures count."""
        # Mock implementation - would typically query database metrics
        return 2.0

    async def _get_current_memory_usage(self) -> Optional[float]:
        """Get current memory usage percentage."""
        # Mock implementation - would typically query system metrics
        return 65.0

    async def _get_current_disk_usage(self) -> Optional[float]:
        """Get current disk usage percentage."""
        # Mock implementation - would typically query system metrics
        return 45.0

    def _get_baseline_rate(
        self, metric_name: str, current_value: float
    ) -> float:
        """Get baseline rate for trend analysis."""
        if metric_name not in self.baseline_data:
            self.baseline_data[metric_name] = current_value
            return current_value

        # Update baseline with exponential moving average
        alpha = 0.1  # Smoothing factor
        self.baseline_data[metric_name] = (
            alpha * current_value
            + (1 - alpha) * self.baseline_data[metric_name]
        )

        return self.baseline_data[metric_name]

    def _is_in_cooldown(self, threshold_name: str) -> bool:
        """Check if threshold is in cooldown period."""
        if threshold_name not in self.alert_cooldowns:
            return False

        threshold = self.thresholds.get(threshold_name)
        if not threshold:
            return False

        cooldown_seconds = threshold.cooldown_minutes * 60
        return (
            time.time() - self.alert_cooldowns[threshold_name]
        ) < cooldown_seconds

    def _record_cooldown(self, threshold_name: str):
        """Record alert cooldown."""
        self.alert_cooldowns[threshold_name] = time.time()

    async def process_threshold_breaches(
        self, breaches: List[ThresholdBreach]
    ):
        """Process threshold breaches and send alerts."""
        for breach in breaches:
            # Check cooldown
            if self._is_in_cooldown(breach.rule_name):
                continue

            # Send alert
            await self.alert_service.process_threshold_breaches([breach])

            # Record cooldown
            self._record_cooldown(breach.rule_name)

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get threshold monitoring service status."""
        return {
            "thresholds_configured": len(self.thresholds),
            "active_cooldowns": len(self.alert_cooldowns),
            "baseline_metrics": len(self.baseline_data),
            "historical_data_points": sum(
                len(data) for data in self.historical_data.values()
            ),
            "thresholds": {
                name: {
                    "threshold_value": threshold.threshold_value,
                    "severity": threshold.severity.value,
                    "component": threshold.component,
                    "cooldown_minutes": threshold.cooldown_minutes,
                }
                for name, threshold in self.thresholds.items()
            },
        }
