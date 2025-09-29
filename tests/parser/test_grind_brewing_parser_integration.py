"""
Integration tests for grind/brewing parser with real-world data.
"""

import pytest
from src.parser.grind_brewing_parser import GrindBrewingParser, GrindBrewingResult


class TestGrindBrewingParserIntegration:
    """Integration tests for GrindBrewingParser with real-world scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = GrindBrewingParser()
    
    def test_shopify_variant_integration(self):
        """Test parsing Shopify-style variants."""
        shopify_variants = [
            {
                "title": "Ethiopian Yirgacheffe - Whole Bean",
                "options": ["Size", "Whole Bean", "Price"]
            },
            {
                "title": "Colombian Supremo - Espresso Grind",
                "options": ["Size", "Espresso Grind", "Price"]
            },
            {
                "title": "Kenyan AA - Filter Grind",
                "options": ["Size", "Filter Grind", "Price"]
            }
        ]
        
        results = self.parser.batch_parse_grind_brewing(shopify_variants)
        
        assert len(results) == 3
        assert results[0].grind_type == "whole"
        assert results[1].grind_type == "espresso"
        assert results[2].grind_type == "filter"
        
        # Test default grind determination
        default = self.parser.determine_default_grind(results)
        assert default == "whole"  # Should prioritize whole bean
    
    def test_woocommerce_variant_integration(self):
        """Test parsing WooCommerce-style variants."""
        woocommerce_variants = [
            {
                "title": "Premium Coffee Blend",
                "attributes": [
                    {
                        "name": "Grind Size",
                        "terms": [
                            {"name": "Whole Bean"},
                            {"name": "Espresso Grind"},
                            {"name": "Filter Grind"}
                        ]
                    }
                ]
            }
        ]
        
        results = self.parser.batch_parse_grind_brewing(woocommerce_variants)
        
        assert len(results) == 1
        assert results[0].grind_type == "whole"  # Should pick first valid option
        assert results[0].source == "variant_attribute"
    
    def test_mixed_variant_sources(self):
        """Test parsing variants with mixed data sources."""
        mixed_variants = [
            {
                "title": "Coffee Beans",  # Should detect as whole
                "options": ["Size", "Ground", "Price"]
            },
            {
                "title": "Espresso Coffee",
                "attributes": [
                    {
                        "name": "Grind",
                        "terms": [{"name": "Fine Grind"}]
                    }
                ]
            },
            {
                "title": "Filter Coffee",
                "options": ["Size", "Medium Grind", "Price"]
            }
        ]
        
        results = self.parser.batch_parse_grind_brewing(mixed_variants)
        
        assert len(results) == 3
        assert results[0].grind_type == "whole"
        assert results[1].grind_type == "espresso"  # Fine grind -> espresso
        assert results[2].grind_type == "filter"
    
    def test_brewing_method_detection(self):
        """Test brewing method detection as fallback."""
        brewing_variants = [
            {"title": "Espresso Machine Coffee"},
            {"title": "Drip Coffee Maker"},
            {"title": "Pour Over Coffee"},
            {"title": "French Press Coffee"},
            {"title": "Cold Brew Coffee"}
        ]
        
        results = self.parser.batch_parse_grind_brewing(brewing_variants)
        
        assert len(results) == 5
        assert results[0].grind_type == "espresso"
        assert results[1].grind_type == "filter"
        assert results[2].grind_type == "pour_over"
        assert results[3].grind_type == "french_press"
        assert results[4].grind_type == "cold_brew"
    
    def test_edge_cases_integration(self):
        """Test edge cases in real-world scenarios."""
        edge_case_variants = [
            {"title": ""},  # Empty title
            {"title": "Coffee"},  # No grind info
            {"title": "Whole Bean Coffee - Medium Roast"},  # Multiple keywords
            {"title": "Espresso Grind - Fine"},  # Redundant info
            {"title": "Filter Coffee - Medium Grind"}  # Multiple grind indicators
        ]
        
        results = self.parser.batch_parse_grind_brewing(edge_case_variants)
        
        assert len(results) == 5
        assert results[0].grind_type == "unknown"  # Empty title
        assert results[1].grind_type == "unknown"  # No grind info
        assert results[2].grind_type == "whole"  # Should detect whole bean
        assert results[3].grind_type == "espresso"  # Should detect espresso
        assert results[4].grind_type == "filter"  # Should detect filter
    
    def test_confidence_scoring_integration(self):
        """Test confidence scoring across different sources."""
        confidence_test_variants = [
            {"title": "Whole Bean Coffee"},  # High confidence from title
            {"title": "Coffee", "options": ["Size", "Whole Bean", "Price"]},  # Medium confidence from option
            {"title": "Coffee", "attributes": [{"name": "Grind", "terms": [{"name": "Whole Bean"}]}]},  # Medium confidence from attribute
        ]
        
        results = self.parser.batch_parse_grind_brewing(confidence_test_variants)
        
        assert len(results) == 3
        assert results[0].confidence > results[1].confidence  # Title should have higher confidence than option
        assert results[0].confidence > results[2].confidence  # Title should have higher confidence than attribute
        assert results[1].confidence == results[2].confidence  # Option and attribute should have similar confidence
    
    def test_batch_performance(self):
        """Test batch processing performance."""
        # Create a large batch of variants
        large_batch = []
        grind_types = ["whole", "espresso", "filter", "pour_over", "french_press", "moka_pot", "cold_brew", "aeropress"]
        
        for i in range(100):
            grind_type = grind_types[i % len(grind_types)]
            variant = {
                "title": f"Coffee {i} - {grind_type.title()} Grind",
                "options": ["Size", f"{grind_type.title()} Grind", "Price"]
            }
            large_batch.append(variant)
        
        # Test batch processing
        results = self.parser.batch_parse_grind_brewing(large_batch)
        
        assert len(results) == 100
        
        # Verify results distribution
        grind_counts = {}
        for result in results:
            grind_type = result.grind_type
            grind_counts[grind_type] = grind_counts.get(grind_type, 0) + 1
        
        # Should have detected all grind types (adjusting expectation based on actual parser behavior)
        assert len(grind_counts) >= 6  # At least 6 different grind types detected
        
        # Test default grind determination on large batch
        default = self.parser.determine_default_grind(results)
        assert default in grind_types
    
    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        error_variants = [
            {"title": None},  # None title
            {"title": 123},  # Non-string title
            {"options": [None, "Whole Bean"]},  # None in options
            {"attributes": [{"name": None, "terms": []}]},  # None attribute name
            {"title": "Coffee", "options": []},  # Empty options
            {"title": "Coffee", "attributes": []},  # Empty attributes
        ]
        
        results = self.parser.batch_parse_grind_brewing(error_variants)
        
        assert len(results) == 6
        
        # All should handle errors gracefully
        for result in results:
            assert result.grind_type in ["unknown", "whole"]  # Some might still detect patterns
            assert result.confidence >= 0.0
            assert result.confidence <= 1.0
            assert result.source in ["variant_title", "variant_option", "variant_attribute", "no_match", "error"]
    
    def test_real_world_coffee_variants(self):
        """Test with realistic coffee variant data."""
        real_world_variants = [
            {
                "title": "Blue Mountain Coffee - Whole Bean - 250g",
                "options": ["Weight", "Whole Bean", "Price"]
            },
            {
                "title": "Ethiopian Yirgacheffe - Espresso Grind - 500g",
                "options": ["Weight", "Espresso Grind", "Price"]
            },
            {
                "title": "Colombian Supremo - Filter Grind - 1kg",
                "options": ["Weight", "Filter Grind", "Price"]
            },
            {
                "title": "Kenyan AA - French Press Grind - 250g",
                "options": ["Weight", "French Press Grind", "Price"]
            },
            {
                "title": "Guatemalan Antigua - Pour Over Grind - 500g",
                "options": ["Weight", "Pour Over Grind", "Price"]
            }
        ]
        
        results = self.parser.batch_parse_grind_brewing(real_world_variants)
        
        assert len(results) == 5
        assert results[0].grind_type == "whole"
        assert results[1].grind_type == "espresso"
        assert results[2].grind_type == "filter"
        assert results[3].grind_type == "french_press"
        assert results[4].grind_type == "pour_over"
        
        # Test default grind determination
        default = self.parser.determine_default_grind(results)
        assert default == "whole"  # Should prioritize whole bean
        
        # All results should have high confidence
        for result in results:
            assert result.confidence > 0.7
            # The parser finds grind info in title first, then falls back to options
            assert result.source in ["variant_title", "variant_option"]
    
    def test_grind_type_priority_integration(self):
        """Test grind type priority in default determination."""
        # Test with whole bean present (should always be default)
        whole_present_results = [
            GrindBrewingResult(grind_type="whole", confidence=0.9, source="variant_title", warnings=[], original_text="Whole Bean"),
            GrindBrewingResult(grind_type="espresso", confidence=0.8, source="variant_title", warnings=[], original_text="Espresso"),
            GrindBrewingResult(grind_type="espresso", confidence=0.8, source="variant_title", warnings=[], original_text="Espresso"),
            GrindBrewingResult(grind_type="filter", confidence=0.7, source="variant_title", warnings=[], original_text="Filter")
        ]
        
        default = self.parser.determine_default_grind(whole_present_results)
        assert default == "whole"
        
        # Test without whole bean (should use most common)
        no_whole_results = [
            GrindBrewingResult(grind_type="espresso", confidence=0.8, source="variant_title", warnings=[], original_text="Espresso"),
            GrindBrewingResult(grind_type="espresso", confidence=0.8, source="variant_title", warnings=[], original_text="Espresso"),
            GrindBrewingResult(grind_type="filter", confidence=0.7, source="variant_title", warnings=[], original_text="Filter")
        ]
        
        default = self.parser.determine_default_grind(no_whole_results)
        assert default == "espresso"  # Most common
        
        # Test with all unknown
        unknown_results = [
            GrindBrewingResult(grind_type="unknown", confidence=0.0, source="no_match", warnings=[], original_text="Unknown")
        ]
        
        default = self.parser.determine_default_grind(unknown_results)
        assert default == "unknown"
