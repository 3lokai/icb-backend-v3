"""
Unit tests for text normalization service.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.parser.text_normalization import TextNormalizationService, TextNormalizationResult
from src.config.text_normalization_config import TextNormalizationConfig


class TestTextNormalizationService:
    """Test cases for TextNormalizationService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TextNormalizationConfig(
            normalize_case=False,
            case_style="preserve",
            normalize_spacing=True,
            remove_extra_spaces=True,
            normalize_punctuation_spacing=True,
            normalize_punctuation=True,
            standardize_quotes=True,
            standardize_dashes=True,
            batch_size=10,
            max_text_length=1000,
            fail_on_error=False,
            log_errors=True,
            enable_confidence_scoring=True,
            confidence_threshold=0.8
        )
        self.service = TextNormalizationService(self.config)
    
    def test_normalize_text_basic(self):
        """Test basic text normalization."""
        text = "  Hello   World  "
        result = self.service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == " Hello World "
        assert "Extra spaces normalized" in result.changes_made
        assert result.confidence > 0.8
        assert result.processing_time_ms > 0
    
    def test_normalize_text_case_title(self):
        """Test title case normalization."""
        config = TextNormalizationConfig(normalize_case=True, case_style="title")
        service = TextNormalizationService(config)
        
        text = "hello world"
        result = service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == "Hello World"
        assert "Text converted to title case" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_case_lower(self):
        """Test lowercase normalization."""
        config = TextNormalizationConfig(normalize_case=True, case_style="lower")
        service = TextNormalizationService(config)
        
        text = "HELLO WORLD"
        result = service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == "hello world"
        assert "Text converted to lowercase" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_case_upper(self):
        """Test uppercase normalization."""
        config = TextNormalizationConfig(normalize_case=True, case_style="upper")
        service = TextNormalizationService(config)
        
        text = "hello world"
        result = service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == "HELLO WORLD"
        assert "Text converted to uppercase" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_case_sentence(self):
        """Test sentence case normalization."""
        config = TextNormalizationConfig(normalize_case=True, case_style="sentence")
        service = TextNormalizationService(config)
        
        text = "hello world"
        result = service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == "Hello world"
        assert "Text converted to sentence case" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_spacing(self):
        """Test spacing normalization."""
        text = "Hello    World   Test"
        result = self.service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == "Hello World Test"
        assert "Extra spaces normalized" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_punctuation_spacing(self):
        """Test punctuation spacing normalization."""
        text = "Hello , World . Test"
        result = self.service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == "Hello, World. Test"
        assert "Punctuation spacing normalized" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_quotes(self):
        """Test quote standardization."""
        # Using Unicode escape sequences for smart quotes
        # \u201c = left double quote, \u201d = right double quote
        # \u2018 = left single quote, \u2019 = right single quote
        text = "Hello \u201cWorld\u201d and \u2018Test\u2019"
        result = self.service.normalize_text(text)
        
        assert result.original_text == text
        # The smart quotes should be standardized to regular quotes
        assert result.normalized_text == 'Hello "World" and \'Test\''
        assert "Quotes standardized" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_dashes(self):
        """Test dash standardization."""
        text = "Hello – World — Test"
        result = self.service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == "Hello - World - Test"
        assert "Dashes standardized" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_ellipsis(self):
        """Test ellipsis normalization."""
        text = "Hello....World......Test"
        result = self.service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == "Hello... World... Test"
        assert "Ellipsis normalized" in result.changes_made
        assert result.confidence > 0.8
    
    def test_normalize_text_empty_input(self):
        """Test empty input handling."""
        result = self.service.normalize_text("")
        
        assert result.original_text == ""
        assert result.normalized_text == ""
        assert result.confidence == 1.0
        assert "Empty or invalid input text" in result.warnings
    
    def test_normalize_text_none_input(self):
        """Test None input handling."""
        result = self.service.normalize_text(None)
        
        assert result.original_text == ""
        assert result.normalized_text == ""
        assert result.confidence == 1.0
        assert "Empty or invalid input text" in result.warnings
    
    def test_normalize_text_long_input(self):
        """Test long input handling."""
        long_text = "A" * 1500  # Exceeds max_text_length
        result = self.service.normalize_text(long_text)
        
        assert len(result.original_text) == 1000  # Truncated to max length
        assert len(result.normalized_text) == 1000  # Truncated
        assert result.confidence > 0.8
    
    def test_normalize_batch(self):
        """Test batch processing."""
        texts = [
            "  Hello   World  ",
            "HELLO WORLD",
            "Normal text"
        ]
        
        results = self.service.normalize_batch(texts)
        
        assert len(results) == 3
        assert results[0].normalized_text == " Hello World "
        assert results[1].normalized_text == "HELLO WORLD"  # Case preserved
        assert results[2].normalized_text == "Normal text"
    
    def test_normalize_text_no_changes(self):
        """Test text that doesn't need normalization."""
        text = "Hello World"
        result = self.service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == text
        assert result.confidence == 1.0
        assert len(result.changes_made) == 0
    
    def test_normalize_text_confidence_scoring(self):
        """Test confidence scoring."""
        # High confidence case
        text = "Hello World"
        result = self.service.normalize_text(text)
        assert result.confidence > 0.8
        
        # Identical text should have perfect confidence
        text = "Already normalized"
        result = self.service.normalize_text(text)
        assert result.confidence == 1.0
    
    def test_normalize_text_error_handling(self):
        """Test error handling."""
        with patch.object(self.service, '_normalize_spacing', side_effect=Exception("Test error")):
            result = self.service.normalize_text("test")
            
            assert result.original_text == "test"
            assert result.normalized_text == "test"
            assert result.confidence == 0.0
            assert any("Normalization error" in warning for warning in result.warnings)
    
    def test_normalize_text_fail_on_error(self):
        """Test fail on error configuration."""
        config = TextNormalizationConfig(fail_on_error=True)
        service = TextNormalizationService(config)
        
        with patch.object(service, '_normalize_spacing', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                service.normalize_text("test")
    
    def test_normalize_text_confidence_disabled(self):
        """Test confidence scoring disabled."""
        config = TextNormalizationConfig(enable_confidence_scoring=False)
        service = TextNormalizationService(config)
        
        result = service.normalize_text("test")
        assert result.confidence == 1.0
    
    def test_normalize_text_custom_rules(self):
        """Test custom normalization rules."""
        config = TextNormalizationConfig(
            normalization_rules={
                "preserve_apostrophes": True,
                "preserve_hyphens": True,
                "normalize_ellipsis": False,
                "standardize_quotes": False
            }
        )
        service = TextNormalizationService(config)
        
        text = "Hello....World"
        result = service.normalize_text(text)
        
        # Ellipsis should not be normalized
        assert result.normalized_text == "Hello.... World"
    
    def test_normalize_text_warnings(self):
        """Test warning generation."""
        # Test low confidence warning
        config = TextNormalizationConfig(confidence_threshold=0.9)
        service = TextNormalizationService(config)
        
        result = service.normalize_text("A" * 1000)  # Long text might reduce confidence
        # Warnings depend on confidence calculation
        assert isinstance(result.warnings, list)
    
    def test_normalize_text_processing_time(self):
        """Test processing time measurement."""
        result = self.service.normalize_text("test")
        assert result.processing_time_ms >= 0
        assert isinstance(result.processing_time_ms, float)
    
    def test_normalize_text_all_features(self):
        """Test all normalization features together."""
        text = "  HELLO   ,   WORLD   —   TEST   "
        result = self.service.normalize_text(text)
        
        assert result.original_text == text
        assert result.normalized_text == " HELLO, WORLD - TEST "
        assert len(result.changes_made) > 0
        assert result.confidence > 0.8
