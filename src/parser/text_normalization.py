"""
Text normalization service for product names and descriptions.
"""

import re
import unicodedata
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from structlog import get_logger

from ..config.text_normalization_config import TextNormalizationConfig
from pydantic import BaseModel, Field

logger = get_logger(__name__)


class TextNormalizationResult(BaseModel):
    """Result of text normalization operation."""
    
    original_text: str = Field(description="Original text before normalization")
    normalized_text: str = Field(description="Text after normalization")
    changes_made: List[str] = Field(default_factory=list, description="List of changes made")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")
    warnings: List[str] = Field(default_factory=list, description="Warnings about normalization")
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        validate_assignment = True


class TextNormalizationService:
    """
    Service for normalizing text content.
    
    Features:
    - Case normalization
    - Spacing normalization
    - Punctuation normalization
    - Confidence scoring
    - Batch processing
    """
    
    def __init__(self, config: TextNormalizationConfig):
        """Initialize text normalization service."""
        self.config = config
        self.normalization_rules = config.normalization_rules
        
        logger.info("TextNormalizationService initialized", 
                   normalize_case=config.normalize_case,
                   case_style=config.case_style,
                   batch_size=config.batch_size)
    
    def normalize_text(self, text: str) -> TextNormalizationResult:
        """
        Normalize text content.
        
        Args:
            text: Text to normalize
            
        Returns:
            TextNormalizationResult with normalization details
        """
        start_time = datetime.now()
        
        if not text or not isinstance(text, str):
            return TextNormalizationResult(
                original_text=text or "",
                normalized_text=text or "",
                changes_made=[],
                confidence=1.0,
                warnings=["Empty or invalid input text"],
                processing_time_ms=0.0
            )
        
        # Check text length
        if len(text) > self.config.max_text_length:
            logger.warning("Text exceeds maximum length", 
                          text_length=len(text), 
                          max_length=self.config.max_text_length)
            text = text[:self.config.max_text_length]
        
        original_text = text
        normalized_text = text
        changes_made = []
        warnings = []
        
        try:
            # Case normalization
            if self.config.normalize_case:
                normalized_text, case_changes = self._normalize_case(normalized_text)
                changes_made.extend(case_changes)
            
            # Spacing normalization
            if self.config.normalize_spacing:
                normalized_text, spacing_changes = self._normalize_spacing(normalized_text)
                changes_made.extend(spacing_changes)
            
            # Punctuation normalization
            if self.config.normalize_punctuation:
                normalized_text, punct_changes = self._normalize_punctuation(normalized_text)
                changes_made.extend(punct_changes)
            
            # Calculate confidence
            confidence = self._calculate_confidence(original_text, normalized_text)
            
            # Generate warnings
            warnings = self._generate_warnings(original_text, normalized_text, confidence)
            
        except Exception as e:
            logger.error("Error during text normalization", error=str(e), text=text[:100])
            if self.config.fail_on_error:
                raise
            warnings.append(f"Normalization error: {str(e)}")
            confidence = 0.0
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return TextNormalizationResult(
            original_text=original_text,
            normalized_text=normalized_text,
            changes_made=changes_made,
            confidence=confidence,
            warnings=warnings,
            processing_time_ms=processing_time
        )
    
    def normalize_batch(self, texts: List[str]) -> List[TextNormalizationResult]:
        """
        Normalize multiple texts in batch.
        
        Args:
            texts: List of texts to normalize
            
        Returns:
            List of TextNormalizationResult objects
        """
        results = []
        
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            
            logger.debug("Processing text normalization batch", 
                        batch_start=i, 
                        batch_size=len(batch))
            
            for text in batch:
                result = self.normalize_text(text)
                results.append(result)
        
        logger.info("Text normalization batch completed", 
                   total_texts=len(texts), 
                   results_count=len(results))
        
        return results
    
    def _normalize_case(self, text: str) -> tuple[str, List[str]]:
        """Normalize text case."""
        changes = []
        original_text = text
        
        if self.config.case_style == "title":
            text = text.title()
            if text != original_text:
                changes.append("Text converted to title case")
        elif self.config.case_style == "lower":
            text = text.lower()
            if text != original_text:
                changes.append("Text converted to lowercase")
        elif self.config.case_style == "upper":
            text = text.upper()
            if text != original_text:
                changes.append("Text converted to uppercase")
        elif self.config.case_style == "sentence":
            text = text.capitalize()
            if text != original_text:
                changes.append("Text converted to sentence case")
        
        return text, changes
    
    def _normalize_spacing(self, text: str) -> tuple[str, List[str]]:
        """Normalize spacing in text."""
        changes = []
        original_text = text
        
        # Remove extra spaces
        if self.config.remove_extra_spaces:
            text = re.sub(r'\s+', ' ', text)
            if text != original_text:
                changes.append("Extra spaces normalized")
        
        # Normalize spacing around punctuation
        if self.config.normalize_punctuation_spacing:
            # Remove spaces before punctuation
            text = re.sub(r'\s+([.!?,:;])', r'\1', text)
            # Add space after punctuation if missing
            text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
            if text != original_text:
                changes.append("Punctuation spacing normalized")
        
        return text, changes
    
    def _normalize_punctuation(self, text: str) -> tuple[str, List[str]]:
        """Normalize punctuation in text."""
        changes = []
        original_text = text
        
        # Standardize quotes
        if self.config.standardize_quotes:
            # Replace smart quotes with standard quotes
            text = re.sub(r'[\u201c\u201d"]', '"', text)
            text = re.sub(r"[\u2018\u2019']", "'", text)
            if text != original_text:
                changes.append("Quotes standardized")
        
        # Standardize dashes
        if self.config.standardize_dashes:
            # Replace em/en dashes with hyphens
            text = re.sub(r'[–—]', '-', text)
            if text != original_text:
                changes.append("Dashes standardized")
        
        # Normalize ellipsis
        if self.normalization_rules.get("normalize_ellipsis", True):
            text = re.sub(r'\.{3,}', '...', text)
            if text != original_text:
                changes.append("Ellipsis normalized")
        
        return text, changes
    
    def _calculate_confidence(self, original_text: str, normalized_text: str) -> float:
        """Calculate confidence score for normalization operation."""
        if not self.config.enable_confidence_scoring:
            return 1.0
        
        if not original_text:
            return 1.0
        
        # Base confidence
        confidence = 1.0
        
        # Penalize if text became too short
        length_ratio = len(normalized_text) / len(original_text) if original_text else 1.0
        if length_ratio < 0.5:
            confidence -= 0.3
        elif length_ratio < 0.8:
            confidence -= 0.1
        
        # Penalize if text is empty after normalization
        if not normalized_text.strip():
            confidence = 0.0
        
        # Bonus for reasonable length preservation
        if 0.8 <= length_ratio <= 1.2:
            confidence += 0.1
        
        # Bonus for minimal changes (high similarity)
        if original_text == normalized_text:
            confidence = 1.0
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_warnings(self, original_text: str, normalized_text: str, confidence: float) -> List[str]:
        """Generate warnings about normalization operation."""
        warnings = []
        
        # Low confidence warning
        if confidence < self.config.confidence_threshold:
            warnings.append(f"Low confidence normalization (score: {confidence:.2f})")
        
        # Empty result warning
        if not normalized_text.strip():
            warnings.append("Text became empty after normalization")
        
        # Significant length reduction warning
        if original_text and len(normalized_text) < len(original_text) * 0.5:
            warnings.append("Significant text length reduction")
        
        return warnings
