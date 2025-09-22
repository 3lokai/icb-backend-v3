"""
Tests for price job metrics collection and Prometheus export.
"""

import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from src.monitoring.price_job_metrics import PriceJobMetrics, PriceDelta


class TestPriceJobMetrics:
    """Test price job metrics collection."""
    
    def test_initialization(self):
        """Test metrics service initialization."""
        metrics = PriceJobMetrics(prometheus_port=8001)
        assert metrics.prometheus_port == 8001
    
    def test_record_price_job_duration(self):
        """Test recording price job duration."""
        metrics = PriceJobMetrics()
        metrics.record_price_job_duration(1.5, "test-roaster", "price_update")
        # Metrics are recorded to Prometheus - no direct assertion possible
    
    def test_record_price_changes(self):
        """Test recording price changes."""
        metrics = PriceJobMetrics()
        metrics.record_price_changes(5, "test-roaster", "USD")
        # Metrics are recorded to Prometheus - no direct assertion possible
    
    def test_record_job_success(self):
        """Test recording job success."""
        metrics = PriceJobMetrics()
        metrics.record_job_success("test-roaster", "price_update")
        # Metrics are recorded to Prometheus - no direct assertion possible
    
    def test_record_job_failure(self):
        """Test recording job failure."""
        metrics = PriceJobMetrics()
        metrics.record_job_failure("test-roaster", "price_update", "network_error")
        # Metrics are recorded to Prometheus - no direct assertion possible
    
    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        metrics = PriceJobMetrics()
        summary = metrics.get_metrics_summary()
        
        assert "prometheus_port" in summary
        assert "metrics_available" in summary
        assert isinstance(summary["metrics_available"], list)
        assert len(summary["metrics_available"]) > 0


class TestPriceDelta:
    """Test price delta calculations."""
    
    def test_price_delta_creation(self):
        """Test price delta creation."""
        delta = PriceDelta(
            variant_id="test-variant",
            old_price=Decimal("25.00"),
            new_price=Decimal("30.00"),
            currency="USD",
            roaster_id="test-roaster"
        )
        
        assert delta.variant_id == "test-variant"
        assert delta.old_price == Decimal("25.00")
        assert delta.new_price == Decimal("30.00")
        assert delta.currency == "USD"
        assert delta.roaster_id == "test-roaster"
    
    def test_price_change_percentage(self):
        """Test price change percentage calculation."""
        delta = PriceDelta(
            variant_id="test-variant",
            old_price=Decimal("25.00"),
            new_price=Decimal("30.00"),
            currency="USD"
        )
        
        # 30 - 25 = 5, 5/25 = 0.2 = 20%
        assert delta.price_change_percentage == 20.0
    
    def test_price_change_percentage_zero_old_price(self):
        """Test price change percentage with zero old price."""
        delta = PriceDelta(
            variant_id="test-variant",
            old_price=Decimal("0.00"),
            new_price=Decimal("30.00"),
            currency="USD"
        )
        
        assert delta.price_change_percentage == 0.0
    
    def test_is_price_spike(self):
        """Test price spike detection."""
        # 60% increase - should be spike
        delta = PriceDelta(
            variant_id="test-variant",
            old_price=Decimal("25.00"),
            new_price=Decimal("40.00"),
            currency="USD"
        )
        
        assert delta.is_price_spike(threshold=50.0) == True
        assert delta.is_price_spike(threshold=70.0) == False
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        delta = PriceDelta(
            variant_id="test-variant",
            old_price=Decimal("25.00"),
            new_price=Decimal("30.00"),
            currency="USD",
            roaster_id="test-roaster"
        )
        
        result = delta.to_dict()
        
        assert result["variant_id"] == "test-variant"
        assert result["old_price"] == 25.0
        assert result["new_price"] == 30.0
        assert result["currency"] == "USD"
        assert result["roaster_id"] == "test-roaster"
        assert result["price_change_percentage"] == 20.0
        assert "timestamp" in result
