"""
Tests for tag normalization service.
"""

import pytest
from src.parser.tag_normalization import TagNormalizationService, TagNormalizationResult


class TestTagNormalizationService:
    """Test cases for TagNormalizationService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TagNormalizationService()
    
    def test_initialization(self):
        """Test service initialization."""
        assert self.service is not None
        assert len(self.service.category_mapping) > 0
        assert len(self.service.tag_to_category) > 0
        assert len(self.service.fuzzy_patterns) > 0
    
    def test_normalize_tags_empty_input(self):
        """Test normalization with empty input."""
        result = self.service.normalize_tags([])
        
        assert isinstance(result, TagNormalizationResult)
        assert result.normalized_tags == {}
        assert result.confidence_scores == {}
        assert result.warnings == ['No tags provided']
        assert result.total_tags == 0
        assert result.normalized_count == 0
    
    def test_normalize_tags_valid_tags(self):
        """Test normalization with valid tags."""
        raw_tags = ['chocolate', 'caramel', 'karnataka', 'light', 'washed']
        result = self.service.normalize_tags(raw_tags)
        
        assert isinstance(result, TagNormalizationResult)
        assert result.total_tags == 5
        assert result.normalized_count > 0
        assert len(result.normalized_tags) > 0
        assert len(result.confidence_scores) > 0
    
    def test_normalize_tags_flavor_category(self):
        """Test normalization of flavor tags."""
        raw_tags = ['chocolate', 'caramel', 'vanilla', 'nutty']
        result = self.service.normalize_tags(raw_tags)
        
        assert 'flavor' in result.normalized_tags
        assert len(result.normalized_tags['flavor']) > 0
        assert result.confidence_scores['flavor'] > 0.8
    
    def test_normalize_tags_origin_category(self):
        """Test normalization of origin tags."""
        raw_tags = ['karnataka', 'kerala', 'tamil-nadu']
        result = self.service.normalize_tags(raw_tags)
        
        assert 'origin' in result.normalized_tags
        assert len(result.normalized_tags['origin']) > 0
        assert result.confidence_scores['origin'] > 0.8
    
    def test_normalize_tags_roast_category(self):
        """Test normalization of roast tags."""
        raw_tags = ['light', 'medium', 'dark', 'espresso']
        result = self.service.normalize_tags(raw_tags)
        
        assert 'roast' in result.normalized_tags
        assert len(result.normalized_tags['roast']) > 0
        assert result.confidence_scores['roast'] > 0.8
    
    def test_normalize_tags_process_category(self):
        """Test normalization of process tags."""
        raw_tags = ['washed', 'natural', 'honey', 'monsooned']
        result = self.service.normalize_tags(raw_tags)
        
        assert 'process' in result.normalized_tags
        assert len(result.normalized_tags['process']) > 0
        assert result.confidence_scores['process'] > 0.8
    
    def test_normalize_tags_unrecognized_tags(self):
        """Test normalization with unrecognized tags."""
        raw_tags = ['unknown-tag', 'random-word', 'xyz']
        result = self.service.normalize_tags(raw_tags)
        
        assert result.normalized_count == 0
        assert len(result.warnings) > 0
        assert all('Unrecognized tag' in warning for warning in result.warnings)
    
    def test_normalize_tags_mixed_categories(self):
        """Test normalization with mixed category tags."""
        raw_tags = ['chocolate', 'karnataka', 'light', 'washed', 'blue-tokai']
        result = self.service.normalize_tags(raw_tags)
        
        assert result.total_tags == 5
        assert result.normalized_count > 0
        assert len(result.normalized_tags) > 1  # Multiple categories
    
    def test_normalize_tags_case_insensitive(self):
        """Test normalization is case insensitive."""
        raw_tags = ['CHOCOLATE', 'Caramel', 'Karnataka', 'LIGHT']
        result = self.service.normalize_tags(raw_tags)
        
        assert result.normalized_count > 0
        assert len(result.normalized_tags) > 0
    
    def test_normalize_tags_whitespace_handling(self):
        """Test normalization handles whitespace correctly."""
        raw_tags = [' chocolate ', ' caramel ', ' karnataka ']
        result = self.service.normalize_tags(raw_tags)
        
        assert result.normalized_count > 0
        # Check that normalized tags don't have extra whitespace
        for category, tags in result.normalized_tags.items():
            for tag in tags:
                assert tag == tag.strip()
    
    def test_normalize_tags_empty_strings(self):
        """Test normalization filters out empty strings."""
        raw_tags = ['chocolate', '', 'caramel', '   ', 'karnataka']
        result = self.service.normalize_tags(raw_tags)
        
        assert result.normalized_count > 0
        # Check that empty strings are filtered out
        for category, tags in result.normalized_tags.items():
            for tag in tags:
                assert len(tag) > 0
    
    def test_batch_normalize_tags(self):
        """Test batch normalization."""
        tag_lists = [
            ['chocolate', 'caramel'],
            ['karnataka', 'kerala'],
            ['light', 'medium'],
            ['washed', 'natural']
        ]
        results = self.service.batch_normalize_tags(tag_lists)
        
        assert len(results) == 4
        assert all(isinstance(result, TagNormalizationResult) for result in results)
        assert all(result.total_tags > 0 for result in results)
    
    def test_batch_normalize_tags_empty_lists(self):
        """Test batch normalization with empty lists."""
        tag_lists = [[], [], []]
        results = self.service.batch_normalize_tags(tag_lists)
        
        assert len(results) == 3
        assert all(result.total_tags == 0 for result in results)
        assert all(result.normalized_count == 0 for result in results)
    
    def test_categorize_tag_direct_match(self):
        """Test direct tag categorization."""
        category, confidence = self.service._categorize_tag('chocolate')
        assert category == 'flavor'
        assert confidence == 0.95
    
    def test_categorize_tag_fuzzy_match(self):
        """Test fuzzy tag categorization."""
        category, confidence = self.service._categorize_tag('choco')
        assert category == 'flavor'
        assert confidence == 0.85
    
    def test_categorize_tag_no_match(self):
        """Test categorization with no match."""
        category, confidence = self.service._categorize_tag('unknown-tag')
        assert category is None
        assert confidence == 0.0
    
    def test_get_performance_metrics(self):
        """Test performance metrics."""
        metrics = self.service.get_performance_metrics()
        
        assert 'service_version' in metrics
        assert 'categories' in metrics
        assert 'total_tags' in metrics
        assert 'fuzzy_patterns' in metrics
        assert 'supported_categories' in metrics
        
        assert metrics['service_version'] == '1.0.0'
        assert len(metrics['categories']) > 0
        assert metrics['total_tags'] > 0
        assert metrics['fuzzy_patterns'] > 0
        assert metrics['supported_categories'] > 0
    
    def test_tag_normalization_result_serialization(self):
        """Test TagNormalizationResult serialization."""
        result = TagNormalizationResult(
            normalized_tags={'flavor': ['chocolate', 'caramel']},
            confidence_scores={'flavor': 0.9},
            warnings=[],
            total_tags=2,
            normalized_count=2
        )
        
        # Test to_dict
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert 'normalized_tags' in result_dict
        assert 'confidence_scores' in result_dict
        assert 'warnings' in result_dict
        assert 'total_tags' in result_dict
        assert 'normalized_count' in result_dict
        
        # Test from_dict
        restored_result = TagNormalizationResult.from_dict(result_dict)
        assert restored_result.normalized_tags == result.normalized_tags
        assert restored_result.confidence_scores == result.confidence_scores
        assert restored_result.warnings == result.warnings
        assert restored_result.total_tags == result.total_tags
        assert restored_result.normalized_count == result.normalized_count
    
    def test_error_handling(self):
        """Test error handling in normalization."""
        # Test with None input
        result = self.service.normalize_tags(None)
        assert isinstance(result, TagNormalizationResult)
        assert result.total_tags == 0
        assert result.normalized_count == 0
        
        # Test with invalid input types
        result = self.service.normalize_tags([None, 123, {}])
        assert isinstance(result, TagNormalizationResult)
        # Should handle gracefully without crashing
    
    def test_india_specific_categories(self):
        """Test India-specific coffee categories."""
        # Test Indian regions
        indian_regions = ['karnataka', 'kerala', 'tamil-nadu', 'chikmagalur', 'coorg']
        result = self.service.normalize_tags(indian_regions)
        
        assert 'origin' in result.normalized_tags or 'regions' in result.normalized_tags
        assert result.normalized_count > 0
        
        # Test Indian roasters
        indian_roasters = ['blue-tokai', 'third-wave', 'tata-coffee', 'hunkal-heights']
        result = self.service.normalize_tags(indian_roasters)
        
        assert 'roasters' in result.normalized_tags
        assert result.normalized_count > 0
        
        # Test Indian estates
        indian_estates = ['tata-coffee', 'hunkal-heights', 'kapi-kottai']
        result = self.service.normalize_tags(indian_estates)
        
        assert 'estates' in result.normalized_tags
        assert result.normalized_count > 0
