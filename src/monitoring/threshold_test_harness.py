"""
Threshold test harness for validating alerting functionality.

This module provides comprehensive testing capabilities for monitoring
and alerting systems, including price spike detection and rate limit backoff.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch
from decimal import Decimal

from .price_job_metrics import PriceDelta, PriceJobMetrics
from .rate_limit_backoff import RateLimitBackoff, RateLimitError, CircuitBreaker
from .price_alert_service import PriceAlertService


class ThresholdTestHarness:
    """Test harness for validating alerting functionality."""
    
    def __init__(self, alert_service: PriceAlertService):
        """Initialize test harness."""
        self.alert_service = alert_service
        self.test_results = []
        self.mock_clients = {}
    
    async def test_price_spike_alert(self) -> bool:
        """Test price spike alerting functionality."""
        try:
            # Create test price delta with 60% increase (above 50% threshold)
            test_delta = PriceDelta(
                variant_id="test-variant-123",
                old_price=Decimal("25.00"),
                new_price=Decimal("40.00"),
                currency="USD",
                in_stock=True,
                roaster_id="test-roaster"
            )
            
            # Check if external mocking is already in place
            if hasattr(self.alert_service.slack_client, 'send_message') and hasattr(self.alert_service.slack_client.send_message, 'side_effect'):
                # External mocking with side_effect (for failure testing)
                await self.alert_service.check_price_spike([test_delta])
                
                # If we get here without exception, the test should fail
                self.test_results.append({
                    "test": "price_spike_alert",
                    "status": "FAIL",
                    "error": "Expected exception from mocked Slack client"
                })
                return False
            elif hasattr(self.alert_service.slack_client, 'send_message') and hasattr(self.alert_service.slack_client.send_message, 'return_value'):
                # External mocking with return_value
                await self.alert_service.check_price_spike([test_delta])
                
                # Check if the mock was called
                if hasattr(self.alert_service.slack_client.send_message, 'called') and self.alert_service.slack_client.send_message.called:
                    call_args = self.alert_service.slack_client.send_message.call_args[0][0]
                    assert "Price Spike Alert" in call_args["text"], "Alert text should contain 'Price Spike Alert'"
                    assert "60.0%" in str(call_args["attachments"]), "Alert should show 60% increase"
                    
                    self.test_results.append({
                        "test": "price_spike_alert",
                        "status": "PASS",
                        "details": "Price spike alert triggered correctly"
                    })
                    return True
                else:
                    self.test_results.append({
                        "test": "price_spike_alert",
                        "status": "FAIL",
                        "error": "Slack alert was not sent"
                    })
                    return False
            else:
                # No external mocking, use internal mocking
                with patch.object(self.alert_service.slack_client, 'send_message') as mock_send:
                    mock_send.return_value = True
                    
                    await self.alert_service.check_price_spike([test_delta])
                    
                    # Verify alert was sent
                    assert mock_send.called, "Slack alert should have been sent"
                    
                    call_args = mock_send.call_args[0][0]
                    assert "Price Spike Alert" in call_args["text"], "Alert text should contain 'Price Spike Alert'"
                    assert "60.0%" in str(call_args["attachments"]), "Alert should show 60% increase"
                    
                    self.test_results.append({
                        "test": "price_spike_alert",
                        "status": "PASS",
                        "details": "Price spike alert triggered correctly"
                    })
                    return True
                
        except Exception as e:
            self.test_results.append({
                "test": "price_spike_alert",
                "status": "FAIL",
                "error": str(e)
            })
            return False
    
    async def test_rate_limit_backoff(self) -> bool:
        """Test rate limit backoff functionality."""
        try:
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
            
            result = await backoff.execute_with_backoff(failing_operation)
            assert result == "success", "Operation should succeed after retries"
            assert call_count == 3, "Should retry twice (3 total calls)"
            
            self.test_results.append({
                "test": "rate_limit_backoff",
                "status": "PASS",
                "details": f"Backoff succeeded after {call_count} attempts"
            })
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "rate_limit_backoff",
                "status": "FAIL",
                "error": str(e)
            })
            return False
    
    async def test_circuit_breaker(self) -> bool:
        """Test circuit breaker functionality."""
        try:
            circuit_breaker = CircuitBreaker(
                failure_threshold=2,
                timeout=1,
                success_threshold=1
            )
            
            # Test normal operation
            async def success_operation():
                return "success"
            
            result = await circuit_breaker.call(success_operation)
            assert result == "success", "Normal operation should succeed"
            
            # Test failure threshold
            async def failing_operation():
                raise Exception("Test failure")
            
            # First failure
            try:
                await circuit_breaker.call(failing_operation)
                assert False, "Should have raised exception"
            except Exception:
                pass  # Expected
            
            # Second failure should open circuit
            try:
                await circuit_breaker.call(failing_operation)
                assert False, "Should have raised exception"
            except Exception:
                pass  # Expected
            
            # Circuit should now be open
            state = circuit_breaker.get_state()
            assert state["state"] == "OPEN", "Circuit should be open after failures"
            
            self.test_results.append({
                "test": "circuit_breaker",
                "status": "PASS",
                "details": "Circuit breaker opened after failure threshold"
            })
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "circuit_breaker",
                "status": "FAIL",
                "error": str(e)
            })
            return False
    
    async def test_alert_throttling(self) -> bool:
        """Test alert throttling functionality."""
        try:
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
            
            # Mock Slack client
            with patch.object(self.alert_service.slack_client, 'send_message') as mock_send:
                mock_send.return_value = True
                
                # Send all alerts
                await self.alert_service.check_price_spike(test_deltas)
                
                # Should be throttled after max_alerts_per_window
                max_alerts = self.alert_service.alert_throttle.max_alerts_per_window
                assert mock_send.call_count <= max_alerts, f"Should be throttled to {max_alerts} alerts"
                
                self.test_results.append({
                    "test": "alert_throttling",
                    "status": "PASS",
                    "details": f"Alert throttling limited to {mock_send.call_count} alerts"
                })
                return True
                
        except Exception as e:
            self.test_results.append({
                "test": "alert_throttling",
                "status": "FAIL",
                "error": str(e)
            })
            return False
    
    async def test_metrics_collection(self) -> bool:
        """Test metrics collection functionality."""
        try:
            metrics = PriceJobMetrics()
            
            # Test metrics recording
            metrics.record_price_job_duration(1.5, "test-roaster", "price_update")
            metrics.record_price_changes(5, "test-roaster", "USD")
            metrics.record_job_success("test-roaster", "price_update")
            metrics.record_job_failure("test-roaster", "price_update", "network_error")
            metrics.record_database_connections(3)
            metrics.record_rate_limit_error("database", "insert")
            metrics.record_price_spike_alert("test-roaster", "test-variant")
            metrics.record_memory_usage("price_job", 1024 * 1024)
            
            # Get metrics summary
            summary = metrics.get_metrics_summary()
            assert "prometheus_port" in summary, "Summary should include Prometheus port"
            assert "metrics_available" in summary, "Summary should include available metrics"
            
            self.test_results.append({
                "test": "metrics_collection",
                "status": "PASS",
                "details": "All metrics recorded successfully"
            })
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "metrics_collection",
                "status": "FAIL",
                "error": str(e)
            })
            return False
    
    async def test_performance_alert(self) -> bool:
        """Test performance alerting functionality."""
        try:
            # Mock Slack client
            with patch.object(self.alert_service.slack_client, 'send_message') as mock_send:
                mock_send.return_value = True
                
                # Send performance alert
                await self.alert_service.send_performance_alert(
                    metric_name="job_duration",
                    current_value=10.0,
                    threshold=5.0,
                    roaster_id="test-roaster"
                )
                
                # Verify alert was sent
                assert mock_send.called, "Performance alert should have been sent"
                
                call_args = mock_send.call_args[0][0]
                assert "Performance Alert" in call_args["text"], "Alert should be performance alert"
                assert "job_duration" in str(call_args["attachments"]), "Alert should mention metric name"
                
                self.test_results.append({
                    "test": "performance_alert",
                    "status": "PASS",
                    "details": "Performance alert sent successfully"
                })
                return True
                
        except Exception as e:
            self.test_results.append({
                "test": "performance_alert",
                "status": "FAIL",
                "error": str(e)
            })
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test scenarios."""
        print("🧪 Running B.3 Monitoring Test Harness...")
        
        test_methods = [
            ("Price Spike Alert", self.test_price_spike_alert),
            ("Rate Limit Backoff", self.test_rate_limit_backoff),
            ("Circuit Breaker", self.test_circuit_breaker),
            ("Alert Throttling", self.test_alert_throttling),
            ("Metrics Collection", self.test_metrics_collection),
            ("Performance Alert", self.test_performance_alert),
        ]
        
        results = {}
        passed = 0
        total = len(test_methods)
        
        for test_name, test_method in test_methods:
            print(f"  Testing {test_name}...")
            try:
                success = await test_method()
                results[test_name] = success
                if success:
                    passed += 1
                    print(f"    ✅ {test_name}: PASS")
                else:
                    print(f"    ❌ {test_name}: FAIL")
            except Exception as e:
                results[test_name] = False
                print(f"    ❌ {test_name}: ERROR - {e}")
        
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total) * 100,
            "results": results,
            "test_details": self.test_results
        }
        
        print(f"\n📊 Test Summary: {passed}/{total} tests passed ({summary['success_rate']:.1f}%)")
        
        return summary
    
    def get_test_results(self) -> List[Dict[str, Any]]:
        """Get detailed test results."""
        return self.test_results
