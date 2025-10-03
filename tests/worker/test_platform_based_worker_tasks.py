"""
Integration tests for platform-based worker tasks.

Tests the worker task integration for Story A.6: Platform-Based Fetcher Selection with Automatic Fallback.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.worker.tasks import execute_scraping_job, _update_roaster_platform, execute_firecrawl_map_job
from src.config.roaster_schema import RoasterConfigSchema


class TestPlatformBasedWorkerTasks:
    """Test cases for platform-based worker tasks."""
    
    @pytest.fixture
    def sample_job_data(self):
        """Create sample job data for testing."""
        return {
            "id": "test-job-123",
            "roaster_id": "test-roaster",
            "data": {
                "job_type": "full_refresh",
                "search_terms": ["coffee", "beans"]
            }
        }
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing."""
        return {
            "roaster_name": "Test Roaster",
            "base_url": "https://test-roaster.com",
            "platform": "shopify",
            "use_firecrawl_fallback": True,
            "firecrawl_budget_limit": 10,
            "timeout": 30.0,
            "max_retries": 3,
            "retry_delay": 1.0,
            "politeness_delay": 0.25,
            "jitter_range": 0.1,
            "max_concurrent": 3,
            "FIRECRAWL_API_KEY": "test-api-key",
            "FIRECRAWL_BASE_URL": "https://api.firecrawl.dev",
            "FIRECRAWL_MAX_PAGES": 50,
            "FIRECRAWL_INCLUDE_SUBDOMAINS": False,
            "FIRECRAWL_SITEMAP_ONLY": False,
            "FIRECRAWL_COFFEE_KEYWORDS": ["coffee", "beans", "roast"],
            "FIRECRAWL_TIMEOUT": 30.0,
            "FIRECRAWL_MAX_RETRIES": 3,
            "FIRECRAWL_RETRY_DELAY": 1.0,
            "FIRECRAWL_ENABLE_MONITORING": True,
            "FIRECRAWL_LOG_LEVEL": "INFO"
        }
    
    @pytest.mark.asyncio
    async def test_execute_scraping_job_shopify_success(self, sample_job_data, sample_config):
        """Test successful Shopify scraping job."""
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=True,
                platform="shopify",
                should_update_platform=True,
                products=[{"id": "1", "name": "Test Coffee"}],
                error=None
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the platform update
            with patch('src.worker.tasks._update_roaster_platform', return_value=True) as mock_update:
                result = await execute_scraping_job(sample_job_data, sample_config)
                
                assert result["status"] == "completed"
                assert result["platform"] == "shopify"
                assert result["items_processed"] == 1
                assert result["errors"] == 0
                
                # Verify platform update was called
                mock_update.assert_called_once_with("test-roaster", "shopify")
    
    @pytest.mark.asyncio
    async def test_execute_scraping_job_woocommerce_success(self, sample_job_data, sample_config):
        """Test successful WooCommerce scraping job."""
        # Update config to use WooCommerce
        sample_config["platform"] = "woocommerce"
        
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=True,
                platform="woocommerce",
                should_update_platform=True,
                products=[{"id": "2", "name": "WooCommerce Coffee"}],
                error=None
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the platform update
            with patch('src.worker.tasks._update_roaster_platform', return_value=True) as mock_update:
                result = await execute_scraping_job(sample_job_data, sample_config)
                
                assert result["status"] == "completed"
                assert result["platform"] == "woocommerce"
                assert result["items_processed"] == 1
                assert result["errors"] == 0
                
                # Verify platform update was called
                mock_update.assert_called_once_with("test-roaster", "woocommerce")
    
    @pytest.mark.asyncio
    async def test_execute_scraping_job_firecrawl_fallback_success(self, sample_job_data, sample_config):
        """Test successful Firecrawl fallback scraping job."""
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service with Firecrawl fallback
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=True,
                platform="firecrawl",
                should_update_platform=False,  # Firecrawl doesn't update platform
                products=[{"url": "https://test-roaster.com/coffee", "source": "firecrawl_fallback"}],
                error=None
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the platform update (should not be called for Firecrawl)
            with patch('src.worker.tasks._update_roaster_platform', return_value=True) as mock_update:
                result = await execute_scraping_job(sample_job_data, sample_config)
                
                assert result["status"] == "completed"
                assert result["platform"] == "firecrawl"
                assert result["items_processed"] == 1
                assert result["errors"] == 0
                
                # Verify platform update was NOT called for Firecrawl
                mock_update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_scraping_job_all_fail(self, sample_job_data, sample_config):
        """Test scraping job when all fetchers fail."""
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
            
            result = await execute_scraping_job(sample_job_data, sample_config)
            
            assert result["status"] == "failed"
            assert result["items_processed"] == 0
            assert result["errors"] == 1
            assert "All fetchers failed including Firecrawl" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_scraping_job_platform_update_failure(self, sample_job_data, sample_config):
        """Test scraping job when platform update fails."""
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service with success
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=True,
                platform="shopify",
                should_update_platform=True,
                products=[{"id": "1", "name": "Test Coffee"}],
                error=None
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the platform update to fail
            with patch('src.worker.tasks._update_roaster_platform', return_value=False) as mock_update:
                result = await execute_scraping_job(sample_job_data, sample_config)
                
                # Job should still succeed even if platform update fails
                assert result["status"] == "completed"
                assert result["platform"] == "shopify"
                assert result["items_processed"] == 1
                assert result["errors"] == 0
                
                # Verify platform update was attempted
                mock_update.assert_called_once_with("test-roaster", "shopify")
    
    @pytest.mark.asyncio
    async def test_update_roaster_platform_success(self):
        """Test successful roaster platform update."""
        with patch('src.validator.rpc_client.RPCClient') as mock_rpc_class:
            # Mock RPC client
            mock_rpc_client = Mock()
            mock_rpc_client.update_roaster_platform.return_value = True
            mock_rpc_class.return_value = mock_rpc_client
            
            # Mock environment variables
            with patch.dict('os.environ', {
                'SUPABASE_URL': 'https://test.supabase.co',
                'SUPABASE_ANON_KEY': 'test-key'
            }):
                result = await _update_roaster_platform("test-roaster", "shopify")
                
                assert result is True
                mock_rpc_client.update_roaster_platform.assert_called_once_with("test-roaster", "shopify")
    
    @pytest.mark.asyncio
    async def test_update_roaster_platform_failure(self):
        """Test roaster platform update failure."""
        with patch('src.validator.rpc_client.RPCClient') as mock_rpc_class:
            # Mock RPC client failure
            mock_rpc_client = Mock()
            mock_rpc_client.update_roaster_platform.return_value = False
            mock_rpc_class.return_value = mock_rpc_client
            
            # Mock environment variables
            with patch.dict('os.environ', {
                'SUPABASE_URL': 'https://test.supabase.co',
                'SUPABASE_ANON_KEY': 'test-key'
            }):
                result = await _update_roaster_platform("test-roaster", "shopify")
                
                assert result is False
                mock_rpc_client.update_roaster_platform.assert_called_once_with("test-roaster", "shopify")
    
    @pytest.mark.asyncio
    async def test_update_roaster_platform_missing_config(self):
        """Test roaster platform update with missing configuration."""
        with patch.dict('os.environ', {}, clear=True):
            result = await _update_roaster_platform("test-roaster", "shopify")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_scraping_job_configuration_validation(self, sample_job_data):
        """Test that job configuration is properly validated."""
        # Test with minimal configuration
        minimal_config = {
            "roaster_name": "Test Roaster",
            "base_url": "https://test-roaster.com",
            "use_firecrawl_fallback": False  # Disable Firecrawl to test minimal config
        }
        
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=True,
                platform="shopify",
                should_update_platform=True,
                products=[{"id": "1", "name": "Test Coffee"}],
                error=None
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the platform update
            with patch('src.worker.tasks._update_roaster_platform', return_value=True):
                result = await execute_scraping_job(sample_job_data, minimal_config)
                
                assert result["status"] == "completed"
                assert result["platform"] == "shopify"
                
                # Verify service was created with default values
                mock_service_class.assert_called_once()
                call_args = mock_service_class.call_args
                roaster_config = call_args[1]['roaster_config']
                
                # Check default values were applied
                assert roaster_config.platform is None  # No platform specified
                assert roaster_config.use_firecrawl_fallback is False  # Explicitly set to False
                assert roaster_config.firecrawl_budget_limit == 10  # Default


class TestPlatformBasedWorkerTasksPerformance:
    """Performance tests for platform-based worker tasks."""
    
    @pytest.mark.asyncio
    async def test_fetcher_cascade_performance(self):
        """Test that fetcher cascade completes within reasonable time."""
        job_data = {
            "id": "perf-test-job",
            "roaster_id": "perf-test-roaster",
            "data": {"job_type": "full_refresh"}
        }
        
        config = {
            "roaster_name": "Performance Test Roaster",
            "base_url": "https://perf-test.com",
            "platform": "shopify",
            "use_firecrawl_fallback": True,
            "firecrawl_budget_limit": 10,
            "timeout": 5.0,  # Short timeout for performance testing
            "max_retries": 1,
            "retry_delay": 0.1,
            "politeness_delay": 0.1,
            "jitter_range": 0.05,
            "max_concurrent": 1,
            "FIRECRAWL_API_KEY": "test-api-key-12345"
        }
        
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=True,
                platform="shopify",
                should_update_platform=True,
                products=[{"id": "1", "name": "Performance Test Coffee"}],
                error=None
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the platform update
            with patch('src.worker.tasks._update_roaster_platform', return_value=True):
                import time
                start_time = time.time()
                
                result = await execute_scraping_job(job_data, config)
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                assert result["status"] == "completed"
                assert execution_time < 10.0  # Should complete within 10 seconds
                print(f"Execution time: {execution_time:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_concurrent_job_handling(self):
        """Test handling multiple concurrent jobs."""
        job_data_1 = {
            "id": "concurrent-job-1",
            "roaster_id": "roaster-1",
            "data": {"job_type": "full_refresh"}
        }
        
        job_data_2 = {
            "id": "concurrent-job-2",
            "roaster_id": "roaster-2",
            "data": {"job_type": "price_only"}
        }
        
        config = {
            "roaster_name": "Concurrent Test Roaster",
            "base_url": "https://concurrent-test.com",
            "platform": "shopify",
            "use_firecrawl_fallback": True,
            "firecrawl_budget_limit": 10,
            "timeout": 5.0,
            "max_retries": 1,
            "retry_delay": 0.1,
            "politeness_delay": 0.1,
            "jitter_range": 0.05,
            "max_concurrent": 2,
            "FIRECRAWL_API_KEY": "test-api-key-12345"
        }
        
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            # Mock the platform service
            mock_service = AsyncMock()
            mock_service.fetch_products_with_cascade.return_value = Mock(
                success=True,
                platform="shopify",
                should_update_platform=True,
                products=[{"id": "1", "name": "Concurrent Test Coffee"}],
                error=None
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the platform update
            with patch('src.worker.tasks._update_roaster_platform', return_value=True):
                # Execute jobs concurrently
                tasks = [
                    execute_scraping_job(job_data_1, config),
                    execute_scraping_job(job_data_2, config)
                ]
                
                results = await asyncio.gather(*tasks)
                
                # Both jobs should succeed
                assert len(results) == 2
                assert results[0]["status"] == "completed"
                assert results[1]["status"] == "completed"
                assert results[0]["platform"] == "shopify"
                assert results[1]["platform"] == "shopify"


class TestWorkerTasksEpicBIntegration:
    """Test Epic B integration features for worker tasks."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            'database': {'url': 'sqlite:///:memory:'},
            'firecrawl': {
                'api_key': 'test_key',
                'budget_limit': 1000
            },
            'monitoring': {'enabled': True},
            'FIRECRAWL_API_KEY': 'test_api_key_1234567890',
            'firecrawl_budget_limit': 1000
        }
    
    @pytest.mark.asyncio
    async def test_firecrawl_map_job_with_epic_b_job_type(self, mock_config):
        """Test Firecrawl map job with Epic B job_type parameter."""
        job_data = {
            'job_id': 'test_job_123',
            'roaster_id': 'test_roaster',
            'platform': 'firecrawl',
            'job_type': 'map_discovery',
            'data': {
                'job_type': 'price_only',  # Epic B price-only mode
                'search_terms': ['coffee', 'beans']
            }
        }
        
        with patch('src.worker.tasks.FirecrawlMapService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.discover_roaster_products.return_value = {
                'roaster_id': 'test_roaster',
                'job_type': 'price_only',
                'discovered_urls': ['https://example.com/coffee/beans'],
                'status': 'success'
            }
            mock_service_class.return_value = mock_service
            
            # Execute the job
            result = await execute_firecrawl_map_job(job_data, mock_config)
            
            # Verify job_type was passed to the service
            mock_service.discover_roaster_products.assert_called_once()
            call_args = mock_service.discover_roaster_products.call_args
            assert call_args[1]['job_type'] == 'price_only'
            
            # Verify result includes job_type
            assert result['status'] == 'completed'
            assert result['job_type'] == 'price_only'
    
    @pytest.mark.asyncio
    async def test_firecrawl_map_job_full_refresh_mode(self, mock_config):
        """Test Firecrawl map job with full refresh mode."""
        job_data = {
            'job_id': 'test_job_124',
            'roaster_id': 'test_roaster',
            'platform': 'firecrawl',
            'job_type': 'map_discovery',
            'data': {
                'job_type': 'full_refresh',  # Full refresh mode
                'search_terms': ['coffee', 'beans']
            }
        }
        
        with patch('src.worker.tasks.FirecrawlMapService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.discover_roaster_products.return_value = {
                'roaster_id': 'test_roaster',
                'job_type': 'full_refresh',
                'discovered_urls': ['https://example.com/coffee/beans'],
                'status': 'success'
            }
            mock_service_class.return_value = mock_service
            
            # Execute the job
            result = await execute_firecrawl_map_job(job_data, mock_config)
            
            # Verify job_type was passed to the service
            mock_service.discover_roaster_products.assert_called_once()
            call_args = mock_service.discover_roaster_products.call_args
            assert call_args[1]['job_type'] == 'full_refresh'
            
            # Verify result includes job_type
            assert result['status'] == 'completed'
            assert result['job_type'] == 'full_refresh'
    
    @pytest.mark.asyncio
    async def test_firecrawl_map_job_default_job_type(self, mock_config):
        """Test Firecrawl map job with default job_type when not specified."""
        job_data = {
            'job_id': 'test_job_125',
            'roaster_id': 'test_roaster',
            'platform': 'firecrawl',
            'job_type': 'map_discovery',
            'data': {
                # No job_type specified - should default to 'full_refresh'
                'search_terms': ['coffee', 'beans']
            }
        }
        
        with patch('src.worker.tasks.FirecrawlMapService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.discover_roaster_products.return_value = {
                'roaster_id': 'test_roaster',
                'job_type': 'full_refresh',
                'discovered_urls': ['https://example.com/coffee/beans'],
                'status': 'success'
            }
            mock_service_class.return_value = mock_service
            
            # Execute the job
            result = await execute_firecrawl_map_job(job_data, mock_config)
            
            # Verify default job_type was used
            mock_service.discover_roaster_products.assert_called_once()
            call_args = mock_service.discover_roaster_products.call_args
            assert call_args[1]['job_type'] == 'full_refresh'
            
            # Verify result includes job_type
            assert result['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_platform_fetcher_service_epic_b_integration(self, mock_config):
        """Test platform fetcher service with Epic B job_type integration."""
        job_data = {
            'job_id': 'test_job_126',
            'roaster_id': 'test_roaster',
            'platform': 'shopify',
            'job_type': 'scraping',
            'data': {
                'job_type': 'price_only',  # Epic B price-only mode
                'search_terms': ['coffee', 'beans']
            }
        }
        
        with patch('src.worker.tasks.PlatformFetcherService') as mock_service_class:
            mock_service = AsyncMock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.platform = 'shopify'
            mock_result.products = []
            mock_result.roaster_id = 'test_roaster'
            mock_result.job_type = 'price_only'
            mock_service.fetch_products_with_cascade.return_value = mock_result
            mock_service_class.return_value = mock_service
            
            # Execute the job
            result = await execute_scraping_job(job_data, mock_config)
            
            # Verify job_type was passed to the service
            mock_service.fetch_products_with_cascade.assert_called_once()
            call_kwargs = mock_service.fetch_products_with_cascade.call_args[1]
            assert call_kwargs['job_type'] == 'price_only'
            
            # Verify result includes job_type
            assert result['status'] == 'completed'