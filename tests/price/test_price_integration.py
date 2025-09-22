"""
Integration tests for B.1 → B.2 price update pipeline.
Tests end-to-end price update flow with mocked database operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from src.price.price_update_service import PriceUpdateService
from src.price.variant_update_service import VariantUpdateService
from src.fetcher.price_parser import PriceDelta, PriceParser
from src.fetcher.price_fetcher import PriceFetcher


class TestPriceIntegration:
    """Integration tests for B.1 → B.2 price update pipeline."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return Mock()
    
    @pytest.fixture
    def mock_rpc_client(self):
        """Mock RPC client."""
        mock_client = Mock()
        # Make insert_price return unique IDs
        price_id_counter = 0
        def mock_insert_price(*args, **kwargs):
            nonlocal price_id_counter
            price_id_counter += 1
            return f"price_{price_id_counter}"
        mock_client.insert_price.side_effect = mock_insert_price
        
        # Make batch_update_variant_pricing return correct counts
        def mock_batch_update_variant_pricing(*args, **kwargs):
            # Count the number of variants being updated
            variant_updates = len(args[0]) if args else 0
            return {
                'total_updates': variant_updates,
                'successful_updates': variant_updates,
                'failed_updates': 0,
                'errors': []
            }
        mock_client.batch_update_variant_pricing.side_effect = mock_batch_update_variant_pricing
        return mock_client
    
    @pytest.fixture
    def price_update_service(self, mock_supabase_client, mock_rpc_client):
        """Price update service with mocked dependencies."""
        return PriceUpdateService(
            supabase_client=mock_supabase_client,
            rpc_client=mock_rpc_client
        )
    
    @pytest.fixture
    def variant_update_service(self, mock_supabase_client, mock_rpc_client):
        """Variant update service with mocked dependencies."""
        return VariantUpdateService(
            supabase_client=mock_supabase_client,
            rpc_client=mock_rpc_client
        )
    
    @pytest.fixture
    def sample_price_deltas(self):
        """Sample price deltas from B.1 price fetcher."""
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
    async def test_b1_to_b2_price_update_pipeline(self, price_update_service, sample_price_deltas):
        """Test complete B.1 → B.2 price update pipeline."""
        # Simulate B.1 price fetcher output
        price_deltas = sample_price_deltas
        
        # B.2: Process price deltas through update service
        result = await price_update_service.update_prices_atomic(price_deltas)
        
        # Verify successful processing
        assert result.success is True
        assert len(result.price_ids) == 2
        assert result.variant_updates == 2
        assert result.errors == []
        
        # Verify RPC operations were called
        assert price_update_service.rpc_client.insert_price.call_count == 2
        assert price_update_service.rpc_client.batch_update_variant_pricing.call_count == 1
        
        # Verify price record insertion calls
        insert_calls = price_update_service.rpc_client.insert_price.call_args_list
        assert insert_calls[0][1]['variant_id'] == "variant_1"
        assert insert_calls[0][1]['price'] == 24.99
        assert insert_calls[1][1]['variant_id'] == "variant_2"
        assert insert_calls[1][1]['price'] == 15.99
    
    @pytest.mark.asyncio
    async def test_price_update_with_currency_validation(self, price_update_service):
        """Test price update with currency validation."""
        price_deltas = [
            PriceDelta(
                variant_id="variant_1",
                old_price=Decimal("19.99"),
                new_price=Decimal("24.99"),
                currency="EUR",  # Different currency
                in_stock=True,
                sku="SKU001"
            )
        ]
        
        result = await price_update_service.update_prices_atomic(price_deltas)
        
        assert result.success is True
        assert len(result.price_ids) == 1
        
        # Verify currency was passed correctly
        insert_call = price_update_service.rpc_client.insert_price.call_args[1]
        assert insert_call['currency'] == "EUR"
    
    @pytest.mark.asyncio
    async def test_price_update_with_availability_changes(self, price_update_service):
        """Test price update with availability changes."""
        price_deltas = [
            PriceDelta(
                variant_id="variant_1",
                old_price=Decimal("19.99"),
                new_price=Decimal("19.99"),  # Same price
                currency="USD",
                in_stock=False,  # Availability changed
                sku="SKU001"
            )
        ]
        
        result = await price_update_service.update_prices_atomic(price_deltas)
        
        assert result.success is True
        assert len(result.price_ids) == 1
        assert result.variant_updates == 1
        
        # Verify variant update included availability
        batch_call = price_update_service.rpc_client.batch_update_variant_pricing.call_args[0][0]
        assert batch_call[0]['in_stock'] is False
    
    @pytest.mark.asyncio
    async def test_price_update_rollback_scenario(self, price_update_service):  
        """Test price update rollback scenario."""
        # Mock RPC client to fail on variant updates
        def mock_batch_update_variant_pricing(*args, **kwargs):
            return {
                'total_updates': 1,
                'successful_updates': 0,
                'failed_updates': 1,
                'errors': ['Variant update failed']
            }
        price_update_service.rpc_client.batch_update_variant_pricing.side_effect = mock_batch_update_variant_pricing

        price_deltas = [
            PriceDelta(
                variant_id="variant_1",
                old_price=Decimal("19.99"),
                new_price=Decimal("24.99"),
                currency="USD",
                in_stock=True,
                sku="SKU001"
            )
        ]

        result = await price_update_service.update_prices_atomic(price_deltas)  

        # Should still succeed as we don't implement rollback in this version   
        # (This would be enhanced in a production system)
        assert result.success is True
        assert len(result.price_ids) == 1
        assert result.variant_updates == 0  # Failed variant updates
    
    @pytest.mark.asyncio
    async def test_batch_price_update_performance(self, price_update_service):
        """Test batch price update performance."""
        # Create larger batch of price deltas
        price_deltas = []
        for i in range(50):  # 50 variants
            price_deltas.append(
                PriceDelta(
                    variant_id=f"variant_{i}",
                    old_price=Decimal("19.99"),
                    new_price=Decimal("24.99"),
                    currency="USD",
                    in_stock=True,
                    sku=f"SKU{i:03d}"
                )
            )
        
        result = await price_update_service.update_prices_atomic(price_deltas)
        
        assert result.success is True
        assert len(result.price_ids) == 50
        assert result.variant_updates == 50
        
        # Verify all RPC operations were called
        assert price_update_service.rpc_client.insert_price.call_count == 50
        assert price_update_service.rpc_client.batch_update_variant_pricing.call_count == 1
        
        # Verify performance metrics
        stats = price_update_service.get_update_stats()
        assert stats['total_updates'] == 50
        assert stats['successful_updates'] == 50
        assert stats['price_records_inserted'] == 50
        assert stats['variant_records_updated'] == 50
    
    @pytest.mark.asyncio
    async def test_price_update_error_handling(self, price_update_service):
        """Test price update error handling."""
        # Mock RPC client to fail on price insertion
        price_update_service.rpc_client.insert_price.side_effect = Exception("Database connection failed")
        
        price_deltas = [
            PriceDelta(
                variant_id="variant_1",
                old_price=Decimal("19.99"),
                new_price=Decimal("24.99"),
                currency="USD",
                in_stock=True,
                sku="SKU001"
            )
        ]
        
        result = await price_update_service.update_prices_atomic(price_deltas)
        
        assert result.success is False
        assert len(result.price_ids) == 0
        assert len(result.errors) == 1
        assert "Failed to insert any price records" in result.errors[0]
    
    def test_price_update_service_initialization(self, mock_supabase_client, mock_rpc_client):
        """Test price update service initialization."""
        service = PriceUpdateService(
            supabase_client=mock_supabase_client,
            rpc_client=mock_rpc_client
        )
        
        assert service.supabase_client == mock_supabase_client
        assert service.rpc_client == mock_rpc_client
        assert service.database_integration is not None
        
        # Verify initial stats
        stats = service.get_update_stats()
        assert stats['total_updates'] == 0
        assert stats['successful_updates'] == 0
        assert stats['failed_updates'] == 0
    
    def test_variant_update_service_initialization(self, mock_supabase_client, mock_rpc_client):
        """Test variant update service initialization."""
        service = VariantUpdateService(
            supabase_client=mock_supabase_client,
            rpc_client=mock_rpc_client
        )
        
        assert service.supabase_client == mock_supabase_client
        assert service.rpc_client == mock_rpc_client
        assert service.database_integration is not None
        
        # Verify initial stats
        stats = service.get_variant_stats()
        assert stats['total_updates'] == 0
        assert stats['successful_updates'] == 0
        assert stats['failed_updates'] == 0
