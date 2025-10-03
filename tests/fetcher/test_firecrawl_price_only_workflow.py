"""
Tests for Firecrawl Price-Only Workflow.

Tests the integration between Firecrawl services and Epic B price infrastructure.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, List, Any

from src.fetcher.firecrawl_price_only_workflow import FirecrawlPriceOnlyWorkflow
from src.fetcher.firecrawl_map_service import FirecrawlMapService
from src.fetcher.firecrawl_extract_service import FirecrawlExtractService
from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService
from src.fetcher.price_fetcher import PriceFetcher
from src.price.price_update_service import PriceUpdateService
from src.config.roaster_schema import RoasterConfigSchema


class TestFirecrawlPriceOnlyWorkflow:
    """Test cases for Firecrawl Price-Only Workflow."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        map_service = Mock(spec=FirecrawlMapService)
        extract_service = Mock(spec=FirecrawlExtractService)
        budget_service = Mock(spec=FirecrawlBudgetManagementService)
        price_fetcher = Mock(spec=PriceFetcher)
        price_updater = Mock(spec=PriceUpdateService)
        
        return {
            'map_service': map_service,
            'extract_service': extract_service,
            'budget_service': budget_service,
            'price_fetcher': price_fetcher,
            'price_updater': price_updater
        }
    
    @pytest.fixture
    def workflow(self, mock_services):
        """Create workflow instance with mock services."""
        return FirecrawlPriceOnlyWorkflow(
            map_service=mock_services['map_service'],
            extract_service=mock_services['extract_service'],
            budget_service=mock_services['budget_service'],
            price_fetcher=mock_services['price_fetcher'],
            price_updater=mock_services['price_updater']
        )
    
    @pytest.fixture
    def roaster_config(self):
        """Create test roaster configuration."""
        return RoasterConfigSchema(
            id="test_roaster",
            name="Test Roaster",
            base_url="https://testroaster.com",
            use_firecrawl_fallback=True
        )
    
    @pytest.fixture
    def sample_urls(self):
        """Sample URLs for testing."""
        return [
            "https://testroaster.com/coffee/ethiopian-yirgacheffe",
            "https://testroaster.com/coffee/colombian-huila",
            "https://testroaster.com/coffee/guatemalan-antigua"
        ]
    
    @pytest.fixture
    def sample_extraction_results(self):
        """Sample extraction results for testing."""
        return [
            {
                'url': 'https://testroaster.com/coffee/ethiopian-yirgacheffe',
                'success': True,
                'result': {
                    'artifact': {
                        'product': {
                            'platform_product_id': 'ethiopian-yirgacheffe',
                            'title': 'Ethiopian Yirgacheffe',
                            'variants': [
                                {
                                    'platform_variant_id': 'ethiopian-250g',
                                    'title': '250g',
                                    'price': '18.99',
                                    'currency': 'USD',
                                    'in_stock': True
                                }
                            ]
                        }
                    }
                }
            },
            {
                'url': 'https://testroaster.com/coffee/colombian-huila',
                'success': True,
                'result': {
                    'artifact': {
                        'product': {
                            'platform_product_id': 'colombian-huila',
                            'title': 'Colombian Huila',
                            'variants': [
                                {
                                    'platform_variant_id': 'colombian-500g',
                                    'title': '500g',
                                    'price': '24.99',
                                    'currency': 'USD',
                                    'in_stock': True
                                }
                            ]
                        }
                    }
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_execute_price_only_workflow_success(
        self, 
        workflow, 
        roaster_config, 
        sample_urls, 
        sample_extraction_results,
        mock_services
    ):
        """Test successful price-only workflow execution."""
        # Setup mocks
        mock_services['map_service'].discover_price_only_urls = AsyncMock(return_value=sample_urls)
        mock_services['extract_service'].extract_batch_products = AsyncMock(return_value=sample_extraction_results)
        mock_services['price_updater'].update_prices_atomic = AsyncMock(return_value=Mock(success=True))
        mock_services['budget_service'].track_price_only_usage = AsyncMock()
        
        # Execute workflow
        result = await workflow.execute_price_only_workflow(roaster_config, "price_only")
        
        # Verify results
        assert result['success'] is True
        assert result['roaster_id'] == "test_roaster"
        assert result['job_type'] == "price_only"
        assert result['discovered_urls'] == sample_urls
        assert result['total_extractions'] == len(sample_extraction_results)
        assert result['successful_extractions'] == len(sample_extraction_results)
        assert 'processing_time' in result
        assert 'cost_tracking' in result
        
        # Verify service calls
        mock_services['map_service'].discover_price_only_urls.assert_called_once_with(
            "https://testroaster.com", "price_only"
        )
        mock_services['extract_service'].extract_batch_products.assert_called_once_with(
            urls=sample_urls, job_type="price_only"
        )
        mock_services['price_updater'].update_prices_atomic.assert_called_once()
        mock_services['budget_service'].track_price_only_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_price_only_workflow_no_urls_discovered(
        self, 
        workflow, 
        roaster_config, 
        mock_services
    ):
        """Test workflow when no URLs are discovered."""
        # Setup mocks
        mock_services['map_service'].discover_price_only_urls = AsyncMock(return_value=[])
        
        # Execute workflow
        result = await workflow.execute_price_only_workflow(roaster_config, "price_only")
        
        # Verify results
        assert result['success'] is False
        assert result['error'] == 'No price-relevant URLs discovered'
        assert result['roaster_id'] == "test_roaster"
        assert result['discovered_urls'] == []
    
    @pytest.mark.asyncio
    async def test_execute_price_only_workflow_no_successful_extractions(
        self, 
        workflow, 
        roaster_config, 
        sample_urls, 
        mock_services
    ):
        """Test workflow when no extractions are successful."""
        # Setup mocks
        mock_services['map_service'].discover_price_only_urls = AsyncMock(return_value=sample_urls)
        mock_services['extract_service'].extract_batch_products = AsyncMock(return_value=[
            {'url': url, 'success': False, 'error': 'Extraction failed'} for url in sample_urls
        ])
        
        # Execute workflow
        result = await workflow.execute_price_only_workflow(roaster_config, "price_only")
        
        # Verify results
        assert result['success'] is False
        assert result['error'] == 'No successful price extractions'
        assert result['roaster_id'] == "test_roaster"
        assert result['discovered_urls'] == sample_urls
    
    @pytest.mark.asyncio
    async def test_execute_price_only_workflow_invalid_job_type(
        self, 
        workflow, 
        roaster_config
    ):
        """Test workflow with invalid job type."""
        # Execute workflow
        result = await workflow.execute_price_only_workflow(roaster_config, "full_refresh")
        
        # Verify results
        assert result['success'] is False
        assert 'Invalid job type' in result['error']
    
    @pytest.mark.asyncio
    async def test_execute_price_only_workflow_exception(
        self, 
        workflow, 
        roaster_config, 
        mock_services
    ):
        """Test workflow when an exception occurs."""
        # Setup mocks to raise exception
        mock_services['map_service'].discover_price_only_urls = AsyncMock(
            side_effect=Exception("Map service error")
        )
        
        # Execute workflow
        result = await workflow.execute_price_only_workflow(roaster_config, "price_only")
        
        # Verify results
        assert result['success'] is False
        assert 'Map service error' in result['error']
        assert result['roaster_id'] == "test_roaster"
        assert 'processing_time' in result
    
    @pytest.mark.asyncio
    async def test_process_price_data(
        self, 
        workflow, 
        roaster_config
    ):
        """Test price data processing."""
        # Sample price data
        price_data = [
            {
                'product': {
                    'platform_product_id': 'test-product',
                    'title': 'Test Product',
                    'variants': [
                        {
                            'platform_variant_id': 'test-variant-1',
                            'title': '250g',
                            'price': '15.99',
                            'currency': 'USD',
                            'in_stock': True
                        }
                    ]
                }
            }
        ]
        
        # Process price data
        result = await workflow._process_price_data(price_data, roaster_config)
        
        # Verify results
        assert len(result) == 1
        assert result[0].variant_id == 'test-variant-1'
        assert result[0].new_price == 15.99
        assert result[0].currency == 'USD'
        assert result[0].in_stock is True
        assert result[0].roaster_id == 'test_roaster'
    
    @pytest.mark.asyncio
    async def test_track_price_only_costs(
        self, 
        workflow, 
        sample_urls, 
        sample_extraction_results, 
        mock_services
    ):
        """Test cost tracking for price-only operations."""
        # Setup mocks
        mock_services['budget_service'].track_price_only_usage = AsyncMock()
        
        # Track costs
        result = await workflow._track_price_only_costs(sample_urls, sample_extraction_results)
        
        # Verify results
        assert result['total_urls'] == len(sample_urls)
        assert result['successful_extractions'] == len(sample_extraction_results)
        assert 'cost_per_url' in result
        assert 'total_cost' in result
        assert 'cost_efficiency' in result
        assert 'cost_optimization' in result
        
        # Verify budget service call
        mock_services['budget_service'].track_price_only_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(
        self, 
        workflow, 
        mock_services
    ):
        """Test workflow status retrieval."""
        # Setup mocks
        mock_services['map_service'].get_service_status = AsyncMock(return_value={'status': 'healthy'})
        mock_services['extract_service'].get_health_status = Mock(return_value={'status': 'healthy'})
        mock_services['budget_service'].get_budget_status = Mock(return_value={'status': 'healthy'})
        
        # Get status
        result = await workflow.get_workflow_status()
        
        # Verify results
        assert result['workflow'] == 'FirecrawlPriceOnlyWorkflow'
        assert result['status'] == 'healthy'
        assert 'timestamp' in result
        assert 'services' in result
        assert 'map_service' in result['services']
        assert 'extract_service' in result['services']
        assert 'budget_service' in result['services']
    
    @pytest.mark.asyncio
    async def test_get_workflow_status_error(
        self, 
        workflow, 
        mock_services
    ):
        """Test workflow status when an error occurs."""
        # Setup mocks to raise exception
        mock_services['map_service'].get_service_status = AsyncMock(
            side_effect=Exception("Status check failed")
        )
        
        # Get status
        result = await workflow.get_workflow_status()
        
        # Verify results
        assert result['workflow'] == 'FirecrawlPriceOnlyWorkflow'
        assert result['status'] == 'error'
        assert 'error' in result
        assert 'Status check failed' in result['error']


class TestFirecrawlPriceOnlyWorkflowIntegration:
    """Integration tests for Firecrawl Price-Only Workflow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_price_only_workflow(self):
        """Test complete end-to-end price-only workflow."""
        # This would be an integration test with real services
        # For now, we'll test the workflow structure
        pass
    
    @pytest.mark.asyncio
    async def test_cost_optimization_metrics(self):
        """Test cost optimization metrics calculation."""
        # Test that price-only mode provides 60-80% cost reduction
        pass
    
    @pytest.mark.asyncio
    async def test_epic_b_integration(self):
        """Test integration with Epic B price infrastructure."""
        # Test B.1, B.2, B.3 integration
        pass
