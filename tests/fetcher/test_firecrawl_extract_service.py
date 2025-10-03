"""
Tests for Firecrawl extract service with JavaScript rendering and dropdown interaction.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.fetcher.firecrawl_extract_service import FirecrawlExtractService
from src.fetcher.firecrawl_client import FirecrawlClient, FirecrawlAPIError
from src.parser.normalizer_pipeline import NormalizerPipelineService
from src.config.pipeline_config import PipelineConfig


class TestFirecrawlExtractService:
    """Test cases for Firecrawl extract service."""
    
    @pytest.fixture
    def mock_firecrawl_client(self):
        """Mock Firecrawl client."""
        client = Mock(spec=FirecrawlClient)
        client.extract_coffee_product = AsyncMock()
        client.get_usage_stats = Mock(return_value={'budget_used': 10, 'budget_limit': 100})
        client.get_health_status = Mock(return_value={'status': 'healthy'})
        return client
    
    @pytest.fixture
    def mock_normalizer_pipeline(self):
        """Mock normalizer pipeline."""
        pipeline = Mock(spec=NormalizerPipelineService)
        pipeline.process_artifact = Mock()
        return pipeline
    
    @pytest.fixture
    def extract_service(self, mock_firecrawl_client, mock_normalizer_pipeline):
        """Firecrawl extract service with mocked dependencies."""
        return FirecrawlExtractService(mock_firecrawl_client, mock_normalizer_pipeline)
    
    @pytest.fixture
    def sample_firecrawl_data(self):
        """Sample Firecrawl extraction data."""
        return {
            "name": "Ethiopian Yirgacheffe",
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
            "description": "Bright and floral Ethiopian coffee with citrus notes.",
            "tasting_notes": ["citrus", "floral", "bright"],
            "images": [
                "https://example.com/image1.jpg",
                "https://example.com/image2.jpg"
            ]
        }
    
    @pytest.fixture
    def sample_normalized_result(self):
        """Sample normalized result from pipeline."""
        return {
            'execution_id': 'test-123',
            'stage': 'completed',
            'processing_time': 1.5,
            'deterministic_results': {
                'weight': {'success': True, 'confidence': 0.9},
                'roast': {'success': True, 'confidence': 0.8}
            },
            'overall_confidence': 0.85
        }
    
    @pytest.mark.asyncio
    async def test_extract_coffee_product_success(self, extract_service, sample_firecrawl_data, sample_normalized_result):
        """Test successful coffee product extraction."""
        # Setup mocks
        extract_service.client.extract_coffee_product.return_value = sample_firecrawl_data
        extract_service.normalizer_pipeline.process_artifact.return_value = sample_normalized_result
        
        # Test extraction
        url = "https://example.com/coffee-product"
        result = await extract_service.extract_coffee_product_with_pricing(url)
        
        # Verify client was called correctly
        extract_service.client.extract_coffee_product.assert_called_once()
        call_args = extract_service.client.extract_coffee_product.call_args
        assert call_args[0][0] == url  # URL
        assert '250g' in call_args[0][1]  # size_options
        assert '1kg' in call_args[0][1]
        
        # Verify actions were built for dropdown interaction
        actions = call_args[0][2]
        assert len(actions) > 0
        assert any(action.get('type') == 'click' for action in actions)
        assert any(action.get('type') == 'screenshot' for action in actions)
        
        # Verify schema was provided
        schema = call_args[0][3]
        assert schema['type'] == 'object'
        assert 'price_variations' in schema['properties']
        
        # Verify result structure
        assert result['success'] is True
        assert 'raw_data' in result
        assert 'artifact' in result
        assert 'normalized_result' in result
        assert result['raw_data'] == sample_firecrawl_data
        assert result['normalized_result'] == sample_normalized_result
    
    @pytest.mark.asyncio
    async def test_extract_coffee_product_with_custom_sizes(self, extract_service, sample_firecrawl_data, sample_normalized_result):
        """Test extraction with custom size options."""
        # Setup mocks
        extract_service.client.extract_coffee_product.return_value = sample_firecrawl_data
        extract_service.normalizer_pipeline.process_artifact.return_value = sample_normalized_result
        
        # Test with custom sizes
        url = "https://example.com/coffee-product"
        custom_sizes = ['100g', '500g', '1kg']
        result = await extract_service.extract_coffee_product_with_pricing(url, custom_sizes)
        
        # Verify custom sizes were used
        call_args = extract_service.client.extract_coffee_product.call_args
        assert call_args[0][1] == custom_sizes
        
        # Verify actions were built for custom sizes
        actions = call_args[0][2]
        size_actions = [action for action in actions if action.get('type') == 'click' and 'option:contains' in action.get('selector', '')]
        assert len(size_actions) == len(custom_sizes)
    
    @pytest.mark.asyncio
    async def test_extract_coffee_product_client_error(self, extract_service):
        """Test extraction when Firecrawl client fails."""
        # Setup client to raise error
        extract_service.client.extract_coffee_product.side_effect = FirecrawlAPIError("API error")
        
        # Test extraction should raise error
        url = "https://example.com/coffee-product"
        with pytest.raises(FirecrawlAPIError, match="Extraction failed"):
            await extract_service.extract_coffee_product_with_pricing(url)
    
    @pytest.mark.asyncio
    async def test_extract_coffee_product_normalizer_error(self, extract_service, sample_firecrawl_data):
        """Test extraction when normalizer pipeline fails."""
        # Setup mocks
        extract_service.client.extract_coffee_product.return_value = sample_firecrawl_data
        extract_service.normalizer_pipeline.process_artifact.side_effect = Exception("Normalizer error")
        
        # Test extraction should raise error
        url = "https://example.com/coffee-product"
        with pytest.raises(FirecrawlAPIError, match="Extraction failed"):
            await extract_service.extract_coffee_product_with_pricing(url)
    
    def test_build_dropdown_actions(self, extract_service):
        """Test dropdown actions building."""
        size_options = ['250g', '500g', '1kg']
        actions = extract_service._build_dropdown_actions(size_options)
        
        # Verify actions structure
        assert len(actions) > 0
        
        # Check for wait actions
        wait_actions = [action for action in actions if action.get('type') == 'wait']
        assert len(wait_actions) > 0
        
        # Check for click actions
        click_actions = [action for action in actions if action.get('type') == 'click']
        assert len(click_actions) > 0
        
        # Check for screenshot actions
        screenshot_actions = [action for action in actions if action.get('type') == 'screenshot']
        assert len(screenshot_actions) > 0
        
        # Verify size options are included in selectors
        for size in size_options:
            size_selectors = [action for action in actions if f"option:contains('{size}')" in action.get('selector', '')]
            assert len(size_selectors) > 0
    
    def test_get_coffee_extraction_schema(self, extract_service):
        """Test coffee extraction schema generation."""
        schema = extract_service._get_coffee_extraction_schema()
        
        # Verify schema structure
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'required' in schema
        
        # Check required fields
        assert 'name' in schema['required']
        assert 'price_variations' in schema['required']
        
        # Check properties
        properties = schema['properties']
        assert 'name' in properties
        assert 'roaster' in properties
        assert 'origin' in properties
        assert 'roast_level' in properties
        assert 'price_variations' in properties
        assert 'description' in properties
        assert 'tasting_notes' in properties
        assert 'images' in properties
    
    def test_convert_coffee_artifact(self, extract_service, sample_firecrawl_data):
        """Test Firecrawl data to canonical artifact conversion."""
        url = "https://example.com/coffee-product"
        artifact = extract_service._convert_coffee_artifact(sample_firecrawl_data, url)
        
        # Verify artifact structure
        assert artifact['source'] == 'firecrawl'
        assert artifact['roaster_domain'] == 'example.com'
        assert 'scraped_at' in artifact
        assert 'product' in artifact
        assert 'normalization' in artifact
        
        # Verify product data
        product = artifact['product']
        assert product['platform_product_id'] is not None
        assert product['title'] == sample_firecrawl_data['name']
        assert product['source_url'] == url
        assert product['description_html'] == sample_firecrawl_data['description']
        assert len(product['variants']) == len(sample_firecrawl_data['price_variations'])
        assert len(product['images']) == len(sample_firecrawl_data['images'])
        
        # Verify variants
        variants = product['variants']
        for i, variant in enumerate(variants):
            assert variant['platform_variant_id'] == f"firecrawl_{i}"
            assert variant['title'] == sample_firecrawl_data['price_variations'][i]['size']
            assert variant['price'] == sample_firecrawl_data['price_variations'][i]['price']
            assert variant['currency'] == sample_firecrawl_data['price_variations'][i]['currency']
    
    def test_extract_product_id_from_data(self, extract_service):
        """Test product ID extraction from raw data."""
        raw_data = {"id": "product-123", "name": "Test Coffee"}
        source_url = "https://example.com/coffee"
        
        product_id = extract_service._extract_product_id(raw_data, source_url)
        assert product_id == "product-123"
    
    def test_extract_product_id_from_url(self, extract_service):
        """Test product ID extraction from URL when not in data."""
        raw_data = {"name": "Test Coffee"}
        source_url = "https://example.com/coffee/test-product"
        
        product_id = extract_service._extract_product_id(raw_data, source_url)
        assert product_id == "test-product"
    
    def test_extract_product_id_fallback(self, extract_service):
        """Test product ID fallback to hash."""
        raw_data = {"name": "Test Coffee"}
        source_url = "https://example.com/"
        
        product_id = extract_service._extract_product_id(raw_data, source_url)
        assert product_id is not None
        assert isinstance(product_id, str)
    
    def test_extract_tags(self, extract_service):
        """Test tag extraction from Firecrawl data."""
        raw_data = {
            "roaster": "Blue Bottle",
            "origin": "Ethiopia",
            "roast_level": "Light",
            "tasting_notes": ["citrus", "floral", "bright"]
        }
        
        tags = extract_service._extract_tags(raw_data)
        
        # Verify tags
        assert f"roaster:{raw_data['roaster']}" in tags
        assert f"origin:{raw_data['origin']}" in tags
        assert f"roast:{raw_data['roast_level']}" in tags
        
        # Verify tasting notes
        for note in raw_data['tasting_notes']:
            assert f"tasting:{note}" in tags
    
    def test_convert_images(self, extract_service):
        """Test image URL conversion."""
        image_urls = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "  https://example.com/image3.jpg  "  # Test whitespace handling
        ]
        
        images = extract_service._convert_images(image_urls)
        
        assert len(images) == 3
        
        for i, image in enumerate(images):
            assert image['url'] == image_urls[i].strip()
            assert image['alt_text'] == f"Product image {i + 1}"
            assert image['order'] == i
            assert image['source_id'] == f"firecrawl_{i}"
    
    def test_convert_variants(self, extract_service):
        """Test price variations to variants conversion."""
        price_variations = [
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
                "availability": "out_of_stock"
            }
        ]
        
        variants = extract_service._convert_variants(price_variations)
        
        assert len(variants) == 2
        
        # Check first variant
        variant1 = variants[0]
        assert variant1['platform_variant_id'] == "firecrawl_0"
        assert variant1['title'] == "250g"
        assert variant1['price'] == "$18.00"
        assert variant1['currency'] == "USD"
        assert variant1['in_stock'] is True
        assert variant1['grams'] == 250
        assert variant1['weight_unit'] == "g"
        
        # Check second variant
        variant2 = variants[1]
        assert variant2['platform_variant_id'] == "firecrawl_1"
        assert variant2['title'] == "500g"
        assert variant2['price'] == "$32.00"
        assert variant2['currency'] == "USD"
        assert variant2['in_stock'] is False
        assert variant2['grams'] == 500
        assert variant2['weight_unit'] == "g"
    
    def test_extract_weight_from_size(self, extract_service):
        """Test weight extraction from size strings."""
        # Test grams
        assert extract_service._extract_weight_from_size("250g") == 250
        assert extract_service._extract_weight_from_size("500g") == 500
        
        # Test kilograms
        assert extract_service._extract_weight_from_size("1kg") == 1000
        assert extract_service._extract_weight_from_size("2.5kg") == 2500
        
        # Test pounds
        assert extract_service._extract_weight_from_size("1lb") == 453
        assert extract_service._extract_weight_from_size("2.5lb") == 1133
        
        # Test no match
        assert extract_service._extract_weight_from_size("Large") is None
        assert extract_service._extract_weight_from_size("") is None
        assert extract_service._extract_weight_from_size(None) is None
    
    @pytest.mark.asyncio
    async def test_extract_batch_products_success(self, extract_service, sample_firecrawl_data, sample_normalized_result):
        """Test batch product extraction."""
        # Setup mocks
        extract_service.client.extract_coffee_product.return_value = sample_firecrawl_data
        extract_service.normalizer_pipeline.process_artifact.return_value = sample_normalized_result
        
        # Test batch extraction
        urls = [
            "https://example.com/coffee1",
            "https://example.com/coffee2",
            "https://example.com/coffee3"
        ]
        
        results = await extract_service.extract_batch_products(urls)
        
        # Verify results
        assert len(results) == 3
        
        for i, result in enumerate(results):
            assert result['url'] == urls[i]
            assert result['success'] is True
            assert 'result' in result
    
    @pytest.mark.asyncio
    async def test_extract_batch_products_with_failures(self, extract_service, sample_firecrawl_data, sample_normalized_result):
        """Test batch extraction with some failures."""
        # Setup mocks - fail on second URL
        def mock_extract(url, *args, **kwargs):
            if "coffee2" in url:
                raise FirecrawlAPIError("Extraction failed")
            return sample_firecrawl_data
        
        extract_service.client.extract_coffee_product.side_effect = mock_extract
        extract_service.normalizer_pipeline.process_artifact.return_value = sample_normalized_result
        
        # Test batch extraction
        urls = [
            "https://example.com/coffee1",
            "https://example.com/coffee2",
            "https://example.com/coffee3"
        ]
        
        results = await extract_service.extract_batch_products(urls)
        
        # Verify results
        assert len(results) == 3
        
        # First and third should succeed
        assert results[0]['success'] is True
        assert results[2]['success'] is True
        
        # Second should fail
        assert results[1]['success'] is False
        assert 'error' in results[1]
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, extract_service):
        """Test health check when service is healthy."""
        # Setup mocks
        extract_service.client.extract_coffee_product.return_value = {"name": "Test"}
        extract_service.normalizer_pipeline.process_artifact.return_value = {}
        
        # Test health check
        is_healthy = await extract_service.health_check()
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, extract_service):
        """Test health check when service is unhealthy."""
        # Setup mocks to fail
        extract_service.client.extract_coffee_product.side_effect = Exception("Service down")
        
        # Test health check
        is_healthy = await extract_service.health_check()
        assert is_healthy is False
    
    def test_get_usage_stats(self, extract_service):
        """Test usage stats retrieval."""
        stats = extract_service.get_usage_stats()
        
        # Should delegate to client
        extract_service.client.get_usage_stats.assert_called_once()
        assert stats == {'budget_used': 10, 'budget_limit': 100}
    
    def test_get_health_status(self, extract_service):
        """Test health status retrieval."""
        status = extract_service.get_health_status()
        
        # Should delegate to client
        extract_service.client.get_health_status.assert_called_once()
        assert status == {'status': 'healthy'}


class TestFirecrawlExtractServiceIntegration:
    """Integration tests for Firecrawl extract service."""
    
    @pytest.mark.asyncio
    async def test_full_extraction_workflow(self):
        """Test complete extraction workflow with real dependencies."""
        # This would be an integration test with actual Firecrawl API
        # For now, we'll test the workflow with mocked dependencies
        pass
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery during extraction."""
        # This would test retry logic and error handling
        pass
