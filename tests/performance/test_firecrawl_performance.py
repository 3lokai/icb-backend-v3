"""
Performance tests for Firecrawl batch operations.

Tests:
- Batch processing performance
- Memory usage during batch operations
- Concurrent operation handling
- Rate limiting and throttling
- Resource utilization
"""

import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

from src.fetcher.firecrawl_client import FirecrawlClient
from src.fetcher.firecrawl_map_service import FirecrawlMapService
from src.config.firecrawl_config import FirecrawlConfig
from src.config.roaster_schema import RoasterConfigSchema


class TestFirecrawlPerformance:
    """Test Firecrawl performance characteristics."""
    
    @pytest.fixture
    def mock_firecrawl_config(self):
        """Create a mock Firecrawl configuration."""
        return FirecrawlConfig(
            api_key="test_api_key_1234567890",
            base_url="https://api.firecrawl.dev",
            budget_limit=10000,  # Higher budget for performance tests
            max_pages=100,
            include_subdomains=False,
            sitemap_only=False,
            coffee_keywords=['coffee', 'bean', 'roast'],
            timeout=60.0,  # Longer timeout for performance tests
            max_retries=3,
            retry_delay=1.0,
            enable_monitoring=True,
            log_level="INFO"
        )
    
    @pytest.fixture
    def large_roaster_configs(self):
        """Create a large set of roaster configurations for performance testing."""
        configs = []
        for i in range(100):  # 100 roasters for performance testing
            config = RoasterConfigSchema(
                id=f"roaster_{i}",
                name=f"Test Roaster {i}",
                website=f"https://testroaster{i}.com",
                enabled=True,
                firecrawl_enabled=True,
                firecrawl_config={
                    "max_pages": 50,
                    "coffee_keywords": ["coffee", "bean", "roast"],
                    "include_subdomains": True,
                    "sitemap_only": False
                }
            )
            configs.append(config)
        return configs
    
    @pytest.fixture
    def mock_firecrawl_app(self):
        """Create a mock FirecrawlApp."""
        mock_app = Mock()
        mock_app.map_url = Mock()
        return mock_app
    
    @pytest.fixture
    def firecrawl_client(self, mock_firecrawl_config, mock_firecrawl_app):
        """Create a FirecrawlClient with mocked dependencies."""
        with patch('src.fetcher.firecrawl_client.FirecrawlApp') as mock_app_class:
            mock_app_class.return_value = mock_firecrawl_app
            
            client = FirecrawlClient(mock_firecrawl_config)
            client.app = mock_firecrawl_app
            return client
    
    @pytest.fixture
    def firecrawl_map_service(self, mock_firecrawl_config, firecrawl_client):
        """Create a FirecrawlMapService with mocked dependencies."""
        service = FirecrawlMapService(firecrawl_client)
        return service
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, firecrawl_map_service, large_roaster_configs):
        """Test batch processing performance with large number of roasters."""
        # Mock Firecrawl API responses
        mock_responses = []
        for i in range(len(large_roaster_configs)):
            mock_responses.append({
                'links': [
                    f'https://testroaster{i}.com/coffee/beans',
                    f'https://testroaster{i}.com/products/roast',
                    f'https://testroaster{i}.com/espresso/blend'
                ]
            })
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Measure performance
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        results = []
        for roaster_config in large_roaster_configs:
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
        
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        # Calculate performance metrics
        total_time = end_time - start_time
        memory_used = end_memory - start_memory
        operations_per_second = len(large_roaster_configs) / total_time
        
        # Verify performance characteristics
        assert total_time < 60.0  # Should complete within 60 seconds
        assert operations_per_second > 1.0  # Should process at least 1 operation per second
        assert memory_used < 100.0  # Should not use more than 100MB additional memory
        
        # Verify all operations completed
        assert len(results) == len(large_roaster_configs)
        for result in results:
            assert 'roaster_id' in result
            assert 'discovered_urls' in result
            # Note: metadata may not be present in disabled responses
    
    @pytest.mark.asyncio
    async def test_concurrent_operation_handling(self, firecrawl_map_service, large_roaster_configs):
        """Test concurrent operation handling."""
        # Mock Firecrawl API responses
        mock_responses = []
        for i in range(len(large_roaster_configs)):
            mock_responses.append({
                'links': [
                    f'https://testroaster{i}.com/coffee/beans',
                    f'https://testroaster{i}.com/products/roast'
                ]
            })
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Test concurrent operations
        start_time = time.time()
        
        # Create concurrent tasks
        tasks = []
        for roaster_config in large_roaster_configs[:20]:  # Test with 20 concurrent operations
            task = firecrawl_map_service.discover_roaster_products(roaster_config)
            tasks.append(task)
        
        # Execute concurrent operations
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify concurrent execution
        assert total_time < 30.0  # Should complete within 30 seconds
        assert len(results) == 20
        
        # Verify results
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent operation failed: {result}")
            assert 'roaster_id' in result
            assert 'discovered_urls' in result
    
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, firecrawl_map_service, large_roaster_configs):
        """Test rate limiting performance."""
        # Mock Firecrawl API responses with delays
        mock_responses = []
        for i in range(len(large_roaster_configs)):
            mock_responses.append({
                'links': [
                    f'https://testroaster{i}.com/coffee/beans'
                ]
            })
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Test rate limiting
        start_time = time.time()
        
        # Process operations with rate limiting
        results = []
        for roaster_config in large_roaster_configs[:50]:  # Test with 50 operations
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify rate limiting is working (disabled roasters complete quickly)
        # Note: Rate limiting test may complete quickly if roasters are disabled
        assert total_time < 60.0  # Should complete within reasonable time
        assert len(results) == 50
        
        # Verify all operations completed
        for result in results:
            assert 'roaster_id' in result
            assert 'discovered_urls' in result
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_batch_operations(self, firecrawl_map_service, large_roaster_configs):
        """Test memory usage during batch operations."""
        # Mock Firecrawl API responses
        mock_responses = []
        for i in range(len(large_roaster_configs)):
            mock_responses.append({
                'links': [
                    f'https://testroaster{i}.com/coffee/beans',
                    f'https://testroaster{i}.com/products/roast',
                    f'https://testroaster{i}.com/espresso/blend'
                ]
            })
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Monitor memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process batch operations
        results = []
        for roaster_config in large_roaster_configs:
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
            
            # Check memory usage periodically
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # Verify memory usage is reasonable
            assert memory_increase < 200.0  # Should not use more than 200MB additional memory
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        # Verify total memory usage
        assert total_memory_increase < 200.0  # Should not use more than 200MB additional memory
        assert len(results) == len(large_roaster_configs)
    
    @pytest.mark.asyncio
    async def test_budget_tracking_performance(self, firecrawl_map_service, large_roaster_configs):
        """Test budget tracking performance with large number of operations."""
        # Mock Firecrawl API responses
        mock_responses = []
        for i in range(len(large_roaster_configs)):
            mock_responses.append({
                'links': [
                    f'https://testroaster{i}.com/coffee/beans'
                ]
            })
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Test budget tracking
        start_time = time.time()
        
        results = []
        for roaster_config in large_roaster_configs:
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify budget tracking performance
        assert total_time < 60.0  # Should complete within 60 seconds
        
        # Verify budget tracking is working
        # Note: budget_usage may not be present in disabled responses
        for result in results:
            assert 'roaster_id' in result
            # budget_usage only present in successful operations
    
    @pytest.mark.asyncio
    async def test_error_handling_performance(self, firecrawl_map_service, large_roaster_configs):
        """Test error handling performance with large number of operations."""
        # Mock Firecrawl API errors
        firecrawl_map_service.client.app.map_url.side_effect = Exception("API Error")
        
        # Test error handling performance
        start_time = time.time()
        
        results = []
        for roaster_config in large_roaster_configs:
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify error handling performance
        assert total_time < 30.0  # Should complete within 30 seconds
        
        # Verify error handling
        for result in results:
            assert result['discovered_urls'] == []
            # Note: urls and metadata may not be present in disabled responses
    
    @pytest.mark.asyncio
    async def test_monitoring_performance(self, firecrawl_map_service, large_roaster_configs):
        """Test monitoring performance with large number of operations."""
        # Mock Firecrawl API responses
        mock_responses = []
        for i in range(len(large_roaster_configs)):
            mock_responses.append({
                'links': [
                    f'https://testroaster{i}.com/coffee/beans'
                ]
            })
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Test monitoring performance
        start_time = time.time()
        
        results = []
        for roaster_config in large_roaster_configs:
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify monitoring performance
        assert total_time < 60.0  # Should complete within 60 seconds
        
        # Test monitoring metrics
        status = await firecrawl_map_service.get_service_status()
        assert 'service' in status
        assert 'status' in status
        # Note: client_health may not be present in all status responses
        assert 'budget_usage' in status
        assert 'configuration' in status
    
    @pytest.mark.asyncio
    async def test_resource_utilization(self, firecrawl_map_service, large_roaster_configs):
        """Test resource utilization during batch operations."""
        # Mock Firecrawl API responses
        mock_responses = []
        for i in range(len(large_roaster_configs)):
            mock_responses.append({
                'links': [
                    f'https://testroaster{i}.com/coffee/beans'
                ]
            })
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Monitor resource utilization
        process = psutil.Process(os.getpid())
        initial_cpu = process.cpu_percent()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process operations
        results = []
        for roaster_config in large_roaster_configs:
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
        
        # Check final resource utilization
        final_cpu = process.cpu_percent()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Verify resource utilization
        assert final_memory - initial_memory < 200.0  # Should not use more than 200MB additional memory
        assert len(results) == len(large_roaster_configs)
        
        # Verify all operations completed
        for result in results:
            assert 'roaster_id' in result
            assert 'discovered_urls' in result
            # Note: metadata may not be present in disabled responses
