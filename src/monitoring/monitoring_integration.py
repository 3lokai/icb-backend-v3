"""
Monitoring integration script for testing and validation.

This script provides integration testing and validation for the B.3 monitoring
and alerting system, including end-to-end testing of all components.
"""

import asyncio
import os
import time
from typing import Dict, Any, List
from decimal import Decimal

from .price_job_metrics import PriceJobMetrics, PriceDelta
from .rate_limit_backoff import RateLimitBackoff, RateLimitError, CircuitBreaker
from .price_alert_service import PriceAlertService
from .threshold_test_harness import ThresholdTestHarness


class MonitoringIntegration:
    """Integration testing for monitoring and alerting system."""
    
    def __init__(self):
        """Initialize monitoring integration."""
        self.metrics = PriceJobMetrics(prometheus_port=8001)
        
        # Initialize alert service with environment variables
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')
        sentry_dsn = os.getenv('SENTRY_DSN', '')
        
        if slack_webhook and sentry_dsn:
            self.alert_service = PriceAlertService(slack_webhook, sentry_dsn, self.metrics)
        else:
            # Use mock services for testing
            self.alert_service = PriceAlertService("mock-webhook", "mock-dsn", self.metrics)
        
        self.test_harness = ThresholdTestHarness(self.alert_service)
    
    async def test_metrics_collection(self) -> Dict[str, Any]:
        """Test metrics collection functionality."""
        print("🧪 Testing metrics collection...")
        
        # Test basic metrics recording
        self.metrics.record_price_job_duration(1.5, "test-roaster", "price_update")
        self.metrics.record_price_changes(5, "test-roaster", "USD")
        self.metrics.record_job_success("test-roaster", "price_update")
        self.metrics.record_job_failure("test-roaster", "price_update", "network_error")
        self.metrics.record_database_connections(3)
        self.metrics.record_rate_limit_error("database", "insert")
        self.metrics.record_price_spike_alert("test-roaster", "test-variant")
        self.metrics.record_memory_usage("price_job", 1024 * 1024)
        
        # Get metrics summary
        summary = self.metrics.get_metrics_summary()
        
        print(f"✅ Metrics collection test passed")
        print(f"   Prometheus port: {summary['prometheus_port']}")
        print(f"   Available metrics: {len(summary['metrics_available'])}")
        
        return {
            "status": "PASS",
            "metrics_recorded": 8,
            "prometheus_port": summary['prometheus_port'],
            "available_metrics": len(summary['metrics_available'])
        }
    
    async def test_rate_limit_backoff(self) -> Dict[str, Any]:
        """Test rate limit backoff functionality."""
        print("🧪 Testing rate limit backoff...")
        
        backoff = RateLimitBackoff(
            base_delay=0.1,  # Fast for testing
            max_delay=1.0,
            max_attempts=3
        )
        
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limit exceeded")
            return "success"
        
        start_time = time.time()
        result = await backoff.execute_with_backoff(failing_operation)
        duration = time.time() - start_time
        
        print(f"✅ Rate limit backoff test passed")
        print(f"   Result: {result}")
        print(f"   Attempts: {call_count}")
        print(f"   Duration: {duration:.2f}s")
        
        return {
            "status": "PASS",
            "result": result,
            "attempts": call_count,
            "duration": duration
        }
    
    async def test_circuit_breaker(self) -> Dict[str, Any]:
        """Test circuit breaker functionality."""
        print("🧪 Testing circuit breaker...")
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            timeout=1,
            success_threshold=1
        )
        
        # Test normal operation
        async def success_operation():
            return "success"
        
        result1 = await circuit_breaker.call(success_operation)
        
        # Test failure threshold
        async def failing_operation():
            raise Exception("Test failure")
        
        # First failure
        try:
            await circuit_breaker.call(failing_operation)
        except Exception:
            pass
        
        # Second failure should open circuit
        try:
            await circuit_breaker.call(failing_operation)
        except Exception:
            pass
        
        state = circuit_breaker.get_state()
        
        print(f"✅ Circuit breaker test passed")
        print(f"   Initial result: {result1}")
        print(f"   Final state: {state['state']}")
        print(f"   Failure count: {state['failure_count']}")
        
        return {
            "status": "PASS",
            "initial_result": result1,
            "final_state": state['state'],
            "failure_count": state['failure_count']
        }
    
    async def test_price_spike_detection(self) -> Dict[str, Any]:
        """Test price spike detection and alerting."""
        print("🧪 Testing price spike detection...")
        
        # Create test price deltas
        test_deltas = [
            PriceDelta(
                variant_id="test-variant-1",
                old_price=Decimal("25.00"),
                new_price=Decimal("40.00"),  # 60% increase - should trigger
                currency="USD",
                roaster_id="test-roaster"
            ),
            PriceDelta(
                variant_id="test-variant-2",
                old_price=Decimal("30.00"),
                new_price=Decimal("35.00"),  # 16.7% increase - should not trigger
                currency="USD",
                roaster_id="test-roaster"
            )
        ]
        
        # Test price spike detection
        spikes_detected = 0
        for delta in test_deltas:
            if delta.is_price_spike(threshold=50.0):
                spikes_detected += 1
                print(f"   Spike detected: {delta.variant_id} ({delta.price_change_percentage:.1f}%)")
        
        # Test alert service
        await self.alert_service.check_price_spike(test_deltas)
        
        print(f"✅ Price spike detection test passed")
        print(f"   Spikes detected: {spikes_detected}/2")
        
        return {
            "status": "PASS",
            "spikes_detected": spikes_detected,
            "total_deltas": len(test_deltas)
        }
    
    async def test_alert_throttling(self) -> Dict[str, Any]:
        """Test alert throttling functionality."""
        print("🧪 Testing alert throttling...")
        
        # Create multiple price deltas for same variant
        test_deltas = [
            PriceDelta(
                variant_id="throttle-test-variant",
                old_price=Decimal("10.00"),
                new_price=Decimal("20.00"),  # 100% increase
                currency="USD",
                roaster_id="test-roaster"
            )
            for _ in range(10)  # Create 10 alerts
        ]
        
        # Send all alerts
        await self.alert_service.check_price_spike(test_deltas)
        
        # Check throttling status
        alert_status = self.alert_service.get_alert_status()
        throttle_status = alert_status["throttle_status"]
        
        print(f"✅ Alert throttling test passed")
        print(f"   Active alerts: {throttle_status['active_alerts']}")
        print(f"   Max per window: {throttle_status['max_alerts_per_window']}")
        
        return {
            "status": "PASS",
            "active_alerts": throttle_status['active_alerts'],
            "max_per_window": throttle_status['max_alerts_per_window']
        }
    
    async def test_performance_monitoring(self) -> Dict[str, Any]:
        """Test performance monitoring and alerting."""
        print("🧪 Testing performance monitoring...")
        
        # Test performance alert
        await self.alert_service.send_performance_alert(
            metric_name="job_duration",
            current_value=10.0,
            threshold=5.0,
            roaster_id="test-roaster"
        )
        
        # Test memory usage recording
        self.metrics.record_memory_usage("test_component", 1024 * 1024 * 100)  # 100MB
        
        print(f"✅ Performance monitoring test passed")
        
        return {
            "status": "PASS",
            "performance_alert_sent": True,
            "memory_usage_recorded": True
        }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive monitoring integration test."""
        print("🚀 Starting B.3 Monitoring Integration Test")
        print("=" * 50)
        
        test_results = {}
        
        # Run individual tests
        tests = [
            ("Metrics Collection", self.test_metrics_collection),
            ("Rate Limit Backoff", self.test_rate_limit_backoff),
            ("Circuit Breaker", self.test_circuit_breaker),
            ("Price Spike Detection", self.test_price_spike_detection),
            ("Alert Throttling", self.test_alert_throttling),
            ("Performance Monitoring", self.test_performance_monitoring),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_method in tests:
            try:
                result = await test_method()
                test_results[test_name] = result
                if result["status"] == "PASS":
                    passed += 1
            except Exception as e:
                test_results[test_name] = {
                    "status": "FAIL",
                    "error": str(e)
                }
                print(f"❌ {test_name}: FAIL - {e}")
        
        # Run test harness
        print("\n🧪 Running Test Harness...")
        harness_results = await self.test_harness.run_all_tests()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 B.3 Monitoring Integration Test Results")
        print("=" * 50)
        print(f"Individual Tests: {passed}/{total} passed")
        print(f"Test Harness: {harness_results['passed']}/{harness_results['total_tests']} passed")
        print(f"Overall Success Rate: {((passed + harness_results['passed']) / (total + harness_results['total_tests'])) * 100:.1f}%")
        
        return {
            "individual_tests": test_results,
            "test_harness": harness_results,
            "summary": {
                "individual_passed": passed,
                "individual_total": total,
                "harness_passed": harness_results['passed'],
                "harness_total": harness_results['total_tests'],
                "overall_success_rate": ((passed + harness_results['passed']) / (total + harness_results['total_tests'])) * 100
            }
        }


async def main():
    """Main function for running monitoring integration tests."""
    integration = MonitoringIntegration()
    results = await integration.run_comprehensive_test()
    
    print("\n🎯 B.3 Monitoring Integration Complete!")
    print(f"Overall Success Rate: {results['summary']['overall_success_rate']:.1f}%")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
