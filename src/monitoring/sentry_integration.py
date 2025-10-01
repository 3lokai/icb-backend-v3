"""
Sentry integration for error tracking and performance monitoring.

This module provides comprehensive Sentry integration for capturing errors,
performance issues, and system anomalies in the coffee scraper.
"""

import time
from typing import Dict, Any, Optional, List
from contextlib import contextmanager


class SentryIntegration:
    """Sentry integration for error tracking and performance monitoring."""
    
    def __init__(self, dsn: str, environment: str = "production"):
        """Initialize Sentry integration."""
        self.dsn = dsn
        self.environment = environment
        self._initialize_sentry()
    
    def _initialize_sentry(self):
        """Initialize Sentry SDK with proper configuration."""
        try:
            import sentry_sdk
            from sentry_sdk.integrations.asyncio import AsyncioIntegration
            from sentry_sdk.integrations.httpx import HttpxIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            
            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                integrations=[
                    AsyncioIntegration(),
                    HttpxIntegration(),
                    SqlalchemyIntegration(),
                ],
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1,
                # Custom options
                max_breadcrumbs=50,
                attach_stacktrace=True,
                send_default_pii=False,
            )
            
            # Set global tags
            sentry_sdk.set_tag("service", "coffee-scraper")
            sentry_sdk.set_tag("component", "price-monitoring")
            
        except ImportError:
            print("Warning: Sentry SDK not available")
        except Exception as e:
            print(f"Warning: Failed to initialize Sentry: {e}")
    
    def capture_price_job_error(self, error: Exception, context: Dict[str, Any]):
        """Capture price job errors with context."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("job_type", "price_update")
                scope.set_tag("error_category", "price_job")
                scope.set_context("price_job", context)
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture price job error: {e}")
    
    def capture_performance_issue(
        self, 
        metric_name: str, 
        value: float, 
        threshold: float,
        roaster_id: str = ""
    ):
        """Capture performance issues."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("issue_type", "performance")
                scope.set_tag("metric_name", metric_name)
                scope.set_tag("roaster_id", roaster_id)
                scope.set_context("performance", {
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "roaster_id": roaster_id,
                    "exceeded_by": ((value - threshold) / threshold * 100) if threshold > 0 else 0
                })
                sentry_sdk.capture_message(
                    f"Performance threshold exceeded: {metric_name} = {value:.2f} (threshold: {threshold:.2f})",
                    level="warning"
                )
        except Exception as e:
            print(f"Failed to capture performance issue: {e}")
    
    def capture_rate_limit_error(
        self,
        service: str,
        operation: str,
        retry_count: int,
        roaster_id: str = ""
    ):
        """Capture rate limit errors."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("error_type", "rate_limit")
                scope.set_tag("service", service)
                scope.set_tag("operation", operation)
                scope.set_tag("roaster_id", roaster_id)
                scope.set_context("rate_limit", {
                    "service": service,
                    "operation": operation,
                    "retry_count": retry_count,
                    "roaster_id": roaster_id,
                    "timestamp": time.time()
                })
                sentry_sdk.capture_message(
                    f"Rate limit exceeded: {service}.{operation} (retry #{retry_count})",
                    level="warning"
                )
        except Exception as e:
            print(f"Failed to capture rate limit error: {e}")
    
    def capture_database_error(
        self,
        error: Exception,
        operation: str,
        roaster_id: str = "",
        connection_info: Dict[str, Any] = None
    ):
        """Capture database errors."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("error_type", "database")
                scope.set_tag("operation", operation)
                scope.set_tag("roaster_id", roaster_id)
                scope.set_context("database", {
                    "operation": operation,
                    "roaster_id": roaster_id,
                    "connection_info": connection_info or {},
                    "timestamp": time.time()
                })
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture database error: {e}")
    
    def capture_price_spike(
        self,
        variant_id: str,
        old_price: float,
        new_price: float,
        increase_percentage: float,
        roaster_id: str = ""
    ):
        """Capture price spike events."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("event_type", "price_spike")
                scope.set_tag("variant_id", variant_id)
                scope.set_tag("roaster_id", roaster_id)
                scope.set_context("price_spike", {
                    "variant_id": variant_id,
                    "old_price": old_price,
                    "new_price": new_price,
                    "increase_percentage": increase_percentage,
                    "roaster_id": roaster_id,
                    "timestamp": time.time()
                })
                sentry_sdk.capture_message(
                    f"Price spike detected: {variant_id} increased by {increase_percentage:.1f}%",
                    level="warning"
                )
        except Exception as e:
            print(f"Failed to capture price spike: {e}")
    
    def capture_alert_system_error(
        self,
        error: Exception,
        alert_type: str,
        roaster_id: str = ""
    ):
        """Capture alert system errors."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("error_type", "alert_system")
                scope.set_tag("alert_type", alert_type)
                scope.set_tag("roaster_id", roaster_id)
                scope.set_context("alert_system", {
                    "alert_type": alert_type,
                    "roaster_id": roaster_id,
                    "timestamp": time.time()
                })
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture alert system error: {e}")
    
    @contextmanager
    def capture_operation(self, operation_name: str, roaster_id: str = ""):
        """Context manager for capturing operation performance."""
        start_time = time.time()
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("operation", operation_name)
                scope.set_tag("roaster_id", roaster_id)
                yield
        except Exception as e:
            # Capture the exception
            try:
                import sentry_sdk
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("operation", operation_name)
                    scope.set_tag("roaster_id", roaster_id)
                    scope.set_context("operation", {
                        "name": operation_name,
                        "roaster_id": roaster_id,
                        "duration": time.time() - start_time
                    })
                    sentry_sdk.capture_exception(e)
            except Exception as capture_error:
                print(f"Failed to capture operation exception: {capture_error}")
            raise
        finally:
            # Record operation duration
            duration = time.time() - start_time
            try:
                import sentry_sdk
                sentry_sdk.add_breadcrumb(
                    message=f"Operation completed: {operation_name}",
                    category="operation",
                    data={
                        "operation": operation_name,
                        "roaster_id": roaster_id,
                        "duration": duration
                    }
                )
            except Exception as e:
                print(f"Failed to add operation breadcrumb: {e}")
    
    def set_user_context(self, user_id: str, roaster_id: str = ""):
        """Set user context for error tracking."""
        try:
            import sentry_sdk
            sentry_sdk.set_user({
                "id": user_id,
                "roaster_id": roaster_id
            })
        except Exception as e:
            print(f"Failed to set user context: {e}")
    
    def add_breadcrumb(self, message: str, category: str, data: Dict[str, Any] = None):
        """Add breadcrumb for debugging context."""
        try:
            import sentry_sdk
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                data=data or {}
            )
        except Exception as e:
            print(f"Failed to add breadcrumb: {e}")
    
    def capture_pipeline_error(
        self,
        error: Exception,
        component: str,
        operation: str,
        artifact_id: str = "",
        pipeline_state: Dict[str, Any] = None,
        user_info: Dict[str, Any] = None
    ):
        """Capture pipeline errors with comprehensive context."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", component)
                scope.set_tag("operation", operation)
                scope.set_tag("artifact_id", artifact_id)
                scope.set_tag("error_category", "pipeline")
                
                # Add pipeline context
                if pipeline_state:
                    scope.set_context("pipeline_state", pipeline_state)
                
                # Add user context
                if user_info:
                    scope.set_context("user_info", user_info)
                
                # Add artifact context
                if artifact_id:
                    scope.set_context("artifact", {
                        "id": artifact_id,
                        "component": component,
                        "operation": operation
                    })
                
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture pipeline error: {e}")
    
    def capture_normalizer_error(
        self,
        error: Exception,
        artifact_id: str,
        parser_type: str,
        validation_errors: List[str] = None,
        pipeline_state: Dict[str, Any] = None
    ):
        """Capture normalizer pipeline errors (C.1-C.8)."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "normalizer")
                scope.set_tag("parser_type", parser_type)
                scope.set_tag("artifact_id", artifact_id)
                scope.set_tag("error_category", "normalizer")
                
                # Add validation context
                if validation_errors:
                    scope.set_context("validation_errors", {
                        "errors": validation_errors,
                        "count": len(validation_errors)
                    })
                
                # Add pipeline state
                if pipeline_state:
                    scope.set_context("pipeline_state", pipeline_state)
                
                # Add artifact context
                scope.set_context("artifact", {
                    "id": artifact_id,
                    "parser_type": parser_type,
                    "component": "normalizer"
                })
                
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture normalizer error: {e}")
    
    def capture_llm_error(
        self,
        error: Exception,
        artifact_id: str,
        llm_provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0
    ):
        """Capture LLM enrichment errors (D.1-D.2)."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "llm_enrichment")
                scope.set_tag("llm_provider", llm_provider)
                scope.set_tag("model", model)
                scope.set_tag("artifact_id", artifact_id)
                scope.set_tag("error_category", "llm")
                
                # Add LLM context
                scope.set_context("llm_usage", {
                    "provider": llm_provider,
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cost": cost,
                    "total_tokens": prompt_tokens + completion_tokens
                })
                
                # Add artifact context
                scope.set_context("artifact", {
                    "id": artifact_id,
                    "component": "llm_enrichment"
                })
                
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture LLM error: {e}")
    
    def capture_image_error(
        self,
        error: Exception,
        artifact_id: str,
        image_url: str,
        operation: str,
        image_size: int = 0,
        processing_time: float = 0.0
    ):
        """Capture image handling errors (F.1-F.3)."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "image_handling")
                scope.set_tag("operation", operation)
                scope.set_tag("artifact_id", artifact_id)
                scope.set_tag("error_category", "image")
                
                # Add image context
                scope.set_context("image_info", {
                    "url": image_url,
                    "size_bytes": image_size,
                    "processing_time": processing_time,
                    "operation": operation
                })
                
                # Add artifact context
                scope.set_context("artifact", {
                    "id": artifact_id,
                    "component": "image_handling"
                })
                
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture image error: {e}")
    
    def capture_fetcher_error(
        self,
        error: Exception,
        source: str,
        platform: str,
        operation: str,
        roaster_id: str = "",
        retry_count: int = 0
    ):
        """Capture fetcher errors (A.1-A.5)."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "fetcher")
                scope.set_tag("source", source)
                scope.set_tag("platform", platform)
                scope.set_tag("operation", operation)
                scope.set_tag("roaster_id", roaster_id)
                scope.set_tag("error_category", "fetcher")
                
                # Add fetcher context
                scope.set_context("fetcher_info", {
                    "source": source,
                    "platform": platform,
                    "operation": operation,
                    "roaster_id": roaster_id,
                    "retry_count": retry_count,
                    "timestamp": time.time()
                })
                
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture fetcher error: {e}")
    
    def capture_system_failure(
        self,
        error: Exception,
        component: str,
        failure_type: str,
        system_state: Dict[str, Any] = None
    ):
        """Capture critical system failures."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", component)
                scope.set_tag("failure_type", failure_type)
                scope.set_tag("severity", "critical")
                scope.set_tag("error_category", "system_failure")
                
                # Add system state
                if system_state:
                    scope.set_context("system_state", system_state)
                
                # Add failure context
                scope.set_context("failure_info", {
                    "component": component,
                    "failure_type": failure_type,
                    "timestamp": time.time()
                })
                
                sentry_sdk.capture_exception(error)
        except Exception as e:
            print(f"Failed to capture system failure: {e}")
    
    def capture_threshold_breach(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        component: str,
        severity: str = "warning"
    ):
        """Capture threshold breach events."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("event_type", "threshold_breach")
                scope.set_tag("metric_name", metric_name)
                scope.set_tag("component", component)
                scope.set_tag("severity", severity)
                
                # Add threshold context
                scope.set_context("threshold_breach", {
                    "metric_name": metric_name,
                    "current_value": current_value,
                    "threshold": threshold,
                    "exceeded_by": ((current_value - threshold) / threshold * 100) if threshold > 0 else 0,
                    "component": component,
                    "timestamp": time.time()
                })
                
                sentry_sdk.capture_message(
                    f"Threshold breach: {metric_name} = {current_value:.2f} (threshold: {threshold:.2f})",
                    level=severity
                )
        except Exception as e:
            print(f"Failed to capture threshold breach: {e}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get Sentry integration status."""
        try:
            import sentry_sdk
            return {
                "sentry_available": True,
                "dsn_configured": bool(self.dsn),
                "environment": self.environment,
                "integrations": [
                    "AsyncioIntegration",
                    "HttpxIntegration", 
                    "SqlalchemyIntegration"
                ],
                "error_capture_methods": [
                    "capture_pipeline_error",
                    "capture_normalizer_error", 
                    "capture_llm_error",
                    "capture_image_error",
                    "capture_fetcher_error",
                    "capture_system_failure",
                    "capture_threshold_breach"
                ]
            }
        except ImportError:
            return {
                "sentry_available": False,
                "dsn_configured": bool(self.dsn),
                "environment": self.environment,
                "error": "Sentry SDK not available"
            }
        except Exception as e:
            return {
                "sentry_available": False,
                "dsn_configured": bool(self.dsn),
                "environment": self.environment,
                "error": str(e)
            }
