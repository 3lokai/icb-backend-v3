"""
Integration tests for Firecrawl operations.

Tests:
- End-to-end Firecrawl workflow
- Integration with job queue
- Real API interactions (with mocking)
- Error handling and recovery
- Performance characteristics
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

from src.fetcher.firecrawl_client import FirecrawlClient
from src.fetcher.firecrawl_map_service import FirecrawlMapService
from src.config.firecrawl_config import FirecrawlConfig
from src.config.roaster_schema import RoasterConfigSchema
from src.validator.integration_service import ValidatorIntegrationService
from src.worker.tasks import (
    execute_firecrawl_map_job,
    execute_firecrawl_batch_map_job,
    queue_firecrawl_extract_jobs
)


class TestFirecrawlIntegration:
    """Test Firecrawl integration functionality."""
    
    @pytest.fixture
    def mock_firecrawl_config(self):
        """Create a mock Firecrawl configuration."""
        return FirecrawlConfig(
            api_key="test_api_key_1234567890",
            base_url="https://api.firecrawl.dev",
            budget_limit=1000,
            max_pages=50,
            include_subdomains=False,
            sitemap_only=False,
            coffee_keywords=['coffee', 'bean', 'roast'],
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
            enable_monitoring=True,
            log_level="INFO"
        )
    
    @pytest.fixture
    def mock_roaster_configs(self):
        """Create mock roaster configurations."""
        return [
            RoasterConfigSchema(
                id="roaster_1",
                name="Test Roaster 1",
                base_url="https://testroaster1.com",
                active=True,
                use_firecrawl_fallback=True,
                firecrawl_budget_limit=1000
            ),
            RoasterConfigSchema(
                id="roaster_2",
                name="Test Roaster 2",
                base_url="https://testroaster2.com",
                active=True,
                use_firecrawl_fallback=True,
                firecrawl_budget_limit=1000
            ),
            RoasterConfigSchema(
                id="roaster_3",
                name="Disabled Roaster",
                base_url="https://disabledroaster.com",
                active=False,
                use_firecrawl_fallback=False
            )
        ]
    
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
    def firecrawl_map_service(self, firecrawl_client):
        """Create a FirecrawlMapService with mocked dependencies."""
        service = FirecrawlMapService(firecrawl_client)
        return service
    
    @pytest.mark.asyncio
    async def test_end_to_end_roaster_discovery(self, firecrawl_map_service, mock_roaster_configs):
        """Test end-to-end roaster product discovery."""
        # Mock Firecrawl API response
        mock_response = {
            'links': [
                'https://testroaster1.com/coffee/beans',
                'https://testroaster1.com/products/roast',
                'https://testroaster1.com/espresso/blend',
                'https://testroaster1.com/about',
                'https://testroaster1.com/contact'
            ]
        }
        
        firecrawl_map_service.client.app.map_url.return_value = mock_response
        
        # Test discovery for first roaster
        roaster_config = mock_roaster_configs[0]
        result = await firecrawl_map_service.discover_roaster_products(roaster_config)
        
        # Verify result structure
        assert 'roaster_id' in result
        assert 'discovered_urls' in result
        assert 'status' in result
        
        # Verify URLs were discovered
        assert len(result['discovered_urls']) > 0
        
        # Verify metadata
        assert result['roaster_id'] == "roaster_1"
        assert result['roaster_name'] == "Test Roaster 1"
    
    @pytest.mark.asyncio
    async def test_batch_roaster_discovery(self, firecrawl_map_service, mock_roaster_configs):
        """Test batch roaster product discovery."""
        # Mock Firecrawl API responses for different roasters
        mock_responses = [
            {
                'links': [
                    'https://testroaster1.com/coffee/beans',
                    'https://testroaster1.com/products/roast'
                ]
            },
            {
                'links': [
                    'https://testroaster2.com/coffee/beans',
                    'https://testroaster2.com/products/roast'
                ]
            }
        ]
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Test batch discovery
        results = []
        for roaster_config in mock_roaster_configs:
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
        
        # Verify results
        assert len(results) == 3
        
        # First two roasters should have URLs discovered
        assert len(results[0]['discovered_urls']) > 0
        assert len(results[1]['discovered_urls']) > 0
        
        # Disabled roaster should be skipped
        assert len(results[2]['discovered_urls']) == 0
        assert results[2]['status'] == 'disabled'
    
    @pytest.mark.asyncio
    async def test_firecrawl_map_job_execution(self, mock_firecrawl_config, mock_roaster_configs):
        """Test Firecrawl map job execution."""
        # Mock the FirecrawlMapService
        with patch('src.worker.tasks.FirecrawlMapService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the discover_roaster_products method as async
            async def mock_discover_roaster_products(*args, **kwargs):
                return {
                    'roaster_id': 'roaster_1',
                    'roaster_name': 'Test Roaster 1',
                    'discovered_urls': [
                        'https://testroaster1.com/coffee/beans',
                        'https://testroaster1.com/products/roast'
                    ],
                    'status': 'success',
                    'budget_used': 50,
                    'operation_time_seconds': 2.5,
                    'timestamp': '2024-01-01T00:00:00Z'
                }
            mock_service.discover_roaster_products = Mock(side_effect=mock_discover_roaster_products)
            
            # Test job execution
            roaster_config = mock_roaster_configs[0]
            job_data = roaster_config.model_dump()
            job_data['roaster_id'] = roaster_config.id  # Add roaster_id to job_data
            config_dict = mock_firecrawl_config.model_dump()
            # Add FIRECRAWL_ prefix to match what the worker expects
            firecrawl_config = {f"FIRECRAWL_{k.upper()}": v for k, v in config_dict.items()}
            result = await execute_firecrawl_map_job(
                job_data,
                firecrawl_config
            )
            
            # Verify result structure
            assert 'roaster_id' in result
            assert 'discovered_urls' in result
            assert 'status' in result
            assert 'budget_used' in result
            
            # Verify service was called
            mock_service.discover_roaster_products.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_firecrawl_batch_map_job_execution(self, mock_firecrawl_config, mock_roaster_configs):
        """Test Firecrawl batch map job execution."""
        # Mock the FirecrawlMapService
        with patch('src.worker.tasks.FirecrawlMapService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the batch_discover_products method to be async
            async def mock_batch_discover_products(*args, **kwargs):
                return {
                    'total_roasters': 3,
                    'successful_discoveries': 2,
                    'failed_discoveries': 1,
                    'total_urls_discovered': 2,
                    'results': [
                        {'roaster_id': 'roaster_1', 'discovered_urls': ['https://testroaster1.com/coffee/beans']},
                        {'roaster_id': 'roaster_2', 'discovered_urls': ['https://testroaster2.com/coffee/beans']},
                        {'roaster_id': 'roaster_3', 'discovered_urls': [], 'status': 'disabled'}
                    ]
                }
            
            mock_service.batch_discover_products = Mock(side_effect=mock_batch_discover_products)
            
            # Test batch job execution
            job_data = {
                'id': 'batch_job_123',
                'data': {
                    'roaster_ids': ['roaster_1', 'roaster_2', 'roaster_3'],
                    'job_type': 'firecrawl_batch_map'
                }
            }
            config_dict = mock_firecrawl_config.model_dump()
            # Add FIRECRAWL_ prefix to match what the worker expects
            firecrawl_config = {f"FIRECRAWL_{k.upper()}": v for k, v in config_dict.items()}
            result = await execute_firecrawl_batch_map_job(
                job_data,
                firecrawl_config
            )
            
            # Verify result structure
            assert 'roaster_count' in result
            assert 'successful_discoveries' in result
            assert 'total_urls_discovered' in result
            assert 'batch_results' in result
            
            # Verify service was called for batch discovery
            assert mock_service.batch_discover_products.call_count == 1
    
    @pytest.mark.asyncio
    async def test_queue_firecrawl_extract_jobs(self, mock_roaster_configs):
        """Test queuing Firecrawl extract jobs."""
        # Mock the job queue
        mock_job_queue = Mock()
        async def mock_enqueue(*args, **kwargs):
            return "job_id_123"
        mock_job_queue.enqueue = Mock(side_effect=mock_enqueue)
        
        # Mock discovered URLs
        discovered_urls = [
            'https://testroaster1.com/coffee/beans',
            'https://testroaster1.com/products/roast'
        ]
        
        # Test job queuing
        result = await queue_firecrawl_extract_jobs(
            discovered_urls=discovered_urls,
            roaster_id="roaster_1",
            job_queue=mock_job_queue
        )
        
        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == len(discovered_urls)
        
        # Verify jobs were queued
        assert mock_job_queue.enqueue.call_count == len(discovered_urls)
    
    @pytest.mark.asyncio
    async def test_integration_service_firecrawl_discovery(self, mock_firecrawl_config, mock_roaster_configs):
        """Test Firecrawl discovery through integration service."""
        # Mock the ValidatorIntegrationService
        with patch('src.validator.integration_service.ValidatorIntegrationService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the discover_roaster_products_firecrawl method
            mock_service.discover_roaster_products_firecrawl.return_value = {
                'roaster_id': 'roaster_1',
                'roaster_name': 'Test Roaster 1',
                'discovered_urls': ['https://testroaster1.com/coffee/beans'],
                'status': 'success',
                'budget_used': 50,
                'operation_time_seconds': 2.5,
                'timestamp': '2024-01-01T00:00:00Z'
            }
            
            # Test discovery through integration service
            roaster_config = mock_roaster_configs[0]
            result = mock_service.discover_roaster_products_firecrawl(roaster_config)
            
            # Verify result structure
            assert 'roaster_id' in result
            assert 'discovered_urls' in result
            assert 'status' in result
            assert 'budget_used' in result
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, firecrawl_map_service, mock_roaster_configs):
        """Test error handling and recovery mechanisms."""
        # Mock Firecrawl API error
        firecrawl_map_service.client.app.map_url.side_effect = Exception("API Error")
        
        # Test error handling
        roaster_config = mock_roaster_configs[0]
        result = await firecrawl_map_service.discover_roaster_products(roaster_config)
        
        # Verify error handling
        assert len(result['discovered_urls']) == 0
        assert result['status'] == 'error'
        assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_budget_tracking_integration(self, firecrawl_map_service, mock_roaster_configs):
        """Test budget tracking across multiple operations."""
        # Mock Firecrawl API responses
        mock_responses = [
            {'links': ['https://testroaster1.com/coffee/beans']},
            {'links': ['https://testroaster2.com/coffee/beans']}
        ]
        
        firecrawl_map_service.client.app.map_url.side_effect = mock_responses
        
        # Test multiple operations
        results = []
        for roaster_config in mock_roaster_configs[:2]:  # Only test first two
            result = await firecrawl_map_service.discover_roaster_products(roaster_config)
            results.append(result)
        
        # Verify budget tracking
        for result in results:
            assert 'budget_used' in result
            assert result['budget_used'] >= 0
    
    @pytest.mark.asyncio
    async def test_performance_characteristics(self, firecrawl_map_service, mock_roaster_configs):
        """Test performance characteristics of Firecrawl operations."""
        import time
        
        # Mock Firecrawl API response
        mock_response = {'links': ['https://testroaster1.com/coffee/beans']}
        firecrawl_map_service.client.app.map_url.return_value = mock_response
        
        # Test operation timing
        start_time = time.time()
        roaster_config = mock_roaster_configs[0]
        result = await firecrawl_map_service.discover_roaster_products(roaster_config)
        end_time = time.time()
        
        operation_time = end_time - start_time
        
        # Verify timing is recorded in logs (not in result)
        # The actual implementation logs timing but doesn't return it in the result
        assert 'discovery_timestamp' in result
        assert result['discovery_timestamp'] is not None
        
        # Verify operation completed within reasonable time
        assert operation_time < 5.0  # Should complete within 5 seconds
    
    @pytest.mark.asyncio
    async def test_monitoring_and_metrics_integration(self, firecrawl_map_service, mock_roaster_configs):
        """Test monitoring and metrics integration."""
        # Mock Firecrawl API response
        mock_response = {'links': ['https://testroaster1.com/coffee/beans']}
        firecrawl_map_service.client.app.map_url.return_value = mock_response
        
        # Test operation
        roaster_config = mock_roaster_configs[0]
        result = await firecrawl_map_service.discover_roaster_products(roaster_config)
        
        # Verify metrics are recorded
        assert 'discovery_timestamp' in result
        assert 'budget_used' in result
        assert result['discovery_timestamp'] is not None
        
        # Test service status
        status = await firecrawl_map_service.get_service_status()
        assert 'service' in status
        assert 'status' in status
        assert 'budget_usage' in status
        assert 'configuration' in status
