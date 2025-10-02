"""
Test execution monitoring and alerting system.

This module provides real-time monitoring, alerting, and reporting
for test execution with performance metrics and health indicators.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock, patch

import pytest

# Set up logger
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TestExecutionMetrics:
    """Metrics for test execution monitoring."""
    test_name: str
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Test execution alert."""
    level: AlertLevel
    message: str
    test_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestHealthStatus:
    """Overall test health status."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    success_rate: float
    average_execution_time: float
    total_execution_time: float
    health_score: float  # 0-100


class TestExecutionMonitor:
    """Real-time test execution monitoring."""
    
    def __init__(self):
        self.active_tests: Dict[str, TestExecutionMetrics] = {}
        self.completed_tests: List[TestExecutionMetrics] = []
        self.alerts: List[Alert] = []
        self.monitoring_active = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    async def start_monitoring(self):
        """Start test execution monitoring."""
        self.monitoring_active = True
        self.start_time = datetime.now()
        logger.info("Test execution monitoring started")
    
    async def stop_monitoring(self):
        """Stop test execution monitoring."""
        self.monitoring_active = False
        self.end_time = datetime.now()
        logger.info("Test execution monitoring stopped")
    
    async def start_test(self, test_name: str) -> TestExecutionMetrics:
        """Start monitoring a test."""
        if not self.monitoring_active:
            raise RuntimeError("Monitoring not active")
        
        metrics = TestExecutionMetrics(
            test_name=test_name,
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        
        self.active_tests[test_name] = metrics
        logger.info(f"Started monitoring test: {test_name}")
        
        return metrics
    
    async def update_test_status(self, test_name: str, status: TestStatus, 
                                error_message: Optional[str] = None,
                                performance_metrics: Optional[Dict[str, Any]] = None):
        """Update test status and complete monitoring."""
        if test_name not in self.active_tests:
            logger.warning(f"Test {test_name} not found in active tests")
            return
        
        metrics = self.active_tests[test_name]
        metrics.status = status
        metrics.end_time = datetime.now()
        metrics.execution_time = (metrics.end_time - metrics.start_time).total_seconds()
        
        if error_message:
            metrics.error_message = error_message
        
        if performance_metrics:
            metrics.performance_metrics = performance_metrics
        
        # Move to completed tests
        self.completed_tests.append(metrics)
        del self.active_tests[test_name]
        
        # Check for alerts
        await self._check_test_alerts(metrics)
        
        logger.info(f"Test {test_name} completed with status: {status.value}")
    
    async def _check_test_alerts(self, metrics: TestExecutionMetrics):
        """Check for alerts based on test metrics."""
        # Alert for failed tests
        if metrics.status == TestStatus.FAILED:
            alert = Alert(
                level=AlertLevel.ERROR,
                message=f"Test {metrics.test_name} failed",
                test_name=metrics.test_name,
                metadata={'error_message': metrics.error_message}
            )
            self.alerts.append(alert)
        
        # Alert for long-running tests
        if metrics.execution_time > 60.0:  # 1 minute threshold
            alert = Alert(
                level=AlertLevel.WARNING,
                message=f"Test {metrics.test_name} took {metrics.execution_time:.2f}s",
                test_name=metrics.test_name,
                metadata={'execution_time': metrics.execution_time}
            )
            self.alerts.append(alert)
        
        # Alert for high memory usage
        if metrics.memory_usage > 500.0:  # 500MB threshold
            alert = Alert(
                level=AlertLevel.WARNING,
                message=f"Test {metrics.test_name} used {metrics.memory_usage:.2f}MB memory",
                test_name=metrics.test_name,
                metadata={'memory_usage': metrics.memory_usage}
            )
            self.alerts.append(alert)
    
    def get_test_health_status(self) -> TestHealthStatus:
        """Get overall test health status."""
        total_tests = len(self.completed_tests)
        passed_tests = len([t for t in self.completed_tests if t.status == TestStatus.PASSED])
        failed_tests = len([t for t in self.completed_tests if t.status == TestStatus.FAILED])
        skipped_tests = len([t for t in self.completed_tests if t.status == TestStatus.SKIPPED])
        error_tests = len([t for t in self.completed_tests if t.status == TestStatus.ERROR])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        average_execution_time = sum(t.execution_time for t in self.completed_tests) / total_tests if total_tests > 0 else 0
        total_execution_time = sum(t.execution_time for t in self.completed_tests)
        
        # Calculate health score (0-100)
        health_score = success_rate * 0.7  # 70% weight on success rate
        if average_execution_time < 30.0:  # Bonus for fast tests
            health_score += 10
        if len(self.alerts) == 0:  # Bonus for no alerts
            health_score += 20
        
        health_score = min(100, max(0, health_score))
        
        return TestHealthStatus(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            error_tests=error_tests,
            success_rate=success_rate,
            average_execution_time=average_execution_time,
            total_execution_time=total_execution_time,
            health_score=health_score
        )
    
    def get_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """Get alerts, optionally filtered by level."""
        if level:
            return [alert for alert in self.alerts if alert.level == level]
        return self.alerts
    
    def get_active_tests(self) -> List[str]:
        """Get list of currently active test names."""
        return list(self.active_tests.keys())
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get monitoring summary."""
        health_status = self.get_test_health_status()
        
        return {
            'monitoring_active': self.monitoring_active,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'active_tests_count': len(self.active_tests),
            'completed_tests_count': len(self.completed_tests),
            'alerts_count': len(self.alerts),
            'health_status': {
                'total_tests': health_status.total_tests,
                'success_rate': health_status.success_rate,
                'health_score': health_status.health_score
            }
        }


class TestAlertingSystem:
    """Test failure alerting and notification system."""
    
    def __init__(self, monitor: TestExecutionMonitor):
        self.monitor = monitor
        self.notification_channels = []
        self.alert_thresholds = {
            'failure_rate': 10.0,  # 10% failure rate threshold
            'execution_time': 300.0,  # 5 minutes execution time threshold
            'memory_usage': 1024.0,  # 1GB memory usage threshold
            'health_score': 70.0  # 70% health score threshold
        }
    
    async def check_alert_conditions(self):
        """Check for alert conditions and send notifications."""
        health_status = self.monitor.get_test_health_status()
        
        # Check failure rate threshold
        if health_status.success_rate < (100 - self.alert_thresholds['failure_rate']):
            await self._send_alert(
                AlertLevel.ERROR,
                f"High failure rate: {100 - health_status.success_rate:.1f}%",
                {'failure_rate': 100 - health_status.success_rate}
            )
        
        # Check execution time threshold
        if health_status.total_execution_time > self.alert_thresholds['execution_time']:
            await self._send_alert(
                AlertLevel.WARNING,
                f"Long execution time: {health_status.total_execution_time:.1f}s",
                {'execution_time': health_status.total_execution_time}
            )
        
        # Check health score threshold
        if health_status.health_score < self.alert_thresholds['health_score']:
            await self._send_alert(
                AlertLevel.WARNING,
                f"Low health score: {health_status.health_score:.1f}%",
                {'health_score': health_status.health_score}
            )
    
    async def _send_alert(self, level: AlertLevel, message: str, metadata: Dict[str, Any]):
        """Send alert notification."""
        alert = Alert(
            level=level,
            message=message,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        self.monitor.alerts.append(alert)
        
        # Send to notification channels
        for channel in self.notification_channels:
            await channel.send_notification(alert)
        
        logger.warning(f"Alert sent: {level.value} - {message}")


class TestDashboard:
    """Test execution dashboard and reporting."""
    
    def __init__(self, monitor: TestExecutionMonitor):
        self.monitor = monitor
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate dashboard data."""
        health_status = self.monitor.get_test_health_status()
        active_tests = self.monitor.get_active_tests()
        alerts = self.monitor.get_alerts()
        
        return {
            'overview': {
                'total_tests': health_status.total_tests,
                'active_tests': len(active_tests),
                'success_rate': health_status.success_rate,
                'health_score': health_status.health_score,
                'total_alerts': len(alerts)
            },
            'test_status': {
                'passed': health_status.passed_tests,
                'failed': health_status.failed_tests,
                'skipped': health_status.skipped_tests,
                'error': health_status.error_tests
            },
            'performance': {
                'average_execution_time': health_status.average_execution_time,
                'total_execution_time': health_status.total_execution_time
            },
            'alerts': [
                {
                    'level': alert.level.value,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'test_name': alert.test_name
                }
                for alert in alerts[-10:]  # Last 10 alerts
            ],
            'active_tests': active_tests
        }
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        health_status = self.monitor.get_test_health_status()
        completed_tests = self.monitor.completed_tests
        alerts = self.monitor.get_alerts()
        
        # Group tests by status
        tests_by_status = {}
        for test in completed_tests:
            status = test.status.value
            if status not in tests_by_status:
                tests_by_status[status] = []
            tests_by_status[status].append({
                'name': test.test_name,
                'execution_time': test.execution_time,
                'error_message': test.error_message
            })
        
        return {
            'summary': {
                'total_tests': health_status.total_tests,
                'success_rate': health_status.success_rate,
                'health_score': health_status.health_score,
                'total_execution_time': health_status.total_execution_time,
                'average_execution_time': health_status.average_execution_time
            },
            'test_results': tests_by_status,
            'alerts': [
                {
                    'level': alert.level.value,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'test_name': alert.test_name,
                    'metadata': alert.metadata
                }
                for alert in alerts
            ],
            'performance_metrics': {
                'fastest_test': min([t.execution_time for t in completed_tests], default=0),
                'slowest_test': max([t.execution_time for t in completed_tests], default=0),
                'total_memory_usage': sum([t.memory_usage for t in completed_tests]),
                'average_memory_usage': sum([t.memory_usage for t in completed_tests]) / len(completed_tests) if completed_tests else 0
            }
        }


# Test cases for test execution monitoring
class TestTestExecutionMonitoring:
    """Test cases for test execution monitoring."""
    
    @pytest.fixture
    def test_monitor(self):
        """Test execution monitor fixture."""
        return TestExecutionMonitor()
    
    @pytest.fixture
    def alerting_system(self, test_monitor):
        """Test alerting system fixture."""
        return TestAlertingSystem(test_monitor)
    
    @pytest.fixture
    def test_dashboard(self, test_monitor):
        """Test dashboard fixture."""
        return TestDashboard(test_monitor)
    
    @pytest.mark.asyncio
    async def test_monitoring_start_stop(self, test_monitor):
        """Test monitoring start and stop."""
        assert not test_monitor.monitoring_active
        
        await test_monitor.start_monitoring()
        assert test_monitor.monitoring_active
        assert test_monitor.start_time is not None
        
        await test_monitor.stop_monitoring()
        assert not test_monitor.monitoring_active
        assert test_monitor.end_time is not None
    
    @pytest.mark.asyncio
    async def test_test_execution_monitoring(self, test_monitor):
        """Test test execution monitoring."""
        await test_monitor.start_monitoring()
        
        # Start a test
        metrics = await test_monitor.start_test("test_example")
        assert metrics.test_name == "test_example"
        assert metrics.status == TestStatus.RUNNING
        assert "test_example" in test_monitor.active_tests
        
        # Update test status
        await test_monitor.update_test_status("test_example", TestStatus.PASSED)
        assert "test_example" not in test_monitor.active_tests
        assert len(test_monitor.completed_tests) == 1
        
        await test_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, test_monitor):
        """Test alert generation for failed tests."""
        await test_monitor.start_monitoring()
        
        # Start and fail a test
        await test_monitor.start_test("failing_test")
        await test_monitor.update_test_status("failing_test", TestStatus.FAILED, "Test failed")
        
        # Check for alerts
        alerts = test_monitor.get_alerts()
        assert len(alerts) > 0
        assert any(alert.level == AlertLevel.ERROR for alert in alerts)
        
        await test_monitor.stop_monitoring()
    
    def test_health_status_calculation(self, test_monitor):
        """Test health status calculation."""
        # Add some completed tests
        test_monitor.completed_tests = [
            TestExecutionMetrics("test1", TestStatus.PASSED, datetime.now(), datetime.now(), 10.0),
            TestExecutionMetrics("test2", TestStatus.PASSED, datetime.now(), datetime.now(), 15.0),
            TestExecutionMetrics("test3", TestStatus.FAILED, datetime.now(), datetime.now(), 5.0)
        ]
        
        health_status = test_monitor.get_test_health_status()
        
        assert health_status.total_tests == 3
        assert health_status.passed_tests == 2
        assert health_status.failed_tests == 1
        assert abs(health_status.success_rate - 66.67) < 0.01
        assert health_status.health_score > 0
    
    @pytest.mark.asyncio
    async def test_alerting_system(self, alerting_system):
        """Test alerting system functionality."""
        # Add some failed tests to trigger alerts
        alerting_system.monitor.completed_tests = [
            TestExecutionMetrics("test1", TestStatus.FAILED, datetime.now(), datetime.now(), 10.0),
            TestExecutionMetrics("test2", TestStatus.FAILED, datetime.now(), datetime.now(), 15.0),
            TestExecutionMetrics("test3", TestStatus.FAILED, datetime.now(), datetime.now(), 5.0)
        ]
        
        await alerting_system.check_alert_conditions()
        
        alerts = alerting_system.monitor.get_alerts()
        assert len(alerts) > 0
        assert any(alert.level == AlertLevel.ERROR for alert in alerts)
    
    def test_dashboard_data_generation(self, test_dashboard):
        """Test dashboard data generation."""
        # Add some test data
        test_dashboard.monitor.completed_tests = [
            TestExecutionMetrics("test1", TestStatus.PASSED, datetime.now(), datetime.now(), 10.0),
            TestExecutionMetrics("test2", TestStatus.FAILED, datetime.now(), datetime.now(), 15.0)
        ]
        
        dashboard_data = test_dashboard.generate_dashboard_data()
        
        assert 'overview' in dashboard_data
        assert 'test_status' in dashboard_data
        assert 'performance' in dashboard_data
        assert 'alerts' in dashboard_data
        assert dashboard_data['overview']['total_tests'] == 2
    
    def test_test_report_generation(self, test_dashboard):
        """Test test report generation."""
        # Add some test data
        test_dashboard.monitor.completed_tests = [
            TestExecutionMetrics("test1", TestStatus.PASSED, datetime.now(), datetime.now(), 10.0),
            TestExecutionMetrics("test2", TestStatus.FAILED, datetime.now(), datetime.now(), 15.0)
        ]
        
        report = test_dashboard.generate_test_report()
        
        assert 'summary' in report
        assert 'test_results' in report
        assert 'alerts' in report
        assert 'performance_metrics' in report
        assert report['summary']['total_tests'] == 2


if __name__ == "__main__":
    # Run test execution monitoring tests
    pytest.main([__file__, "-v"])
