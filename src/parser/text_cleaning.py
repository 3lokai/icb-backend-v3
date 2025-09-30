"""
Text cleaning service for product names and descriptions.
"""

import re
import html
import unicodedata
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from structlog import get_logger

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from ..config.text_cleaning_config import TextCleaningConfig
from pydantic import BaseModel, Field

logger = get_logger(__name__)


class TextCleaningResult(BaseModel):
    """Result of text cleaning operation."""
    
    original_text: str = Field(description="Original text before cleaning")
    cleaned_text: str = Field(description="Text after cleaning")
    changes_made: List[str] = Field(default_factory=list, description="List of changes made")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")
    warnings: List[str] = Field(default_factory=list, description="Warnings about cleaning")
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        validate_assignment = True


class TextCleaningService:
    """
    Service for cleaning and normalizing text content.
    
    Features:
    - HTML tag removal
    - HTML entity decoding
    - Unicode normalization
    - Control character removal
    - Whitespace normalization
    - Confidence scoring
    - Batch processing
    """
    
    def __init__(self, config: TextCleaningConfig):
        """Initialize text cleaning service."""
        self.config = config
        self.html_parser = BeautifulSoup if config.use_beautifulsoup and BeautifulSoup else None
        self.cleaning_rules = config.cleaning_rules
        
        logger.info("TextCleaningService initialized", 
                   use_beautifulsoup=config.use_beautifulsoup,
                   batch_size=config.batch_size)
    
    def clean_text(self, text: str) -> TextCleaningResult:
        """
        Clean and normalize text content.
        
        Args:
            text: Text to clean
            
        Returns:
            TextCleaningResult with cleaning details
        """
        start_time = datetime.now()
        
        if not text or not isinstance(text, str):
            return TextCleaningResult(
                original_text=text or "",
                cleaned_text=text or "",
                changes_made=[],
                confidence=1.0,
                warnings=["Empty or invalid input text"],
                processing_time_ms=0.0
            )
        
        # Check text length
        original_length = len(text)
        if len(text) > self.config.max_text_length:
            logger.warning("Text exceeds maximum length", 
                          text_length=len(text), 
                          max_length=self.config.max_text_length)
            text = text[:self.config.max_text_length]
        
        original_text = text
        cleaned_text = text
        changes_made = []
        warnings = []
        
        # Store original length for confidence calculation
        original_length = len(original_text)
        
        try:
            # HTML removal
            if self.config.remove_html_tags:
                cleaned_text, html_changes = self._remove_html(cleaned_text)
                changes_made.extend(html_changes)
            
            # Special character handling
            if self.config.normalize_unicode or self.config.remove_control_characters:
                cleaned_text, char_changes = self._handle_special_characters(cleaned_text)
                changes_made.extend(char_changes)
            
            # Whitespace normalization
            if self.config.normalize_whitespace:
                cleaned_text, whitespace_changes = self._normalize_whitespace(cleaned_text)
                changes_made.extend(whitespace_changes)
            
            # Calculate confidence
            confidence = self._calculate_confidence(original_text, cleaned_text, original_length)
            
            # Generate warnings
            warnings = self._generate_warnings(original_text, cleaned_text, confidence)
            
        except Exception as e:
            logger.error("Error during text cleaning", error=str(e), text=text[:100])
            if self.config.fail_on_error:
                raise
            warnings.append(f"Cleaning error: {str(e)}")
            confidence = 0.0
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return TextCleaningResult(
            original_text=original_text,
            cleaned_text=cleaned_text,
            changes_made=changes_made,
            confidence=confidence,
            warnings=warnings,
            processing_time_ms=processing_time
        )
    
    def clean_batch(self, texts: List[str]) -> List[TextCleaningResult]:
        """
        Clean multiple texts in batch.
        
        Args:
            texts: List of texts to clean
            
        Returns:
            List of TextCleaningResult objects
        """
        results = []
        
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            
            logger.debug("Processing text cleaning batch", 
                        batch_start=i, 
                        batch_size=len(batch))
            
            for text in batch:
                result = self.clean_text(text)
                results.append(result)
        
        logger.info("Text cleaning batch completed", 
                   total_texts=len(texts), 
                   results_count=len(results))
        
        return results
    
    def _remove_html(self, text: str) -> tuple[str, List[str]]:
        """Remove HTML tags and entities."""
        changes = []
        original_text = text
        
        if self.html_parser:
            # Use BeautifulSoup for better HTML parsing
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text()
            if text != original_text:
                changes.append("HTML tags removed with BeautifulSoup")
        else:
            # Use regex for HTML removal
            text = re.sub(r'<[^>]+>', '', text)
            if text != original_text:
                changes.append("HTML tags removed with regex")
        
        # Decode HTML entities
        if self.config.decode_html_entities:
            decoded_text = html.unescape(text)
            if decoded_text != text:
                changes.append("HTML entities decoded")
                text = decoded_text
        
        return text, changes
    
    def _handle_special_characters(self, text: str) -> tuple[str, List[str]]:
        """Handle special characters and encoding."""
        changes = []
        original_text = text
        
        # Normalize unicode characters
        if self.config.normalize_unicode:
            normalized_text = unicodedata.normalize('NFKD', text)
            if normalized_text != text:
                changes.append("Unicode characters normalized")
                text = normalized_text
        
        # Remove control characters (but preserve line breaks and tabs if configured)
        if self.config.remove_control_characters:
            if self.config.preserve_line_breaks or not self.cleaning_rules.get("remove_newlines", True):
                # Preserve newlines, carriage returns, and tabs
                filtered_text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\r\t')
            else:
                # Remove all control characters including line breaks
                filtered_text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
            if filtered_text != text:
                changes.append("Control characters removed")
                text = filtered_text
        
        return text, changes
    
    def _normalize_whitespace(self, text: str) -> tuple[str, List[str]]:
        """Normalize whitespace characters."""
        changes = []
        original_text = text
        
        # Remove extra spaces (but preserve line breaks if configured)
        if self.cleaning_rules.get("remove_extra_spaces", True):
            if self.config.preserve_line_breaks:
                # Only normalize spaces within lines, not across line breaks
                text = re.sub(r'[ \t]+', ' ', text)
            else:
                # Normalize all whitespace including line breaks
                text = re.sub(r'\s+', ' ', text)
            if text != original_text:
                changes.append("Extra spaces normalized")
        
        # Remove tabs
        if self.cleaning_rules.get("remove_tabs", True):
            new_text = text.replace('\t', ' ')
            if new_text != text:
                changes.append("Tabs replaced with spaces")
                text = new_text
        
        # Remove newlines (unless preserving line breaks)
        if not self.config.preserve_line_breaks and self.cleaning_rules.get("remove_newlines", True):
            new_text = text.replace('\n', ' ').replace('\r', ' ')
            if new_text != text:
                changes.append("Line breaks removed")
                text = new_text
        
        # Strip leading/trailing whitespace
        if self.cleaning_rules.get("strip_whitespace", True):
            text = text.strip()
            if text != original_text:
                changes.append("Leading/trailing whitespace stripped")
        
        return text, changes
    
    def _calculate_confidence(self, original_text: str, cleaned_text: str, original_length: int = None) -> float:
        """Calculate confidence score for cleaning operation."""
        if not self.config.enable_confidence_scoring:
            return 1.0
        
        if not original_text:
            return 1.0
        
        # Use provided original length if available (for truncated text)
        if original_length is not None:
            length_ratio = len(cleaned_text) / original_length if original_length > 0 else 1.0
        else:
            length_ratio = len(cleaned_text) / len(original_text) if original_text else 1.0
        
        # Base confidence
        confidence = 1.0
        
        # Penalize if text became too short
        if length_ratio < 0.3:
            confidence -= 0.4
        elif length_ratio < 0.5:
            confidence -= 0.2
        elif length_ratio < 0.7:
            confidence -= 0.1
        
        # Penalize if text is empty after cleaning
        if not cleaned_text.strip():
            confidence = 0.0
        
        # Bonus for reasonable length preservation
        if 0.7 <= length_ratio <= 1.2:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_warnings(self, original_text: str, cleaned_text: str, confidence: float) -> List[str]:
        """Generate warnings about cleaning operation."""
        warnings = []
        
        # Low confidence warning
        if confidence < self.config.confidence_threshold:
            warnings.append(f"Low confidence cleaning (score: {confidence:.2f})")
        
        # Empty result warning
        if not cleaned_text.strip():
            warnings.append("Text became empty after cleaning")
        
        # Significant length reduction warning
        if original_text and len(cleaned_text) < len(original_text) * 0.5:
            warnings.append("Significant text length reduction")
        
        return warnings
