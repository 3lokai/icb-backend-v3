"""
Tests for PlatformFetcherService - platform-based fetcher selection and cascade logic.

Tests the core functionality of Story A.6: Platform-Based Fetcher Selection with Automatic Fallback.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from src.fetcher.platform_fetcher_service import PlatformFetcherService, FetcherResult
from src.config.roaster_schema import RoasterConfigSchema
from src.config.fetcher_config import FetcherJobConfig
from src.config.firecrawl_config import FirecrawlConfig

# Simple FetcherConfig for testing
from dataclasses import dataclass

@dataclass
class FetcherConfig:
    """Simple fetcher configuration for testing."""
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    politeness_delay: float = 0.25
    jitter_range: float = 0.1
    max_concurrent: int = 3


class TestPlatformFetcherService:
    """Test cases for PlatformFetcherService."""
    
    @pytest.fixture
    def roaster_config(self):
        """Create a test roaster configuration."""
        return RoasterConfigSchema(
            id="test-roaster",
            name="Test Roaster",
            base_url="https://test-roaster.com",
            platform="shopify",
            use_firecrawl_fallback=True,
            firecrawl_budget_limit=10
        )
    
    @pytest.fixture
    def fetcher_config(self):
        """Create a test fetcher configuration."""
        return FetcherConfig(
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
            politeness_delay=0.25,
            jitter_range=0.1,
            max_concurrent=3
        )
    
    @pytest.fixture
    def firecrawl_config(self):
        """Create a test Firecrawl configuration."""
        return FirecrawlConfig(
            api_key="test-api-key",
            base_url="https://api.firecrawl.dev",
            budget_limit=10,
            max_pages=50,
            include_subdomains=False,
            sitemap_only=False,
            coffee_keywords=["coffee", "beans", "roast"],
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
            enable_monitoring=True,
            log_level="INFO"
        )
    
    @pytest.fixture
    def platform_service(self, roaster_config, fetcher_config, firecrawl_config):
        """Create a PlatformFetcherService instance."""
        return PlatformFetcherService(
            roaster_config=roaster_config,
            fetcher_config=fetcher_config,
            firecrawl_config=firecrawl_config
        )
    
    def test_initialization(self, platform_service, roaster_config, fetcher_config, firecrawl_config):
        """Test service initialization."""
        assert platform_service.roaster_config == roaster_config
        assert platform_service.fetcher_config == fetcher_config
        assert platform_service.firecrawl_config == firecrawl_config
        assert platform_service.shopify_fetcher is None
        assert platform_service.woocommerce_fetcher is None
    
    def test_get_fetcher_sequence_known_platform(self, platform_service):
        """Test fetcher sequence for known platform."""
        sequence = platform_service._get_fetcher_sequence()
        assert len(sequence) == 3
        assert sequence[0][0] == "shopify"
        assert sequence[1][0] == "woocommerce"
        assert sequence[2][0] == "firecrawl"
    
    def test_get_fetcher_sequence_unknown_platform(self, platform_service):
        """Test fetcher sequence for unknown platform."""
        sequence = platform_service._get_fetcher_sequence()
        assert len(sequence) == 3
        assert sequence[0][0] == "shopify"
        assert sequence[1][0] == "woocommerce"
        assert sequence[2][0] == "firecrawl"
    
    def test_get_fetcher_sequence_none_platform(self, platform_service):
        """Test fetcher sequence for None platform."""
        sequence = platform_service._get_fetcher_sequence()
        assert len(sequence) == 3
        assert sequence[0][0] == "shopify"
        assert sequence[1][0] == "woocommerce"
        assert sequence[2][0] == "firecrawl"
    
    @pytest.mark.asyncio
    async def test_fetch_products_with_cascade_shopify_success(self, platform_service):
        """Test successful Shopify fetcher cascade."""
        # Mock Shopify fetcher success
        mock_shopify_fetcher = AsyncMock()
        mock_shopify_fetcher.fetch_products.return_value = FetcherResult(
            success=True,
            products=[{"id": "1", "name": "Test Coffee"}],
            platform="shopify",
            should_update_platform=True,
            error=None
        )
        
        with patch.object(platform_service, '_get_shopify_fetcher', return_value=mock_shopify_fetcher):
            result = await platform_service.fetch_products_with_cascade("full_refresh")
            
            assert result.success is True
            assert result.platform == "shopify"
            assert result.should_update_platform is True
            assert len(result.products) == 1
            assert result.products[0]["name"] == "Test Coffee"
    
    @pytest.mark.asyncio
    async def test_fetch_products_with_cascade_shopify_fail_woocommerce_success(self, platform_service):
        """Test Shopify failure with WooCommerce success."""
        # Mock Shopify fetcher failure
        mock_shopify_fetcher = AsyncMock()
        mock_shopify_fetcher.fetch_products.return_value = FetcherResult(
            success=False,
            products=[],
            platform="shopify",
            should_update_platform=False,
            error="Shopify API error"
        )
        
        # Mock WooCommerce fetcher success
        mock_woocommerce_fetcher = AsyncMock()
        mock_woocommerce_fetcher.fetch_products.return_value = FetcherResult(
            success=True,
            products=[{"id": "2", "name": "WooCommerce Coffee"}],
            platform="woocommerce",
            should_update_platform=True,
            error=None
        )
        
        with patch.object(platform_service, '_get_shopify_fetcher', return_value=mock_shopify_fetcher), \
             patch.object(platform_service, '_get_woocommerce_fetcher', return_value=mock_woocommerce_fetcher):
            
            result = await platform_service.fetch_products_with_cascade("full_refresh")
            
            assert result.success is True
            assert result.platform == "woocommerce"
            assert result.should_update_platform is True
            assert len(result.products) == 1
            assert result.products[0]["name"] == "WooCommerce Coffee"
    
    @pytest.mark.asyncio
    async def test_fetch_products_with_cascade_all_standard_fail_firecrawl_success(self, platform_service):
        """Test all standard fetchers fail but Firecrawl succeeds."""
        # Mock both standard fetchers to fail
        mock_shopify_fetcher = AsyncMock()
        mock_shopify_fetcher.fetch_products.return_value = FetcherResult(
            success=False,
            products=[],
            platform="shopify",
            should_update_platform=False,
            error="Shopify API error"
        )
        
        mock_woocommerce_fetcher = AsyncMock()
        mock_woocommerce_fetcher.fetch_products.return_value = FetcherResult(
            success=False,
            products=[],
            platform="woocommerce",
            should_update_platform=False,
            error="WooCommerce API error"
        )
        
        # Mock Firecrawl fallback success
        with patch.object(platform_service, '_get_shopify_fetcher', return_value=mock_shopify_fetcher), \
             patch.object(platform_service, '_get_woocommerce_fetcher', return_value=mock_woocommerce_fetcher), \
             patch.object(platform_service, '_trigger_firecrawl_fallback') as mock_firecrawl:
            
            mock_firecrawl.return_value = FetcherResult(
                success=True,
                products=[{"url": "https://test-roaster.com/coffee", "source": "firecrawl_fallback"}],
                platform="firecrawl",
                should_update_platform=False,
                error=None
            )
            
            result = await platform_service.fetch_products_with_cascade("full_refresh")
            
            assert result.success is True
            assert result.platform == "firecrawl"
            assert result.should_update_platform is False
            assert len(result.products) == 1
            assert result.products[0]["source"] == "firecrawl_fallback"
    
    @pytest.mark.asyncio
    async def test_fetch_products_with_cascade_all_fail(self, platform_service):
        """Test all fetchers fail including Firecrawl."""
        # Mock all fetchers to fail
        mock_shopify_fetcher = AsyncMock()
        mock_shopify_fetcher.fetch_products.return_value = FetcherResult(
            success=False,
            products=[],
            platform="shopify",
            should_update_platform=False,
            error="Shopify API error"
        )
        
        mock_woocommerce_fetcher = AsyncMock()
        mock_woocommerce_fetcher.fetch_products.return_value = FetcherResult(
            success=False,
            products=[],
            platform="woocommerce",
            should_update_platform=False,
            error="WooCommerce API error"
        )
        
        with patch.object(platform_service, '_get_shopify_fetcher', return_value=mock_shopify_fetcher), \
             patch.object(platform_service, '_get_woocommerce_fetcher', return_value=mock_woocommerce_fetcher), \
             patch.object(platform_service, '_trigger_firecrawl_fallback') as mock_firecrawl:
            
            mock_firecrawl.return_value = FetcherResult(
                success=False,
                products=[],
                platform="firecrawl",
                should_update_platform=False,
                error="Firecrawl API error"
            )
            
            result = await platform_service.fetch_products_with_cascade("full_refresh")
            
            assert result.success is False
            assert "All fetchers failed including Firecrawl" in result.error
    
    @pytest.mark.asyncio
    async def test_trigger_firecrawl_fallback(self, platform_service):
        """Test Firecrawl fallback triggering."""
        with patch('src.worker.tasks.execute_firecrawl_map_job') as mock_execute:
            mock_execute.return_value = {
                'status': 'completed',
                'discovered_urls': ['https://test-roaster.com/coffee1', 'https://test-roaster.com/coffee2'],
                'processed_at': '2025-01-02T10:00:00Z'
            }
            
            result = await platform_service._trigger_firecrawl_fallback("full_refresh", search_terms=["coffee"])
            
            assert result.success is True
            assert result.platform == "firecrawl"
            assert result.should_update_platform is False
            assert len(result.products) == 2
            assert result.products[0]["url"] == "https://test-roaster.com/coffee1"
            assert result.products[0]["source"] == "firecrawl_fallback"
    
    @pytest.mark.asyncio
    async def test_trigger_firecrawl_fallback_failure(self, platform_service):
        """Test Firecrawl fallback failure."""
        with patch('src.worker.tasks.execute_firecrawl_map_job') as mock_execute:
            mock_execute.return_value = {
                'status': 'failed',
                'error': 'Firecrawl API error'
            }
            
            result = await platform_service._trigger_firecrawl_fallback("full_refresh")
            
            assert result.success is False
            assert result.platform == "firecrawl"
            assert result.should_update_platform is False
            assert "Firecrawl fallback failed" in result.error
    
    @pytest.mark.asyncio
    async def test_close_cleanup(self, platform_service):
        """Test service cleanup on close."""
        # Mock fetchers
        mock_shopify_fetcher = AsyncMock()
        mock_woocommerce_fetcher = AsyncMock()
        
        platform_service.shopify_fetcher = mock_shopify_fetcher
        platform_service.woocommerce_fetcher = mock_woocommerce_fetcher
        
        await platform_service.close()
        
        mock_shopify_fetcher.close.assert_called_once()
        mock_woocommerce_fetcher.close.assert_called_once()
    
    def test_fetcher_result_creation(self):
        """Test FetcherResult creation and properties."""
        # Test successful result
        success_result = FetcherResult(
            success=True,
            products=[{"id": "1", "name": "Test"}],
            platform="shopify",
            should_update_platform=True,
            error=None
        )
        
        assert success_result.success is True
        assert success_result.platform == "shopify"
        assert success_result.should_update_platform is True
        assert len(success_result.products) == 1
        assert success_result.error is None
        
        # Test failed result
        failed_result = FetcherResult(
            success=False,
            products=[],
            platform="unknown",
            should_update_platform=False,
            error="Test error"
        )
        
        assert failed_result.success is False
        assert failed_result.platform == "unknown"
        assert failed_result.should_update_platform is False
        assert len(failed_result.products) == 0
        assert failed_result.error == "Test error"


class TestPlatformFetcherServiceIntegration:
    """Integration tests for PlatformFetcherService."""
    
    @pytest.mark.asyncio
    async def test_platform_detection_workflow(self):
        """Test the complete platform detection workflow."""
        roaster_config = RoasterConfigSchema(
            id="integration-test-roaster",
            name="Integration Test Roaster",
            base_url="https://integration-test.com",
            platform=None,  # Unknown platform
            use_firecrawl_fallback=True,
            firecrawl_budget_limit=10
        )
        
        fetcher_config = FetcherConfig(
            timeout=5.0,  # Short timeout for testing
            max_retries=1,
            retry_delay=0.1,
            politeness_delay=0.1,
            jitter_range=0.05,
            max_concurrent=1
        )
        
        firecrawl_config = FirecrawlConfig(
            api_key="test-api-key-12345",  # Longer key to pass validation
            base_url="https://api.firecrawl.dev",
            budget_limit=10,
            max_pages=10,
            include_subdomains=False,
            sitemap_only=False,
            coffee_keywords=["coffee"],
            timeout=5.0,
            max_retries=1,
            retry_delay=0.1,
            enable_monitoring=False,
            log_level="ERROR"
        )
        
        service = PlatformFetcherService(
            roaster_config=roaster_config,
            fetcher_config=fetcher_config,
            firecrawl_config=firecrawl_config
        )
        
        try:
            # Test with mocked fetchers to avoid real API calls
            with patch.object(service, '_get_shopify_fetcher') as mock_shopify, \
                 patch.object(service, '_get_woocommerce_fetcher') as mock_woocommerce, \
                 patch.object(service, '_trigger_firecrawl_fallback') as mock_firecrawl:
                
                # Mock Shopify failure
                mock_shopify_fetcher = AsyncMock()
                mock_shopify_fetcher.fetch_products.return_value = FetcherResult(
                    success=False,
                    products=[],
                    platform="shopify",
                    should_update_platform=False,
                    error="Shopify not available"
                )
                mock_shopify.return_value = mock_shopify_fetcher
                
                # Mock WooCommerce failure
                mock_woocommerce_fetcher = AsyncMock()
                mock_woocommerce_fetcher.fetch_products.return_value = FetcherResult(
                    success=False,
                    products=[],
                    platform="woocommerce",
                    should_update_platform=False,
                    error="WooCommerce not available"
                )
                mock_woocommerce.return_value = mock_woocommerce_fetcher
                
                # Mock Firecrawl success
                mock_firecrawl.return_value = FetcherResult(
                    success=True,
                    products=[{"url": "https://integration-test.com/coffee", "source": "firecrawl_fallback"}],
                    platform="firecrawl",
                    should_update_platform=False,
                    error=None
                )
                
                result = await service.fetch_products_with_cascade("full_refresh")
                
                assert result.success is True
                assert result.platform == "firecrawl"
                assert result.should_update_platform is False
                assert len(result.products) == 1
                
        finally:
            await service.close()
