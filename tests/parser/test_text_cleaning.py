"""
Unit tests for text cleaning service.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.parser.text_cleaning import TextCleaningService, TextCleaningResult
from src.config.text_cleaning_config import TextCleaningConfig


class TestTextCleaningService:
    """Test cases for TextCleaningService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TextCleaningConfig(
            use_beautifulsoup=True,
            remove_html_tags=True,
            decode_html_entities=True,
            normalize_unicode=True,
            remove_control_characters=True,
            normalize_whitespace=True,
            batch_size=10,
            max_text_length=1000,
            fail_on_error=False,
            log_errors=True,
            enable_confidence_scoring=True,
            confidence_threshold=0.8
        )
        self.service = TextCleaningService(self.config)
    
    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        text = "  Hello   World  "
        result = self.service.clean_text(text)
        
        assert result.original_text == text
        assert result.cleaned_text == "Hello World"
        assert "Extra spaces normalized" in result.changes_made
        assert result.confidence >= 0.8
        assert result.processing_time_ms > 0
    
    def test_clean_text_html_removal(self):
        """Test HTML tag removal."""
        text = "<p>Hello <strong>World</strong></p>"
        result = self.service.clean_text(text)
        
        assert result.original_text == text
        assert result.cleaned_text == "Hello World"
        assert "HTML tags removed" in " ".join(result.changes_made)
        assert result.confidence >= 0.8
    
    def test_clean_text_html_entities(self):
        """Test HTML entity decoding."""
        text = "Hello &amp; World &lt;test&gt;"
        result = self.service.clean_text(text)
        
        assert result.original_text == text
        assert result.cleaned_text == "Hello & World <test>"
        assert "HTML entities decoded" in result.changes_made
        assert result.confidence >= 0.8
    
    def test_clean_text_unicode_normalization(self):
        """Test unicode normalization."""
        text = "Café résumé naïve"
        result = self.service.clean_text(text)
        
        assert result.original_text == text
        # Unicode normalization changes the representation but keeps the text readable
        assert len(result.cleaned_text) > 0
        assert result.confidence >= 0.8
    
    def test_clean_text_control_characters(self):
        """Test control character removal."""
        text = "Hello\x00World\x01Test"
        result = self.service.clean_text(text)
        
        assert result.original_text == text
        assert result.cleaned_text == "HelloWorldTest"
        assert "Control characters removed" in result.changes_made
        assert result.confidence >= 0.8
    
    def test_clean_text_empty_input(self):
        """Test empty input handling."""
        result = self.service.clean_text("")
        
        assert result.original_text == ""
        assert result.cleaned_text == ""
        assert result.confidence == 1.0
        assert "Empty or invalid input text" in result.warnings
    
    def test_clean_text_none_input(self):
        """Test None input handling."""
        result = self.service.clean_text(None)
        
        assert result.original_text == ""
        assert result.cleaned_text == ""
        assert result.confidence == 1.0
        assert "Empty or invalid input text" in result.warnings
    
    def test_clean_text_long_input(self):
        """Test long input handling."""
        long_text = "A" * 1500  # Exceeds max_text_length
        result = self.service.clean_text(long_text)
        
        assert len(result.original_text) == 1000  # Truncated to max length
        assert len(result.cleaned_text) == 1000  # Truncated
        assert result.confidence >= 0.8
    
    def test_clean_batch(self):
        """Test batch processing."""
        texts = [
            "  Hello   World  ",
            "<p>Test <strong>HTML</strong></p>",
            "Normal text"
        ]
        
        results = self.service.clean_batch(texts)
        
        assert len(results) == 3
        assert results[0].cleaned_text == "Hello World"
        assert results[1].cleaned_text == "Test HTML"
        assert results[2].cleaned_text == "Normal text"
    
    def test_clean_text_with_beautifulsoup_disabled(self):
        """Test HTML removal with BeautifulSoup disabled."""
        config = TextCleaningConfig(use_beautifulsoup=False)
        service = TextCleaningService(config)
        
        text = "<p>Hello <strong>World</strong></p>"
        result = service.clean_text(text)
        
        assert result.original_text == text
        assert result.cleaned_text == "Hello World"
        assert "HTML tags removed" in " ".join(result.changes_made)
    
    def test_clean_text_confidence_scoring(self):
        """Test confidence scoring."""
        # High confidence case
        text = "Hello World"
        result = self.service.clean_text(text)
        assert result.confidence >= 0.8
        
        # Low confidence case (significant reduction)
        text = "A" * 100
        result = self.service.clean_text(text)
        # Should still be high confidence for simple text
        assert result.confidence >= 0.8
    
    def test_clean_text_error_handling(self):
        """Test error handling."""
        with patch.object(self.service, '_remove_html', side_effect=Exception("Test error")):
            result = self.service.clean_text("test")
            
            assert result.original_text == "test"
            assert result.cleaned_text == "test"
            assert result.confidence == 0.0
            assert any("Cleaning error" in warning for warning in result.warnings)
    
    def test_clean_text_fail_on_error(self):
        """Test fail on error configuration."""
        config = TextCleaningConfig(fail_on_error=True)
        service = TextCleaningService(config)
        
        with patch.object(service, '_remove_html', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                service.clean_text("test")
    
    def test_clean_text_confidence_disabled(self):
        """Test confidence scoring disabled."""
        config = TextCleaningConfig(enable_confidence_scoring=False)
        service = TextCleaningService(config)
        
        result = service.clean_text("test")
        assert result.confidence == 1.0
    
    def test_clean_text_preserve_line_breaks(self):
        """Test preserving line breaks."""
        config = TextCleaningConfig(preserve_line_breaks=True)
        service = TextCleaningService(config)
        
        text = "Line 1\nLine 2\nLine 3"
        result = service.clean_text(text)
        
        assert result.cleaned_text == text  # Line breaks preserved
    
    def test_clean_text_cleaning_rules(self):
        """Test custom cleaning rules."""
        config = TextCleaningConfig(
            cleaning_rules={
                "remove_extra_spaces": False,
                "remove_tabs": False,
                "remove_newlines": False,
                "strip_whitespace": False
            }
        )
        service = TextCleaningService(config)
        
        text = "  Hello\tWorld\nTest  "
        result = service.clean_text(text)
        
        # Should preserve original formatting
        assert result.cleaned_text == text
    
    def test_clean_text_warnings(self):
        """Test warning generation."""
        # Test low confidence warning
        config = TextCleaningConfig(confidence_threshold=0.9)
        service = TextCleaningService(config)
        
        result = service.clean_text("A" * 1000)  # Long text might reduce confidence
        # Warnings depend on confidence calculation
        assert isinstance(result.warnings, list)
    
    def test_clean_text_processing_time(self):
        """Test processing time measurement."""
        result = self.service.clean_text("test")
        assert result.processing_time_ms >= 0
        assert isinstance(result.processing_time_ms, float)
