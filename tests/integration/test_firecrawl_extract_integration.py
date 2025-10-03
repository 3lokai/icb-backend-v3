"""
Integration tests for Firecrawl extract service with real API and normalizer pipeline.
"""

import pytest
import asyncio
from unittest.mock import patch, Mock
from datetime import datetime, timezone

from src.fetcher.firecrawl_extract_service import FirecrawlExtractService
from src.fetcher.firecrawl_client import FirecrawlClient
from src.parser.normalizer_pipeline import NormalizerPipelineService
from src.config.pipeline_config import PipelineConfig
from src.config.firecrawl_config import FirecrawlConfig


class TestFirecrawlExtractIntegration:
    """Integration tests for Firecrawl extract service."""
    
    @pytest.fixture
    def firecrawl_config(self):
        """Firecrawl configuration for testing."""
        return FirecrawlConfig(
            api_key="test-api-key",
            base_url="https://api.firecrawl.dev",
            budget_limit=1000,
            rate_limit_per_minute=10,
            max_retries=3,
            retry_delay=1.0
        )
    
    @pytest.fixture
    def pipeline_config(self):
        """Pipeline configuration for testing."""
        return PipelineConfig(
            enable_weight_parsing=True,
            enable_roast_parsing=True,
            enable_process_parsing=True,
            enable_tag_parsing=True,
            enable_notes_parsing=True,
            enable_grind_parsing=True,
            enable_species_parsing=True,
            enable_variety_parsing=True,
            enable_geographic_parsing=True,
            enable_sensory_parsing=True,
            enable_hash_generation=True,
            enable_text_cleaning=True,
            enable_text_normalization=True,
            llm_fallback_threshold=0.7,
            enable_metrics=True
        )
    
    @pytest.fixture
    def firecrawl_client(self, firecrawl_config):
        """Firecrawl client with configuration."""
        return FirecrawlClient(firecrawl_config)
    
    @pytest.fixture
    def normalizer_pipeline(self, pipeline_config):
        """Normalizer pipeline with configuration."""
        return NormalizerPipelineService(pipeline_config)
    
    @pytest.fixture
    def extract_service(self, firecrawl_client, normalizer_pipeline):
        """Firecrawl extract service with real dependencies."""
        return FirecrawlExtractService(firecrawl_client, normalizer_pipeline)
    
    @pytest.fixture
    def sample_coffee_urls(self):
        """Sample coffee product URLs for testing."""
        return [
            "https://bluebottlecoffee.com/us/products/ethiopia-yirgacheffe",
            "https://stumptowncoffee.com/products/ethiopia-yirgacheffe",
            "https://intelligentsia.com/products/ethiopia-yirgacheffe"
        ]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extract_real_coffee_product(self, extract_service, sample_coffee_urls):
        """Test extraction with real coffee product URL (mocked Firecrawl API)."""
        # Mock the Firecrawl API response
        mock_firecrawl_response = {
            "name": "Ethiopia Yirgacheffe",
            "roaster": "Blue Bottle Coffee",
            "origin": "Ethiopia",
            "roast_level": "Light",
            "price_variations": [
                {
                    "size": "250g",
                    "price": "$18.00",
                    "currency": "USD",
                    "availability": "in_stock"
                },
                {
                    "size": "500g",
                    "price": "$32.00",
                    "currency": "USD",
                    "availability": "in_stock"
                }
            ],
            "description": "Bright and floral Ethiopian coffee with citrus notes and clean finish.",
            "tasting_notes": ["citrus", "floral", "bright", "clean"],
            "images": [
                "https://bluebottlecoffee.com/images/ethiopia-yirgacheffe-1.jpg",
                "https://bluebottlecoffee.com/images/ethiopia-yirgacheffe-2.jpg"
            ]
        }
        
        # Mock the Firecrawl client
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.return_value = mock_firecrawl_response
            
            # Test extraction
            url = sample_coffee_urls[0]
            result = await extract_service.extract_coffee_product_with_pricing(url)
            
            # Verify extraction was called
            mock_extract.assert_called_once()
            
            # Verify result structure
            assert result['success'] is True
            assert 'raw_data' in result
            assert 'artifact' in result
            assert 'normalized_result' in result
            
            # Verify artifact structure
            artifact = result['artifact']
            assert artifact['source'] == 'firecrawl'
            assert artifact['roaster_domain'] == 'bluebottlecoffee.com'
            assert 'scraped_at' in artifact
            assert 'product' in artifact
            
            # Verify product data
            product = artifact['product']
            assert product['title'] == mock_firecrawl_response['name']
            assert product['source_url'] == url
            assert len(product['variants']) == 2
            assert len(product['images']) == 2
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_extraction_workflow(self, extract_service, sample_coffee_urls):
        """Test batch extraction workflow."""
        # Mock Firecrawl responses for different URLs
        mock_responses = [
            {
                "name": "Ethiopia Yirgacheffe",
                "roaster": "Blue Bottle Coffee",
                "price_variations": [{"size": "250g", "price": "$18.00", "currency": "USD", "availability": "in_stock"}],
                "description": "Bright and floral",
                "tasting_notes": ["citrus", "floral"],
                "images": ["https://example.com/image1.jpg"]
            },
            {
                "name": "Ethiopia Yirgacheffe",
                "roaster": "Stumptown Coffee",
                "price_variations": [{"size": "500g", "price": "$32.00", "currency": "USD", "availability": "in_stock"}],
                "description": "Complex and layered",
                "tasting_notes": ["chocolate", "nutty"],
                "images": ["https://example.com/image2.jpg"]
            },
            {
                "name": "Ethiopia Yirgacheffe",
                "roaster": "Intelligentsia",
                "price_variations": [{"size": "1kg", "price": "$60.00", "currency": "USD", "availability": "in_stock"}],
                "description": "Elegant and refined",
                "tasting_notes": ["jasmine", "bergamot"],
                "images": ["https://example.com/image3.jpg"]
            }
        ]
        
        # Mock the Firecrawl client to return different responses
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.side_effect = mock_responses
            
            # Test batch extraction
            results = await extract_service.extract_batch_products(sample_coffee_urls)
            
            # Verify results
            assert len(results) == 3
            
            for i, result in enumerate(results):
                assert result['url'] == sample_coffee_urls[i]
                assert result['success'] is True
                assert 'result' in result
                
                # Verify each result has correct roaster
                artifact = result['result']['artifact']
                product = artifact['product']
                assert product['title'] == mock_responses[i]['name']
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extraction_with_dropdown_interaction(self, extract_service):
        """Test extraction with dropdown interaction for pricing variations."""
        url = "https://example.com/coffee-with-dropdown"
        
        # Mock Firecrawl response with multiple price variations
        mock_response = {
            "name": "Colombian Supremo",
            "roaster": "Test Roaster",
            "price_variations": [
                {"size": "250g", "price": "$15.00", "currency": "USD", "availability": "in_stock"},
                {"size": "500g", "price": "$28.00", "currency": "USD", "availability": "in_stock"},
                {"size": "1kg", "price": "$50.00", "currency": "USD", "availability": "in_stock"}
            ],
            "description": "Rich and full-bodied Colombian coffee",
            "tasting_notes": ["chocolate", "caramel", "nutty"],
            "images": ["https://example.com/colombian.jpg"]
        }
        
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.return_value = mock_response
            
            # Test extraction with custom size options
            custom_sizes = ['250g', '500g', '1kg', '2kg']
            result = await extract_service.extract_coffee_product_with_pricing(url, custom_sizes)
            
            # Verify extraction was called with custom sizes
            call_args = mock_extract.call_args
            assert call_args[0][1] == custom_sizes  # size_options
            
            # Verify actions were built for dropdown interaction
            actions = call_args[0][2]
            assert len(actions) > 0
            
            # Check for dropdown interaction actions
            click_actions = [action for action in actions if action.get('type') == 'click']
            assert len(click_actions) > 0
            
            # Check for screenshot actions
            screenshot_actions = [action for action in actions if action.get('type') == 'screenshot']
            assert len(screenshot_actions) > 0
            
            # Verify result
            assert result['success'] is True
            artifact = result['artifact']
            product = artifact['product']
            assert len(product['variants']) == 3  # All price variations captured
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_normalizer_pipeline_integration(self, extract_service):
        """Test integration with normalizer pipeline."""
        url = "https://example.com/coffee-for-normalization"
        
        # Mock Firecrawl response with rich data for normalization
        mock_response = {
            "name": "Kenya AA Nyeri",
            "roaster": "Artisan Coffee Co",
            "origin": "Kenya",
            "roast_level": "Medium",
            "price_variations": [
                {"size": "250g", "price": "$22.00", "currency": "USD", "availability": "in_stock"}
            ],
            "description": "Bright acidity with notes of black currant and wine. Grown at 1800m altitude in Nyeri region.",
            "tasting_notes": ["black currant", "wine", "bright acidity", "full body"],
            "images": ["https://example.com/kenya-aa.jpg"]
        }
        
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.return_value = mock_response
            
            # Mock normalizer pipeline result
            mock_normalized_result = {
                'execution_id': 'test-123',
                'stage': 'completed',
                'processing_time': 2.5,
                'deterministic_results': {
                    'weight': {'success': True, 'confidence': 0.9, 'result_data': {'weight_g': 250}},
                    'roast': {'success': True, 'confidence': 0.8, 'result_data': {'roast_level': 'medium'}},
                    'geographic': {'success': True, 'confidence': 0.9, 'result_data': {'country': 'Kenya', 'region': 'Nyeri'}},
                    'sensory': {'success': True, 'confidence': 0.7, 'result_data': {'acidity': 8.5, 'body': 7.0}}
                },
                'overall_confidence': 0.85
            }
            
            with patch.object(extract_service.normalizer_pipeline, 'process_artifact') as mock_normalize:
                mock_normalize.return_value = mock_normalized_result
                
                # Test extraction
                result = await extract_service.extract_coffee_product_with_pricing(url)
                
                # Verify normalizer was called
                mock_normalize.assert_called_once()
                
                # Verify normalized result
                assert result['normalized_result'] == mock_normalized_result
                
                # Verify artifact was passed to normalizer
                call_args = mock_normalize.call_args
                artifact = call_args[0][0]
                assert artifact['source'] == 'firecrawl'
                assert artifact['product']['title'] == mock_response['name']
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_and_recovery(self, extract_service):
        """Test error handling and recovery during extraction."""
        url = "https://example.com/problematic-coffee"
        
        # Test API error
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.side_effect = Exception("Firecrawl API error")
            
            with pytest.raises(Exception, match="Extraction failed"):
                await extract_service.extract_coffee_product_with_pricing(url)
        
        # Test normalizer error
        mock_response = {"name": "Test Coffee", "price_variations": []}
        
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.return_value = mock_response
            
            with patch.object(extract_service.normalizer_pipeline, 'process_artifact') as mock_normalize:
                mock_normalize.side_effect = Exception("Normalizer error")
                
                with pytest.raises(Exception, match="Extraction failed"):
                    await extract_service.extract_coffee_product_with_pricing(url)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_budget_tracking_integration(self, extract_service):
        """Test budget tracking during extraction."""
        url = "https://example.com/coffee-budget-test"
        
        # Mock successful extraction
        mock_response = {
            "name": "Budget Test Coffee",
            "price_variations": [{"size": "250g", "price": "$10.00", "currency": "USD", "availability": "in_stock"}],
            "description": "Test coffee for budget tracking",
            "tasting_notes": ["test"],
            "images": []
        }
        
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.return_value = mock_response
            
            # Test extraction
            result = await extract_service.extract_coffee_product_with_pricing(url)
            
            # Verify extraction was called (which should track budget)
            mock_extract.assert_called_once()
            
            # Verify result
            assert result['success'] is True
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_metrics_integration(self, extract_service):
        """Test performance metrics during extraction."""
        url = "https://example.com/coffee-performance-test"
        
        # Mock successful extraction
        mock_response = {
            "name": "Performance Test Coffee",
            "price_variations": [{"size": "250g", "price": "$12.00", "currency": "USD", "availability": "in_stock"}],
            "description": "Test coffee for performance metrics",
            "tasting_notes": ["performance"],
            "images": []
        }
        
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.return_value = mock_response
            
            # Test extraction
            result = await extract_service.extract_coffee_product_with_pricing(url)
            
            # Verify processing time is recorded
            assert 'processing_time' in result
            assert isinstance(result['processing_time'], (int, float))
            assert result['processing_time'] > 0
            
            # Verify success flag
            assert result['success'] is True
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_integration(self, extract_service):
        """Test health check integration."""
        # Mock successful health check
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.return_value = {"name": "Health Test"}
            
            with patch.object(extract_service.normalizer_pipeline, 'process_artifact') as mock_normalize:
                mock_normalize.return_value = {}
                
                # Test health check
                is_healthy = await extract_service.health_check()
                assert is_healthy is True
        
        # Mock failed health check
        with patch.object(extract_service.client, 'extract_coffee_product') as mock_extract:
            mock_extract.side_effect = Exception("Service down")
            
            # Test health check
            is_healthy = await extract_service.health_check()
            assert is_healthy is False
