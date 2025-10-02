"""
End-to-end integration tests for platform-based fetcher selection.

Tests the complete workflow for Story A.6: Platform-Based Fetcher Selection with Automatic Fallback.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from src.worker.tasks import execute_scraping_job
from src.fetcher.platform_fetcher_service import PlatformFetcherService
from src.config.roaster_schema import RoasterConfigSchema
from src.config.fetcher_config import FetcherConfigManager
from dataclasses import dataclass
from src.config.firecrawl_config import FirecrawlConfig


@dataclass
class FetcherConfig:
    """Test configuration for fetcher settings."""
    timeout: float
    max_retries: int
    retry_delay: float
    politeness_delay: float
    jitter_range: float
    max_concurrent: int


class TestPlatformBasedFetcherSelectionE2E:
    """End-to-end tests for platform-based fetcher selection."""
    
    @pytest.fixture
    def roaster_configs(self):
        """Create test roaster configurations for different scenarios."""
        return {
            "shopify_roaster": RoasterConfigSchema(
                id="shopify-test",
                name="Shopify Test Roaster",
                base_url="https://shopify-test.com",
                platform="shopify",
                use_firecrawl_fallback=True,
                firecrawl_budget_limit=10
            ),
            "woocommerce_roaster": RoasterConfigSchema(
                id="woocommerce-test",
                name="WooCommerce Test Roaster",
                base_url="https://woocommerce-test.com",
                platform="woocommerce",
                use_firecrawl_fallback=True,
                firecrawl_budget_limit=10
            ),
            "unknown_roaster": RoasterConfigSchema(
                id="unknown-test",
                name="Unknown Test Roaster",
                base_url="https://unknown-test.com",
                platform=None,  # Unknown platform
                use_firecrawl_fallback=True,
                firecrawl_budget_limit=10
            ),
            "firecrawl_only_roaster": RoasterConfigSchema(
                id="firecrawl-test",
                name="Firecrawl Test Roaster",
                base_url="https://firecrawl-test.com",
                platform="other",  # Custom platform
                use_firecrawl_fallback=True,
                firecrawl_budget_limit=10
            )
        }
    
    @pytest.fixture
    def fetcher_config(self):
        """Create test fetcher configuration."""
        return FetcherConfig(
            timeout=10.0,  # Short timeout for testing
            max_retries=2,
            retry_delay=0.5,
            politeness_delay=0.1,
            jitter_range=0.05,
            max_concurrent=2
        )
    
    @pytest.fixture
    def firecrawl_config(self):
        """Create test Firecrawl configuration."""
        return FirecrawlConfig(
            api_key="test-api-key",
            base_url="https://api.firecrawl.dev",
            budget_limit=10,
            max_pages=10,
            include_subdomains=False,
            sitemap_only=False,
            coffee_keywords=["coffee", "beans", "roast"],
            timeout=10.0,
            max_retries=2,
            retry_delay=0.5,
            enable_monitoring=False,
            log_level="ERROR"
        )
    
    @pytest.mark.asyncio
    async def test_shopify_roaster_successful_detection(self, roaster_configs, fetcher_config, firecrawl_config):
        """Test successful Shopify platform detection and product fetching."""
        roaster_config = roaster_configs["shopify_roaster"]
        
        # Create platform service
        service = PlatformFetcherService(
            roaster_config=roaster_config,
            fetcher_config=fetcher_config,
            firecrawl_config=firecrawl_config
        )
        
        try:
            # Mock Shopify fetcher success
            with patch.object(service, '_get_shopify_fetcher') as mock_shopify:
                mock_shopify_fetcher = AsyncMock()
                mock_shopify_fetcher.test_connection.return_value = True
                mock_shopify_fetcher.fetch_all_products.return_value = [
                    {"id": "shopify-1", "name": "Shopify Coffee 1", "price": 15.99},
                    {"id": "shopify-2", "name": "Shopify Coffee 2", "price": 18.99}
                ]
                mock_shopify.return_value = mock_shopify_fetcher
                
                result = await service.fetch_products_with_cascade("full_refresh")
                
                assert result.success is True
                assert result.platform == "shopify"
                assert result.should_update_platform is True
                assert len(result.products) == 2
                assert result.products[0]["name"] == "Shopify Coffee 1"
                assert result.products[1]["name"] == "Shopify Coffee 2"
                
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_woocommerce_roaster_successful_detection(self, roaster_configs, fetcher_config, firecrawl_config):
        """Test successful WooCommerce platform detection and product fetching."""
        roaster_config = roaster_configs["woocommerce_roaster"]
        
        # Create platform service
        service = PlatformFetcherService(
            roaster_config=roaster_config,
            fetcher_config=fetcher_config,
            firecrawl_config=firecrawl_config
        )
        
        try:
            # Mock Shopify failure and WooCommerce success
            with patch.object(service, '_get_shopify_fetcher') as mock_shopify, \
                 patch.object(service, '_get_woocommerce_fetcher') as mock_woocommerce:
                
                # Shopify fails
                mock_shopify_fetcher = AsyncMock()
                mock_shopify_fetcher.test_connection.return_value = False
                mock_shopify.return_value = mock_shopify_fetcher

                # WooCommerce succeeds
                mock_woocommerce_fetcher = AsyncMock()
                mock_woocommerce_fetcher.test_connection.return_value = True
                mock_woocommerce_fetcher.fetch_all_products.return_value = [
                    {"id": "woo-1", "name": "WooCommerce Coffee 1", "price": 12.99},
                    {"id": "woo-2", "name": "WooCommerce Coffee 2", "price": 16.99}
                ]
                mock_woocommerce.return_value = mock_woocommerce_fetcher
                
                result = await service.fetch_products_with_cascade("full_refresh")
                
                assert result.success is True
                assert result.platform == "woocommerce"
                assert result.should_update_platform is True
                assert len(result.products) == 2
                assert result.products[0]["name"] == "WooCommerce Coffee 1"
                assert result.products[1]["name"] == "WooCommerce Coffee 2"
                
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_unknown_roaster_firecrawl_fallback(self, roaster_configs, fetcher_config, firecrawl_config):
        """Test unknown roaster falling back to Firecrawl."""
        roaster_config = roaster_configs["unknown_roaster"]
        
        # Create platform service
        service = PlatformFetcherService(
            roaster_config=roaster_config,
            fetcher_config=fetcher_config,
            firecrawl_config=firecrawl_config
        )
        
        try:
            # Mock all standard fetchers to fail
            with patch.object(service, '_get_shopify_fetcher') as mock_shopify, \
                 patch.object(service, '_get_woocommerce_fetcher') as mock_woocommerce, \
                 patch.object(service, '_trigger_firecrawl_fallback') as mock_firecrawl:
                
                # Shopify fails
                mock_shopify_fetcher = AsyncMock()
                mock_shopify_fetcher.test_connection.return_value = False
                mock_shopify.return_value = mock_shopify_fetcher
                
                # WooCommerce fails
                mock_woocommerce_fetcher = AsyncMock()
                mock_woocommerce_fetcher.test_connection.return_value = False
                mock_woocommerce.return_value = mock_woocommerce_fetcher
                
                # Firecrawl succeeds
                mock_firecrawl.return_value = Mock(
                    success=True,
                    platform="firecrawl",
                    should_update_platform=False,
                    products=[
                        {"url": "https://unknown-test.com/coffee1", "source": "firecrawl_fallback"},
                        {"url": "https://unknown-test.com/coffee2", "source": "firecrawl_fallback"}
                    ],
                    error=None
                )
                
                result = await service.fetch_products_with_cascade("full_refresh")
                
                assert result.success is True
                assert result.platform == "firecrawl"
                assert result.should_update_platform is False
                assert len(result.products) == 2
                assert result.products[0]["source"] == "firecrawl_fallback"
                assert result.products[1]["source"] == "firecrawl_fallback"
                
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_complete_worker_job_workflow(self, roaster_configs):
        """Test complete worker job workflow with platform detection."""
        # Test Shopify roaster
        job_data = {
            "id": "e2e-test-job",
            "roaster_id": "shopify-test",
            "data": {
                "job_type": "full_refresh",
                "search_terms": ["coffee", "beans"]
            }
        }
        
        config = {
            "roaster_name": "Shopify Test Roaster",
            "base_url": "https://shopify-test.com",
            "platform": "shopify",
            "use_firecrawl_fallback": True,
            "firecrawl_budget_limit": 10,
            "timeout": 10.0,
            "max_retries": 2,
            "retry_delay": 0.5,
            "politeness_delay": 0.1,
            "jitter_range": 0.05,
            "max_concurrent": 2,
            "FIRECRAWL_API_KEY": "test-api-key",
            "FIRECRAWL_BASE_URL": "https://api.firecrawl.dev",
            "FIRECRAWL_MAX_PAGES": 10,
            "FIRECRAWL_INCLUDE_SUBDOMAINS": False,
            "FIRECRAWL_SITEMAP_ONLY": False,
            "FIRECRAWL_COFFEE_KEYWORDS": ["coffee", "beans", "roast"],
            "FIRECRAWL_TIMEOUT": 10.0,
            "FIRECRAWL_MAX_RETRIES": 2,
            "FIRECRAWL_RETRY_DELAY": 0.5,
            "FIRECRAWL_ENABLE_MONITORING": False,
            "FIRECRAWL_LOG_LEVEL": "ERROR"
        }
        
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=True,
                platform="shopify",
                should_update_platform=True,
                products=[
                    {"id": "shopify-1", "name": "E2E Test Coffee 1", "price": 15.99},
                    {"id": "shopify-2", "name": "E2E Test Coffee 2", "price": 18.99}
                ],
                error=None
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the platform update
            with patch('src.worker.tasks._update_roaster_platform', return_value=True) as mock_update:
                result = await execute_scraping_job(job_data, config)
                
                assert result["status"] == "completed"
                assert result["job_type"] == "full_refresh"
                assert result["roaster_id"] == "shopify-test"
                assert result["platform"] == "shopify"
                assert result["items_processed"] == 2
                assert result["errors"] == 0
                assert "processed_at" in result
                
                # Verify platform update was called
                mock_update.assert_called_once_with("shopify-test", "shopify")
    
    @pytest.mark.asyncio
    async def test_batch_roaster_processing(self, roaster_configs):
        """Test processing multiple roasters with different platforms."""
        roasters = [
            ("shopify-test", "shopify"),
            ("woocommerce-test", "woocommerce"),
            ("unknown-test", None),
            ("firecrawl-test", "other")
        ]
        
        results = []
        
        for roaster_id, platform in roasters:
            job_data = {
                "id": f"batch-test-{roaster_id}",
                "roaster_id": roaster_id,
                "data": {"job_type": "full_refresh"}
            }
            
            config = {
                "roaster_name": f"{roaster_id.title()} Roaster",
                "base_url": f"https://{roaster_id}.com",
                "platform": platform,
                "use_firecrawl_fallback": True,
                "firecrawl_budget_limit": 10,
                "timeout": 5.0,
                "max_retries": 1,
                "retry_delay": 0.1,
                "politeness_delay": 0.1,
                "jitter_range": 0.05,
                "max_concurrent": 1,
                "FIRECRAWL_API_KEY": "test-api-key",
                "FIRECRAWL_BASE_URL": "https://api.firecrawl.dev",
                "FIRECRAWL_MAX_PAGES": 5,
                "FIRECRAWL_INCLUDE_SUBDOMAINS": False,
                "FIRECRAWL_SITEMAP_ONLY": False,
                "FIRECRAWL_COFFEE_KEYWORDS": ["coffee"],
                "FIRECRAWL_TIMEOUT": 5.0,
                "FIRECRAWL_MAX_RETRIES": 1,
                "FIRECRAWL_RETRY_DELAY": 0.1,
                "FIRECRAWL_ENABLE_MONITORING": False,
                "FIRECRAWL_LOG_LEVEL": "ERROR"
            }
            
            with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
                # Mock the platform service
                mock_service = AsyncMock()
                mock_service.fetch_products_with_cascade.return_value = Mock(
                    success=True,
                    platform=platform or "firecrawl",
                    should_update_platform=platform is not None,
                    products=[{"id": f"{roaster_id}-1", "name": f"Batch Test Coffee for {roaster_id}"}],
                    error=None
                )
                mock_service.close = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock the platform update
                with patch('src.worker.tasks._update_roaster_platform', return_value=True):
                    result = await execute_scraping_job(job_data, config)
                    results.append(result)
        
        # Verify all jobs completed successfully
        assert len(results) == 4
        for result in results:
            assert result["status"] == "completed"
            assert result["items_processed"] == 1
            assert result["errors"] == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, roaster_configs):
        """Test error handling and recovery scenarios."""
        job_data = {
            "id": "error-test-job",
            "roaster_id": "error-test",
            "data": {"job_type": "full_refresh"}
        }
        
        config = {
            "roaster_name": "Error Test Roaster",
            "base_url": "https://error-test.com",
            "platform": None,  # Unknown platform
            "use_firecrawl_fallback": True,
            "firecrawl_budget_limit": 10,
            "timeout": 5.0,
            "max_retries": 1,
            "retry_delay": 0.1,
            "politeness_delay": 0.1,
            "jitter_range": 0.05,
            "max_concurrent": 1,
            "FIRECRAWL_API_KEY": "test-api-key",
            "FIRECRAWL_BASE_URL": "https://api.firecrawl.dev",
            "FIRECRAWL_MAX_PAGES": 5,
            "FIRECRAWL_INCLUDE_SUBDOMAINS": False,
            "FIRECRAWL_SITEMAP_ONLY": False,
            "FIRECRAWL_COFFEE_KEYWORDS": ["coffee"],
            "FIRECRAWL_TIMEOUT": 5.0,
            "FIRECRAWL_MAX_RETRIES": 1,
            "FIRECRAWL_RETRY_DELAY": 0.1,
            "FIRECRAWL_ENABLE_MONITORING": False,
            "FIRECRAWL_LOG_LEVEL": "ERROR"
        }
        
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service with failure
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=False,
                platform="unknown",
                should_update_platform=False,
                products=[],
                error="All fetchers failed including Firecrawl"
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            result = await execute_scraping_job(job_data, config)
            
            assert result["status"] == "failed"
            assert result["items_processed"] == 0
            assert result["errors"] == 1
            assert "All fetchers failed including Firecrawl" in result["error"]
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, roaster_configs):
        """Test performance under concurrent load."""
        # Create multiple concurrent jobs
        job_count = 10
        jobs = []
        
        for i in range(job_count):
            job_data = {
                "id": f"load-test-job-{i}",
                "roaster_id": f"load-test-roaster-{i}",
                "data": {"job_type": "full_refresh"}
            }
            
            config = {
                "roaster_name": f"Load Test Roaster {i}",
                "base_url": f"https://load-test-{i}.com",
                "platform": "shopify" if i % 2 == 0 else "woocommerce",
                "use_firecrawl_fallback": True,
                "firecrawl_budget_limit": 10,
                "timeout": 5.0,
                "max_retries": 1,
                "retry_delay": 0.1,
                "politeness_delay": 0.1,
                "jitter_range": 0.05,
                "max_concurrent": 3,
                "FIRECRAWL_API_KEY": "test-api-key",
                "FIRECRAWL_BASE_URL": "https://api.firecrawl.dev",
                "FIRECRAWL_MAX_PAGES": 5,
                "FIRECRAWL_INCLUDE_SUBDOMAINS": False,
                "FIRECRAWL_SITEMAP_ONLY": False,
                "FIRECRAWL_COFFEE_KEYWORDS": ["coffee"],
                "FIRECRAWL_TIMEOUT": 5.0,
                "FIRECRAWL_MAX_RETRIES": 1,
                "FIRECRAWL_RETRY_DELAY": 0.1,
                "FIRECRAWL_ENABLE_MONITORING": False,
                "FIRECRAWL_LOG_LEVEL": "ERROR"
            }
            
            jobs.append((job_data, config))
        
        # Execute all jobs concurrently
        async def execute_job(job_data, config):
            with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
                # Mock the platform service
                mock_service = AsyncMock()
                mock_service.fetch_products_with_cascade.return_value = Mock(
                    success=True,
                    platform=config["platform"],
                    should_update_platform=True,
                    products=[{"id": f"load-test-{job_data['roaster_id']}-1", "name": "Load Test Coffee"}],
                    error=None
                )
                mock_service.close = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock the platform update
                with patch('src.worker.tasks._update_roaster_platform', return_value=True):
                    return await execute_scraping_job(job_data, config)
        
        # Execute all jobs concurrently
        import time
        start_time = time.time()
        
        tasks = [execute_job(job_data, config) for job_data, config in jobs]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify all jobs completed successfully
        assert len(results) == job_count
        for result in results:
            assert result["status"] == "completed"
            assert result["items_processed"] == 1
            assert result["errors"] == 0
        
        # Performance should be reasonable
        assert execution_time < 30.0  # Should complete within 30 seconds
        print(f"Executed {job_count} concurrent jobs in {execution_time:.2f} seconds")
        print(f"Average time per job: {execution_time / job_count:.2f} seconds")
