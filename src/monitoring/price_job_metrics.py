"""
Price job metrics collection and Prometheus export.

This module provides comprehensive metrics collection for price job operations,
including job duration, success rates, price changes, and database performance.
"""

import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from decimal import Decimal

# Prometheus metrics
price_job_duration = Histogram(
    'price_job_duration_seconds', 
    'Price job execution time',
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

price_changes_count = Counter(
    'price_changes_total', 
    'Total price changes detected',
    ['roaster_id', 'currency']
)

price_job_success = Counter(
    'price_job_success_total', 
    'Successful price jobs',
    ['roaster_id', 'job_type']
)

price_job_failures = Counter(
    'price_job_failures_total', 
    'Failed price jobs',
    ['roaster_id', 'job_type', 'error_type']
)

database_connections = Gauge(
    'database_connections_active', 
    'Active database connections'
)

rate_limit_errors = Counter(
    'rate_limit_errors_total', 
    'Rate limit errors encountered',
    ['service', 'operation']
)

price_spike_alerts = Counter(
    'price_spike_alerts_total',
    'Price spike alerts triggered',
    ['roaster_id', 'variant_id']
)

memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    ['component']
)


class PriceJobMetrics:
    """Metrics collection service for price job operations."""
    
    def __init__(self, prometheus_port: int = 8000):
        """Initialize metrics service with Prometheus export."""
        self.prometheus_port = prometheus_port
        self._start_prometheus_server()
    
    def _start_prometheus_server(self):
        """Start Prometheus metrics server."""
        try:
            start_http_server(self.prometheus_port)
        except Exception as e:
            # Log error but don't fail initialization
            print(f"Warning: Could not start Prometheus server on port {self.prometheus_port}: {e}")
    
    def record_price_job_duration(self, duration: float, roaster_id: str, job_type: str = "price_update"):
        """Record price job execution duration."""
        price_job_duration.observe(duration)
    
    def record_price_changes(self, count: int, roaster_id: str, currency: str = "USD"):
        """Record price changes detected."""
        price_changes_count.labels(roaster_id=roaster_id, currency=currency).inc(count)
    
    def record_job_success(self, roaster_id: str, job_type: str = "price_update"):
        """Record successful price job completion."""
        price_job_success.labels(roaster_id=roaster_id, job_type=job_type).inc()
    
    def record_job_failure(self, roaster_id: str, job_type: str, error_type: str):
        """Record failed price job with error classification."""
        price_job_failures.labels(
            roaster_id=roaster_id, 
            job_type=job_type, 
            error_type=error_type
        ).inc()
    
    def record_database_connections(self, active_connections: int):
        """Record active database connections."""
        database_connections.set(active_connections)
    
    def record_rate_limit_error(self, service: str, operation: str):
        """Record rate limit error."""
        rate_limit_errors.labels(service=service, operation=operation).inc()
    
    def record_price_spike_alert(self, roaster_id: str, variant_id: str):
        """Record price spike alert triggered."""
        price_spike_alerts.labels(roaster_id=roaster_id, variant_id=variant_id).inc()
    
    def record_memory_usage(self, component: str, bytes_used: int):
        """Record memory usage for component."""
        memory_usage.labels(component=component).set(bytes_used)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary for monitoring dashboards."""
        return {
            "prometheus_port": self.prometheus_port,
            "metrics_available": [
                "price_job_duration_seconds",
                "price_changes_total", 
                "price_job_success_total",
                "price_job_failures_total",
                "database_connections_active",
                "rate_limit_errors_total",
                "price_spike_alerts_total",
                "memory_usage_bytes"
            ]
        }


class PriceDelta:
    """Price change delta for monitoring and alerting."""
    
    def __init__(
        self,
        variant_id: str,
        old_price: Decimal,
        new_price: Decimal,
        currency: str = "USD",
        in_stock: bool = True,
        roaster_id: str = ""
    ):
        self.variant_id = variant_id
        self.old_price = old_price
        self.new_price = new_price
        self.currency = currency
        self.in_stock = in_stock
        self.roaster_id = roaster_id
        self.timestamp = time.time()
    
    @property
    def price_change_percentage(self) -> float:
        """Calculate price change percentage."""
        if self.old_price == 0:
            return 0.0
        
        return float(((self.new_price - self.old_price) / self.old_price) * 100)
    
    def is_price_spike(self, threshold: float = 50.0) -> bool:
        """Check if price change constitutes a spike."""
        return self.price_change_percentage > threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "variant_id": self.variant_id,
            "old_price": float(self.old_price),
            "new_price": float(self.new_price),
            "currency": self.currency,
            "in_stock": self.in_stock,
            "roaster_id": self.roaster_id,
            "price_change_percentage": self.price_change_percentage,
            "timestamp": self.timestamp
        }
