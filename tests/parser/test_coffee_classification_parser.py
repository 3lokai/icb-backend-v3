"""
Tests for coffee classification parser.
"""

import pytest
from pytest import mark
from unittest.mock import Mock, patch
from src.parser.coffee_classification_parser import CoffeeClassificationParser, ClassificationResult


class TestCoffeeClassificationParser:
    """Test cases for coffee classification parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CoffeeClassificationParser()
    
    @pytest.mark.asyncio

    
    async def test_coffee_product_classification(self):
        """Test classification of obvious coffee products."""
        # Test coffee beans
        product = {
            "title": "Ethiopian Yirgacheffe Single Origin Coffee Beans",
            "product_type": "coffee",
            "tags": ["arabica", "single origin", "ethiopia"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert result.is_coffee is True
        assert result.confidence >= 0.7
        assert result.method in ["code_based", "product_type"]
        assert "coffee" in result.reasoning.lower()
    
    @pytest.mark.asyncio

    
    async def test_equipment_product_classification(self):
        """Test classification of equipment products."""
        # Test coffee grinder
        product = {
            "title": "Baratza Encore Coffee Grinder",
            "product_type": "equipment",
            "tags": ["grinder", "coffee equipment"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert result.is_coffee is False
        assert result.confidence == 1.0
        assert result.method == "hard_exclusion"
        assert "equipment" in result.reasoning.lower()
    
    @pytest.mark.asyncio

    
    async def test_gift_set_classification(self):
        """Test classification of gift sets."""
        # Test gift set
        product = {
            "title": "Coffee Lover's Gift Set - 3 Coffee Varieties",
            "product_type": "gift",
            "tags": ["gift", "set", "coffee"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert result.is_coffee is False
        assert result.confidence == 1.0
        assert result.method == "hard_exclusion"
        assert "gift" in result.reasoning.lower()
    
    @pytest.mark.asyncio

    
    async def test_training_classification(self):
        """Test classification of training/educational products."""
        # Test workshop
        product = {
            "title": "Coffee Roasting Workshop - Learn to Roast",
            "product_type": "education",
            "tags": ["workshop", "training", "coffee"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert result.is_coffee is False
        assert result.confidence == 1.0
        assert result.method == "hard_exclusion"
        assert "workshop" in result.reasoning.lower() or "hard exclusion" in result.reasoning.lower()
    
    @pytest.mark.asyncio

    
    async def test_woocommerce_classification(self):
        """Test classification with WooCommerce data structure."""
        # Test WooCommerce product
        product = {
            "name": "Kenya AA Coffee Beans",
            "type": "simple",
            "categories": [{"name": "Coffee"}],
            "tags": [{"name": "arabica"}, {"name": "kenya"}]
        }
        
        result = await self.parser.classify_product(product, "woo")
        
        # This should be classified as coffee due to strong coffee indicators
        assert result.is_coffee is True
        assert result.confidence >= 0.7
        assert result.method in ["code_based", "product_type"]
    
    @pytest.mark.asyncio

    
    async def test_contextual_exclusions(self):
        """Test contextual exclusions for specific equipment."""
        # Test French press filter papers
        product = {
            "title": "French Press Filter Papers - 100 Pack",
            "product_type": "accessories",
            "tags": ["french press", "filter", "papers"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert result.is_coffee is False
        assert result.confidence == 1.0
        assert result.method in ["contextual_exclusion", "hard_exclusion"]
    
    @pytest.mark.asyncio

    
    async def test_brewing_context_coffee(self):
        """Test brewing method mentions in coffee context."""
        # Test espresso blend
        product = {
            "title": "Espresso Blend - Dark Roast Coffee",
            "product_type": "coffee",
            "tags": ["espresso", "blend", "dark roast"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert result.is_coffee is True
        assert result.confidence >= 0.7
        assert result.method in ["code_based", "product_type"]
    
    @pytest.mark.asyncio

    
    async def test_soft_exclusions(self):
        """Test soft exclusions when no coffee indicators present."""
        # Test generic equipment without coffee context
        product = {
            "title": "Digital Scale - Precision Weighing",
            "product_type": "equipment",
            "tags": ["scale", "precision", "weighing"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert result.is_coffee is False
        assert result.confidence <= 1.0
        assert result.method in ["low_confidence_skip", "code_based", "hard_exclusion"]
    
    @pytest.mark.asyncio

    
    async def test_llm_fallback(self):
        """Test LLM fallback for medium confidence cases."""
        # Mock LLM service
        mock_llm = Mock()
        mock_llm.classify_coffee_product.return_value = {
            "is_coffee": True,
            "confidence": 0.8,
            "reasoning": "LLM determined this is coffee"
        }
        
        parser_with_llm = CoffeeClassificationParser(llm_service=mock_llm)
        
        # Test ambiguous product
        product = {
            "title": "Artisan Coffee Blend - Limited Edition",
            "product_type": "beverage",
            "tags": ["artisan", "limited", "special"]
        }
        
        result = await parser_with_llm.classify_product(product, "shopify")
        
        assert result.is_coffee is True
        assert result.confidence >= 0.6
        assert result.method in ["llm_fallback", "code_based"]
        assert "LLM" in result.reasoning or "confidence" in result.reasoning
    
    @pytest.mark.asyncio

    
    async def test_llm_fallback_low_confidence(self):
        """Test LLM fallback with low confidence result."""
        # Mock LLM service with low confidence
        mock_llm = Mock()
        mock_llm.classify_coffee_product.return_value = {
            "is_coffee": False,
            "confidence": 0.4,
            "reasoning": "LLM uncertain, defaulting to equipment"
        }
        
        parser_with_llm = CoffeeClassificationParser(llm_service=mock_llm)
        
        # Test ambiguous product
        product = {
            "title": "Mystery Product - Unknown Category",
            "product_type": "other",
            "tags": ["mystery", "unknown"]
        }
        
        result = await parser_with_llm.classify_product(product, "shopify")
        
        assert result.is_coffee is False
        assert result.confidence < 0.6
        assert result.method == "low_confidence_skip"
    
    @pytest.mark.asyncio

    
    async def test_llm_service_unavailable(self):
        """Test behavior when LLM service is unavailable."""
        # Test without LLM service
        product = {
            "title": "Ambiguous Product Name",
            "product_type": "unknown",
            "tags": ["ambiguous"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert result.is_coffee is False
        assert result.method == "low_confidence_skip"
    
    @pytest.mark.asyncio

    
    async def test_batch_classification(self):
        """Test batch classification of multiple products."""
        products = [
            {
                "title": "Ethiopian Coffee Beans",
                "product_type": "coffee",
                "tags": ["arabica", "ethiopia"]
            },
            {
                "title": "Coffee Grinder Machine",
                "product_type": "equipment",
                "tags": ["grinder", "machine"]
            },
            {
                "title": "Coffee Gift Set",
                "product_type": "gift",
                "tags": ["gift", "set"]
            }
        ]
        
        results = await self.parser.batch_classify_products(products, "shopify")
        
        assert len(results) == 3
        assert results[0].is_coffee is True  # Coffee beans
        assert results[1].is_coffee is False  # Grinder
        assert results[2].is_coffee is False  # Gift set
    
    @pytest.mark.asyncio

    
    async def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Empty product data
        product = {}
        result = await self.parser.classify_product(product, "shopify")
        assert result.is_coffee is False
        
        # Product with only spaces
        product = {"title": "   ", "product_type": "", "tags": []}
        result = await self.parser.classify_product(product, "shopify")
        assert result.is_coffee is False
        
        # Product with None values
        product = {"title": None, "product_type": None, "tags": None}
        result = await self.parser.classify_product(product, "shopify")
        assert result.is_coffee is False
    
    @pytest.mark.asyncio

    
    async def test_confidence_scoring(self):
        """Test confidence scoring for different scenarios."""
        # High confidence coffee
        product = {
            "title": "Single Origin Arabica Coffee Beans",
            "product_type": "coffee",
            "tags": ["arabica", "single origin"]
        }
        result = await self.parser.classify_product(product, "shopify")
        assert result.confidence >= 0.7
        
        # Medium confidence (should trigger LLM if available)
        product = {
            "title": "Artisan Blend",
            "product_type": "beverage",
            "tags": ["artisan"]
        }
        result = await self.parser.classify_product(product, "shopify")
        assert 0.3 <= result.confidence <= 0.7
        
        # Low confidence
        product = {
            "title": "Unknown Product",
            "product_type": "other",
            "tags": []
        }
        result = await self.parser.classify_product(product, "shopify")
        assert result.confidence < 0.3
    
    @pytest.mark.asyncio

    
    async def test_warnings_generation(self):
        """Test that appropriate warnings are generated."""
        # Test with warnings
        product = {
            "title": "Low Confidence Product",
            "product_type": "unknown",
            "tags": []
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        if result.method == "low_confidence_skip":
            assert len(result.warnings) > 0
            assert "low confidence" in result.warnings[0].lower()
    
    @pytest.mark.asyncio

    
    async def test_reasoning_quality(self):
        """Test that reasoning is informative and helpful."""
        # Test coffee product
        product = {
            "title": "Ethiopian Coffee Beans",
            "product_type": "coffee",
            "tags": ["arabica"]
        }
        
        result = await self.parser.classify_product(product, "shopify")
        
        assert len(result.reasoning) > 0
        assert "confidence" in result.reasoning.lower() or "coffee" in result.reasoning.lower()
    
    @pytest.mark.asyncio

    
    async def test_method_tracking(self):
        """Test that classification method is properly tracked."""
        # Test different methods
        test_cases = [
            ({"title": "Coffee Grinder", "product_type": "equipment", "tags": []}, "hard_exclusion"),
            ({"title": "Ethiopian Coffee", "product_type": "coffee", "tags": []}, "product_type"),
            ({"title": "Coffee Beans", "product_type": "beverage", "tags": ["arabica"]}, ["code_based", "low_confidence_skip"])
        ]
        
        for product, expected_method in test_cases:
            result = await self.parser.classify_product(product, "shopify")
            if isinstance(expected_method, list):
                assert result.method in expected_method
            else:
                assert result.method == expected_method

    @pytest.mark.asyncio


    async def test_real_sample_data_coffee_products(self):
        """Test with real coffee products from sample data."""
        # Real coffee product from Rosette Coffee (Shopify)
        # Note: This product has confidence 0.65, which triggers LLM fallback
        # Since LLM is not available in tests, it defaults to equipment
        coffee_product = {
            'title': 'Nagaland Tuensang Washed AA',
            'product_type': 'Single Origin',
            'tags': ['arabica', 'single-origin', 'washed'],
            'vendor': 'Rosette Coffee'
        }
        result = await self.parser.classify_product(coffee_product, 'shopify')
        # This should now be classified as coffee due to improved confidence calculation
        assert result.is_coffee is True
        assert result.confidence >= 0.7
        assert result.method in ['code_based', 'product_type']
        assert 'high confidence' in result.reasoning.lower() or 'coffee' in result.reasoning.lower()
        
        # Real coffee product from Baba Beans (WooCommerce)
        coffee_product_woo = {
            'name': 'Hustler',
            'type': 'variable',
            'categories': [{'name': 'COLD BREW', 'slug': 'cold-brew'}],
            'tags': [],
            'short_description': 'Region : Coorg, Karnataka\nElevation: 2800 Ft - 3600 Ft ASL\nType : Cold Brewed Coffee\nStrength : 3/4\nRoast Profile : Dark Roast\nVariety : Arabica & Robusta'
        }
        result = await self.parser.classify_product(coffee_product_woo, 'woocommerce')
        # This should be classified as coffee due to strong coffee indicators
        assert result.is_coffee is True
        assert result.confidence >= 0.7
        assert result.method in ['code_based', 'product_type']
        assert 'high confidence' in result.reasoning.lower() or 'coffee' in result.reasoning.lower()

    @pytest.mark.asyncio


    async def test_real_sample_data_equipment_products(self):
        """Test with real equipment products from sample data."""
        # Real equipment product from Rosette Coffee (Shopify)
        equipment_product = {
            'title': 'Timemore Chestnut C2 Manual Grinder',
            'product_type': 'Equipment',
            'tags': ['grinder', 'manual', 'equipment'],
            'vendor': 'Rosette Coffee'
        }
        result = await self.parser.classify_product(equipment_product, 'shopify')
        assert result.is_coffee is False
        assert result.confidence >= 0.7
        assert result.method in ['hard_exclusion', 'contextual_exclusion']
        assert 'equipment' in result.reasoning.lower() or 'grinder' in result.reasoning.lower()

    @pytest.mark.asyncio


    async def test_real_sample_data_gift_products(self):
        """Test with real gift products from sample data."""
        # Real gift product from Blue Tokai (Shopify)
        gift_product = {
            'title': 'Meghmalhar Gift Hamper',
            'product_type': 'Gifting',
            'tags': ['not_express', 'TAX_18'],
            'vendor': 'Blue Tokai Coffee Roasters'
        }
        result = await self.parser.classify_product(gift_product, 'shopify')
        assert result.is_coffee is False
        assert result.confidence >= 0.7
        assert result.method in ['hard_exclusion', 'contextual_exclusion']
        assert 'gift' in result.reasoning.lower() or 'hamper' in result.reasoning.lower()

    @pytest.mark.asyncio


    async def test_real_sample_data_coffee_grind_variants(self):
        """Test with real coffee grind variants from sample data."""
        # Real coffee grind variant from Rosette Coffee (Shopify)
        # This should be classified as coffee due to "whole beans" and "arabica"
        grind_variant = {
            'title': '200g / Whole Beans',
            'product_type': 'Single Origin',
            'tags': ['arabica', 'whole-beans'],
            'vendor': 'Rosette Coffee'
        }
        result = await self.parser.classify_product(grind_variant, 'shopify')
        assert result.is_coffee is True
        assert result.confidence >= 0.7
        assert result.method in ['code_based', 'product_type']
        assert 'high confidence' in result.reasoning.lower() or 'coffee' in result.reasoning.lower()
        
        # French Press grind variant (should still be coffee due to brewing context)
        french_press_variant = {
            'title': '200g / Cold Brew / Channi / French Press',
            'product_type': 'Single Origin',
            'tags': ['arabica', 'french-press', 'cold-brew'],
            'vendor': 'Rosette Coffee'
        }
        result = await self.parser.classify_product(french_press_variant, 'shopify')
        assert result.is_coffee is True
        assert result.confidence >= 0.7
        assert result.method in ['code_based', 'product_type']
        assert 'high confidence' in result.reasoning.lower() or 'coffee' in result.reasoning.lower()

    @pytest.mark.asyncio


    async def test_real_sample_data_mixed_context(self):
        """Test with real products that have mixed coffee/equipment context."""
        # Product that mentions both coffee and equipment
        mixed_product = {
            'title': 'Coffee Filter Papers',
            'product_type': 'Accessories',
            'tags': ['filter', 'papers', 'coffee'],
            'vendor': 'Blue Tokai Coffee Roasters'
        }
        result = await self.parser.classify_product(mixed_product, 'shopify')
        # Should be classified as equipment due to contextual exclusion
        assert result.is_coffee is False
        assert result.confidence >= 0.7
        assert result.method in ['contextual_exclusion', 'hard_exclusion']
        assert 'equipment' in result.reasoning.lower() or 'filter' in result.reasoning.lower()
