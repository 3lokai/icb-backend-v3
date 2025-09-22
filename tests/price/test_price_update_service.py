"""
Tests for PriceUpdateService - atomic price updates with mocked database operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from src.price.price_update_service import PriceUpdateService, PriceUpdateResult
from src.fetcher.price_parser import PriceDelta


class TestPriceUpdateService:
    """Test cases for PriceUpdateService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return Mock()
    
    @pytest.fixture
    def mock_rpc_client(self):
        """Mock RPC client."""
        mock_client = Mock()
        mock_client.insert_price.return_value = "price_123"
        mock_client.batch_update_variant_pricing.return_value = {
            'total_updates': 2,
            'successful_updates': 2,
            'failed_updates': 0,
            'errors': []
        }
        return mock_client
    
    @pytest.fixture
    def price_update_service(self, mock_supabase_client, mock_rpc_client):
        """Price update service with mocked dependencies."""
        return PriceUpdateService(
            supabase_client=mock_supabase_client,
            rpc_client=mock_rpc_client
        )
    
    @pytest.fixture
    def sample_price_deltas(self):
        """Sample price deltas for testing."""
        return [
            PriceDelta(
                variant_id="variant_1",
                old_price=Decimal("19.99"),
                new_price=Decimal("24.99"),
                currency="USD",
                in_stock=True,
                sku="SKU001"
            ),
            PriceDelta(
                variant_id="variant_2",
                old_price=None,
                new_price=Decimal("15.99"),
                currency="USD",
                in_stock=False,
                sku="SKU002"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_update_prices_atomic_success(self, price_update_service, sample_price_deltas):
        """Test successful atomic price update."""
        result = await price_update_service.update_prices_atomic(sample_price_deltas)
        
        assert result.success is True
        assert len(result.price_ids) == 2
        assert result.variant_updates == 2
        assert result.errors == []
        assert result.processing_time_seconds > 0
        
        # Verify RPC client was called correctly
        assert price_update_service.rpc_client.insert_price.call_count == 2
        assert price_update_service.rpc_client.batch_update_variant_pricing.call_count == 1
    
    @pytest.mark.asyncio
    async def test_update_prices_atomic_no_deltas(self, price_update_service):
        """Test atomic price update with no deltas."""
        result = await price_update_service.update_prices_atomic([])
        
        assert result.success is False
        assert "Failed to insert any price records" in result.errors
    
    @pytest.mark.asyncio
    async def test_update_prices_atomic_rpc_failure(self, price_update_service, sample_price_deltas):
        """Test atomic price update with RPC failure."""
        # Mock RPC client to raise exception
        price_update_service.rpc_client.insert_price.side_effect = Exception("RPC Error")
        
        result = await price_update_service.update_prices_atomic(sample_price_deltas)
        
        assert result.success is False
        assert "Failed to insert any price records" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_insert_price_records_success(self, price_update_service, sample_price_deltas):
        """Test successful price record insertion."""
        price_ids = await price_update_service._insert_price_records(sample_price_deltas)
        
        assert len(price_ids) == 2
        assert price_ids == ["price_123", "price_123"]
        
        # Verify RPC calls
        assert price_update_service.rpc_client.insert_price.call_count == 2
    
    @pytest.mark.asyncio
    async def test_insert_price_records_partial_failure(self, price_update_service, sample_price_deltas):
        """Test price record insertion with partial failure."""
        # Mock RPC client to fail on second call
        price_update_service.rpc_client.insert_price.side_effect = [
            "price_123",  # First call succeeds
            Exception("RPC Error")  # Second call fails
        ]
        
        price_ids = await price_update_service._insert_price_records(sample_price_deltas)
        
        assert len(price_ids) == 1
        assert price_ids == ["price_123"]
    
    @pytest.mark.asyncio
    async def test_update_variant_pricing_success(self, price_update_service, sample_price_deltas):
        """Test successful variant pricing update."""
        variant_updates = await price_update_service._update_variant_pricing(sample_price_deltas)
        
        assert variant_updates == 2
        
        # Verify batch update was called
        assert price_update_service.rpc_client.batch_update_variant_pricing.call_count == 1
        
        # Verify the batch update data
        call_args = price_update_service.rpc_client.batch_update_variant_pricing.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]['variant_id'] == "variant_1"
        assert call_args[1]['variant_id'] == "variant_2"
    
    @pytest.mark.asyncio
    async def test_update_variant_pricing_no_deltas(self, price_update_service):
        """Test variant pricing update with no deltas."""
        variant_updates = await price_update_service._update_variant_pricing([])
        
        assert variant_updates == 0
        assert price_update_service.rpc_client.batch_update_variant_pricing.call_count == 0
    
    def test_get_update_stats(self, price_update_service):
        """Test getting update statistics."""
        # Set some test stats
        price_update_service.update_stats = {
            'total_updates': 10,
            'successful_updates': 8,
            'failed_updates': 2,
            'price_records_inserted': 8,
            'variant_records_updated': 8,
            'start_time': datetime.now(timezone.utc),
            'end_time': datetime.now(timezone.utc)
        }
        
        stats = price_update_service.get_update_stats()
        
        assert stats['total_updates'] == 10
        assert stats['successful_updates'] == 8
        assert stats['failed_updates'] == 2
        assert stats['success_rate'] == 0.8
        assert stats['failure_rate'] == 0.2
        assert 'total_processing_time' in stats
    
    def test_reset_stats(self, price_update_service):
        """Test resetting statistics."""
        # Set some test stats
        price_update_service.update_stats = {
            'total_updates': 10,
            'successful_updates': 8,
            'failed_updates': 2,
            'price_records_inserted': 8,
            'variant_records_updated': 8,
            'start_time': datetime.now(timezone.utc),
            'end_time': datetime.now(timezone.utc)
        }
        
        price_update_service.reset_stats()
        
        stats = price_update_service.get_update_stats()
        assert stats['total_updates'] == 0
        assert stats['successful_updates'] == 0
        assert stats['failed_updates'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['failure_rate'] == 0.0


class TestPriceUpdateResult:
    """Test cases for PriceUpdateResult dataclass."""
    
    def test_price_update_result_defaults(self):
        """Test PriceUpdateResult with default values."""
        result = PriceUpdateResult(success=True)
        
        assert result.success is True
        assert result.price_ids == []
        assert result.variant_updates == 0
        assert result.errors == []
        assert result.processing_time_seconds == 0.0
    
    def test_price_update_result_with_values(self):
        """Test PriceUpdateResult with specific values."""
        result = PriceUpdateResult(
            success=False,
            price_ids=["price_1", "price_2"],
            variant_updates=2,
            errors=["Error 1", "Error 2"],
            processing_time_seconds=1.5
        )
        
        assert result.success is False
        assert result.price_ids == ["price_1", "price_2"]
        assert result.variant_updates == 2
        assert result.errors == ["Error 1", "Error 2"]
        assert result.processing_time_seconds == 1.5
