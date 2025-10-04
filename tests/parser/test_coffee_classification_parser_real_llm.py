"""Test coffee classification parser with real LLM service (not mocked)."""

import pytest
import asyncio
from unittest.mock import Mock
from src.parser.coffee_classification_parser import CoffeeClassificationParser, ClassificationResult
from src.llm.deepseek_wrapper import DeepSeekWrapperService
from src.config.deepseek_config import DeepSeekConfig
from src.llm.cache_service import CacheService
from src.config.cache_config import CacheConfig
from src.llm.rate_limiter import RateLimiter
from src.llm.llm_metrics import LLMServiceMetrics


class TestCoffeeClassificationParserRealLLM:
    """Test coffee classification with real LLM service."""
    
    @pytest.fixture
    def llm_service(self):
        """Create a real LLM service for testing."""
        # Check if we have API key
        import os
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY not set - skipping real LLM test")
        
        # Create real LLM service
        config = DeepSeekConfig(
            api_key=api_key,
            model="deepseek-chat",
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=200
        )
        
        cache_config = CacheConfig(backend="memory")
        cache_service = CacheService(cache_config)
        rate_limiter = RateLimiter({
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000
        })
        metrics = LLMServiceMetrics()
        
        return DeepSeekWrapperService(config, cache_service, rate_limiter, metrics)
    
    @pytest.fixture
    def parser_with_llm(self, llm_service):
        """Create parser with real LLM service."""
        return CoffeeClassificationParser(llm_service=llm_service)
    
    @pytest.mark.asyncio
    async def test_real_llm_classification_ambiguous_product(self, parser_with_llm):
        """Test LLM classification with an ambiguous product that needs LLM fallback."""
        # This product has medium confidence (0.3-0.7) and should trigger LLM fallback
        # Using a product that mentions coffee but isn't clearly coffee or equipment
        product_data = {
            "title": "Artisan Beverage Experience",
            "product_type": "Beverage",
            "tags": ["artisan", "experience", "premium"],
            "description": "Premium beverage experience with curated flavors"
        }
        
        result = await parser_with_llm.classify_product(product_data, "shopify")
        
        # Should use LLM fallback for ambiguous cases
        assert result.method == "llm_fallback"
        assert result.confidence >= 0.5  # LLM should be confident
        assert isinstance(result.is_coffee, bool)
        assert "LLM classification" in result.reasoning or "LLM" in result.reasoning
        
        print(f"Real LLM Result: {result.is_coffee} (confidence: {result.confidence})")
        print(f"Reasoning: {result.reasoning}")
    
    @pytest.mark.asyncio
    async def test_real_llm_classification_edge_case(self, parser_with_llm):
        """Test LLM classification with a complex edge case."""
        # Complex product that could go either way
        product_data = {
            "name": "Coffee Bean Storage Container with Grinder Attachment",
            "product_type": "Accessory",
            "tags": ["storage", "container", "grinder", "coffee", "beans"],
            "description": "Premium storage solution for coffee beans with integrated grinding mechanism"
        }
        
        result = await parser_with_llm.classify_product(product_data, "shopify")
        
        # Should use LLM fallback
        assert result.method == "llm_fallback"
        assert result.confidence >= 0.5
        assert isinstance(result.is_coffee, bool)
        
        print(f"Real LLM Result: {result.is_coffee} (confidence: {result.confidence})")
        print(f"Reasoning: {result.reasoning}")
    
    @pytest.mark.asyncio
    async def test_real_llm_classification_woocommerce_data(self, parser_with_llm):
        """Test LLM classification with WooCommerce data structure."""
        # WooCommerce product that needs LLM analysis
        product_data = {
            "name": "Artisan Coffee Roasting Workshop Kit",
            "type": "variable",
            "categories": [{"name": "Education"}, {"name": "Coffee Accessories"}],
            "tags": [{"name": "workshop"}, {"name": "roasting"}, {"name": "education"}],
            "short_description": "Complete kit for learning coffee roasting at home",
            "description": "Includes green beans, roasting guide, and cupping materials"
        }
        
        result = await parser_with_llm.classify_product(product_data, "woo")
        
        # Should use LLM fallback
        assert result.method == "llm_fallback"
        assert result.confidence >= 0.5
        assert isinstance(result.is_coffee, bool)
        
        print(f"Real LLM Result: {result.is_coffee} (confidence: {result.confidence})")
        print(f"Reasoning: {result.reasoning}")
    
    @pytest.mark.asyncio
    async def test_real_llm_service_health_check(self, llm_service):
        """Test that the real LLM service is healthy and available."""
        health = llm_service.get_service_health()
        
        assert health['available'] is True
        assert health['provider'] == 'deepseek'
        assert 'model' in health
        
        print(f"LLM Service Health: {health}")
    
    @pytest.mark.asyncio
    async def test_real_llm_classification_direct_call(self, llm_service):
        """Test direct LLM service classification method."""
        context = {
            "name": "Specialty Coffee Cupping Set",
            "product_type": "Accessory",
            "tags": ["cupping", "coffee", "tasting", "professional"],
            "description": "Professional cupping set for coffee tasting and evaluation"
        }
        
        result = await llm_service.classify_coffee_product(context)
        
        assert 'is_coffee' in result
        assert 'confidence' in result
        assert 'reasoning' in result
        assert isinstance(result['is_coffee'], bool)
        assert 0.0 <= result['confidence'] <= 1.0
        assert isinstance(result['reasoning'], str)
        
        print(f"Direct LLM Result: {result}")


if __name__ == "__main__":
    # Run a simple test if executed directly
    import os
    
    async def main():
        # Check for API key
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            print("DEEPSEEK_API_KEY not set. Set it to run real LLM tests.")
            return
        
        # Create real LLM service
        config = DeepSeekConfig(api_key=api_key, model="deepseek-chat", temperature=0.1)
        cache_config = CacheConfig(backend="memory")
        cache_service = CacheService(cache_config)
        rate_limiter = RateLimiter({
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000
        })
        metrics = LLMServiceMetrics()
        llm_service = DeepSeekWrapperService(config, cache_service, rate_limiter, metrics)
        
        # Test health
        health = llm_service.get_service_health()
        print(f"LLM Service Health: {health}")
        
        # Test direct classification
        context = {
            "name": "Ethiopian Yirgacheffe Single Origin Coffee",
            "product_type": "Coffee",
            "tags": ["single-origin", "ethiopia", "arabica"],
            "description": "Premium single origin coffee from Yirgacheffe region"
        }
        
        result = await llm_service.classify_coffee_product(context)
        print(f"Direct LLM Classification: {result}")
        
        # Test with parser
        parser = CoffeeClassificationParser(llm_service=llm_service)
        product_data = {
            "name": "Coffee Workshop Training Course",
            "product_type": "Digital Product",
            "tags": ["training", "coffee", "education"],
            "description": "Learn coffee brewing techniques"
        }
        
        result = await parser.classify_product(product_data, "shopify")
        print(f"Parser with Real LLM: {result}")
    
    asyncio.run(main())
