"""
Tests for VariantUpdateService - variant record updates with mocked database operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from src.price.variant_update_service import VariantUpdateService


class TestVariantUpdateService:
    """Test cases for VariantUpdateService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return Mock()
    
    @pytest.fixture
    def mock_rpc_client(self):
        """Mock RPC client."""
        mock_client = Mock()
        mock_client.update_variant_pricing.return_value = True
        mock_client.batch_update_variant_pricing.return_value = {
            'total_updates': 2,
            'successful_updates': 2,
            'failed_updates': 0,
            'errors': []
        }
        return mock_client
    
    @pytest.fixture
    def variant_update_service(self, mock_supabase_client, mock_rpc_client):
        """Variant update service with mocked dependencies."""
        return VariantUpdateService(
            supabase_client=mock_supabase_client,
            rpc_client=mock_rpc_client
        )
    
    @pytest.mark.asyncio
    async def test_update_variant_pricing_success(self, variant_update_service):
        """Test successful variant pricing update."""
        variant_id = "variant_123"
        new_price = Decimal("24.99")
        currency = "USD"
        in_stock = True
        scraped_at = datetime.now(timezone.utc)
        
        result = await variant_update_service.update_variant_pricing(
            variant_id=variant_id,
            new_price=new_price,
            currency=currency,
            in_stock=in_stock,
            scraped_at=scraped_at
        )
        
        assert result is True
        
        # Verify RPC client was called correctly
        variant_update_service.rpc_client.update_variant_pricing.assert_called_once_with(
            variant_id=variant_id,
            price_current=24.99,
            price_last_checked_at=scraped_at.isoformat(),
            in_stock=in_stock,
            currency=currency
        )
        
        # Verify stats were updated
        stats = variant_update_service.get_variant_stats()
        assert stats['total_updates'] == 1
        assert stats['successful_updates'] == 1
        assert stats['failed_updates'] == 0
    
    @pytest.mark.asyncio
    async def test_update_variant_pricing_failure(self, variant_update_service):
        """Test variant pricing update failure."""
        # Mock RPC client to return False
        variant_update_service.rpc_client.update_variant_pricing.return_value = False
        
        variant_id = "variant_123"
        new_price = Decimal("24.99")
        currency = "USD"
        in_stock = True
        scraped_at = datetime.now(timezone.utc)
        
        result = await variant_update_service.update_variant_pricing(
            variant_id=variant_id,
            new_price=new_price,
            currency=currency,
            in_stock=in_stock,
            scraped_at=scraped_at
        )
        
        assert result is False
        
        # Verify stats were updated
        stats = variant_update_service.get_variant_stats()
        assert stats['total_updates'] == 1
        assert stats['successful_updates'] == 0
        assert stats['failed_updates'] == 1
    
    @pytest.mark.asyncio
    async def test_update_variant_pricing_exception(self, variant_update_service):
        """Test variant pricing update with exception."""
        # Mock RPC client to raise exception
        variant_update_service.rpc_client.update_variant_pricing.side_effect = Exception("RPC Error")
        
        variant_id = "variant_123"
        new_price = Decimal("24.99")
        currency = "USD"
        in_stock = True
        scraped_at = datetime.now(timezone.utc)
        
        result = await variant_update_service.update_variant_pricing(
            variant_id=variant_id,
            new_price=new_price,
            currency=currency,
            in_stock=in_stock,
            scraped_at=scraped_at
        )
        
        assert result is False
        
        # Verify stats were updated
        stats = variant_update_service.get_variant_stats()
        assert stats['total_updates'] == 1
        assert stats['successful_updates'] == 0
        assert stats['failed_updates'] == 1
    
    @pytest.mark.asyncio
    async def test_batch_update_variant_pricing_success(self, variant_update_service):
        """Test successful batch variant pricing update."""
        variant_updates = [
            {
                'variant_id': 'variant_1',
                'price_current': 19.99,
                'price_last_checked_at': '2025-01-12T10:00:00Z',
                'in_stock': True,
                'currency': 'USD'
            },
            {
                'variant_id': 'variant_2',
                'price_current': 24.99,
                'price_last_checked_at': '2025-01-12T10:00:00Z',
                'in_stock': False,
                'currency': 'USD'
            }
        ]
        
        result = await variant_update_service.batch_update_variant_pricing(variant_updates)
        
        assert result['total_updates'] == 2
        assert result['successful_updates'] == 2
        assert result['failed_updates'] == 0
        assert result['errors'] == []
        assert 'processing_time_seconds' in result
        
        # Verify RPC client was called
        variant_update_service.rpc_client.batch_update_variant_pricing.assert_called_once_with(variant_updates)
        
        # Verify stats were updated
        stats = variant_update_service.get_variant_stats()
        assert stats['total_updates'] == 2
        assert stats['successful_updates'] == 2
        assert stats['failed_updates'] == 0
    
    @pytest.mark.asyncio
    async def test_batch_update_variant_pricing_failure(self, variant_update_service):
        """Test batch variant pricing update with failure."""
        # Mock RPC client to raise exception
        variant_update_service.rpc_client.batch_update_variant_pricing.side_effect = Exception("Batch Error")
        
        variant_updates = [
            {
                'variant_id': 'variant_1',
                'price_current': 19.99,
                'in_stock': True
            }
        ]
        
        result = await variant_update_service.batch_update_variant_pricing(variant_updates)
        
        assert result['total_updates'] == 1
        assert result['successful_updates'] == 0
        assert result['failed_updates'] == 1
        assert len(result['errors']) == 1
        assert "Batch variant update failed" in result['errors'][0]
        
        # Verify stats were updated
        stats = variant_update_service.get_variant_stats()
        assert stats['total_updates'] == 1
        assert stats['successful_updates'] == 0
        assert stats['failed_updates'] == 1
    
    @pytest.mark.asyncio
    async def test_update_variant_availability_success(self, variant_update_service):
        """Test successful variant availability update."""
        variant_id = "variant_123"
        in_stock = False
        stock_qty = 5
        
        result = await variant_update_service.update_variant_availability(
            variant_id=variant_id,
            in_stock=in_stock,
            stock_qty=stock_qty
        )
        
        assert result is True
        
        # Verify RPC client was called correctly
        variant_update_service.rpc_client.update_variant_pricing.assert_called_once_with(
            variant_id=variant_id,
            in_stock=in_stock,
            stock_qty=stock_qty
        )
        
        # Verify stats were updated
        stats = variant_update_service.get_variant_stats()
        assert stats['total_updates'] == 1
        assert stats['successful_updates'] == 1
        assert stats['failed_updates'] == 0
    
    @pytest.mark.asyncio
    async def test_update_variant_availability_failure(self, variant_update_service):
        """Test variant availability update failure."""
        # Mock RPC client to return False
        variant_update_service.rpc_client.update_variant_pricing.return_value = False
        
        variant_id = "variant_123"
        in_stock = False
        
        result = await variant_update_service.update_variant_availability(
            variant_id=variant_id,
            in_stock=in_stock
        )
        
        assert result is False
        
        # Verify stats were updated
        stats = variant_update_service.get_variant_stats()
        assert stats['total_updates'] == 1
        assert stats['successful_updates'] == 0
        assert stats['failed_updates'] == 1
    
    def test_get_variant_stats(self, variant_update_service):
        """Test getting variant statistics."""
        # Set some test stats
        variant_update_service.variant_stats = {
            'total_updates': 10,
            'successful_updates': 8,
            'failed_updates': 2,
            'start_time': datetime.now(timezone.utc),
            'end_time': datetime.now(timezone.utc)
        }
        
        stats = variant_update_service.get_variant_stats()
        
        assert stats['total_updates'] == 10
        assert stats['successful_updates'] == 8
        assert stats['failed_updates'] == 2
        assert stats['success_rate'] == 0.8
        assert stats['failure_rate'] == 0.2
        assert 'total_processing_time' in stats
    
    def test_reset_stats(self, variant_update_service):
        """Test resetting statistics."""
        # Set some test stats
        variant_update_service.variant_stats = {
            'total_updates': 10,
            'successful_updates': 8,
            'failed_updates': 2,
            'start_time': datetime.now(timezone.utc),
            'end_time': datetime.now(timezone.utc)
        }
        
        variant_update_service.reset_stats()
        
        stats = variant_update_service.get_variant_stats()
        assert stats['total_updates'] == 0
        assert stats['successful_updates'] == 0
        assert stats['failed_updates'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['failure_rate'] == 0.0
