"""
Notes extraction service for extracting tasting notes from product descriptions.

Features:
- Pattern-based tasting notes extraction
- Confidence scoring for extraction accuracy
- Batch processing optimization for multiple products
- Comprehensive error handling and logging
- Pydantic result models for type safety
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger(__name__)


class NotesExtractionResult(BaseModel):
    """Represents a notes extraction result with metadata."""
    
    notes_raw: List[str] = Field(..., description="Extracted tasting notes")
    confidence_scores: List[float] = Field(..., description="Confidence scores for each note")
    warnings: List[str] = Field(default_factory=list, description="Extraction warnings")
    total_notes: int = Field(..., description="Total number of extracted notes")
    extraction_success: bool = Field(..., description="Whether extraction was successful")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotesExtractionResult':
        """Create NotesExtractionResult from dictionary."""
        return cls.model_validate(data)


class NotesExtractionService:
    """
    Service for extracting tasting notes from product descriptions.
    
    Features:
    - Pattern-based notes extraction
    - Confidence scoring for extraction accuracy
    - Batch processing for multiple products
    - Comprehensive error handling
    """
    
    def __init__(self, config=None):
        """Initialize notes extraction service with tasting patterns."""
        self.config = config
        # Tasting notes extraction patterns
        self.tasting_patterns = [
            r'(tasting notes?|flavor notes?|aroma notes?)',
            r'(notes?:|tasting:)',
            r'(flavor profile|aroma profile)',
            r'(coffee notes?|brewing notes?)',
            r'(taste|flavor|aroma|body|acidity)',
            r'(smooth|rich|bold|bright|fruity|chocolate|caramel)',
            r'(citrus|berry|floral|herbal|woody|smoky)',
            r'(sweet|bitter|acidic|earthy|spicy|nutty)'
        ]
        
        # Context patterns for better extraction
        self.context_patterns = [
            r'(this coffee|this blend|our coffee|our blend)',
            r'(features|characteristics|profile|description)',
            r'(taste like|flavors of|notes of|hints of)',
            r'(with notes|flavors include|tasting like)'
        ]
        
        # Common tasting note keywords
        self.tasting_keywords = [
            'chocolate', 'caramel', 'vanilla', 'nutty', 'fruity', 'spicy',
            'earthy', 'bold', 'smooth', 'rich', 'sweet', 'bitter', 'acidic',
            'citrus', 'berry', 'floral', 'herbal', 'woody', 'smoky',
            'bright', 'clean', 'complex', 'balanced', 'full-bodied',
            'light', 'medium', 'dark', 'roasted', 'toasted', 'burnt'
        ]
        
        # Confidence scoring patterns
        self.high_confidence_patterns = [
            r'tasting notes?:?\s*([^.!?]+)',
            r'flavor notes?:?\s*([^.!?]+)',
            r'aroma notes?:?\s*([^.!?]+)',
            r'notes?:?\s*([^.!?]+)'
        ]
        
        self.medium_confidence_patterns = [
            r'flavors? of ([^.!?]+)',
            r'notes? of ([^.!?]+)',
            r'hints? of ([^.!?]+)',
            r'tastes? like ([^.!?]+)'
        ]
        
        self.low_confidence_patterns = [
            r'([^.!?]*(?:chocolate|caramel|vanilla|nutty|fruity|spicy|earthy|bold|smooth|rich|sweet|bitter|acidic|citrus|berry|floral|herbal|woody|smoky)[^.!?]*)',
            r'([^.!?]*(?:bright|clean|complex|balanced|full-bodied|light|medium|dark|roasted|toasted|burnt)[^.!?]*)'
        ]
        
        logger.info(
            "Notes extraction service initialized",
            tasting_patterns=len(self.tasting_patterns),
            context_patterns=len(self.context_patterns),
            tasting_keywords=len(self.tasting_keywords)
        )
    
    def extract_notes(self, description: str) -> NotesExtractionResult:
        """
        Extract tasting notes from product description.

        Args:
            description: Product description text

        Returns:
            NotesExtractionResult with extracted notes and metadata
        """
        try:
            # Handle invalid input types
            if not isinstance(description, str):
                return NotesExtractionResult(
                    notes_raw=[],
                    confidence_scores=[],
                    warnings=['Invalid input type - expected string'],
                    total_notes=0,
                    extraction_success=False
                )
            
            if not description or not description.strip():
                return NotesExtractionResult(
                    notes_raw=[],
                    confidence_scores=[],
                    warnings=['No description provided'],
                    total_notes=0,
                    extraction_success=False
                )
            
            notes = []
            confidence_scores = []
            warnings = []
            
            # Extract notes using high confidence patterns
            high_confidence_notes = self._extract_with_patterns(
                description, self.high_confidence_patterns, 0.9
            )
            notes.extend(high_confidence_notes['notes'])
            confidence_scores.extend(high_confidence_notes['scores'])
            warnings.extend(high_confidence_notes['warnings'])
            
            # Extract notes using medium confidence patterns
            medium_confidence_notes = self._extract_with_patterns(
                description, self.medium_confidence_patterns, 0.7
            )
            notes.extend(medium_confidence_notes['notes'])
            confidence_scores.extend(medium_confidence_notes['scores'])
            warnings.extend(medium_confidence_notes['warnings'])
            
            # Extract notes using low confidence patterns
            low_confidence_notes = self._extract_with_patterns(
                description, self.low_confidence_patterns, 0.5
            )
            notes.extend(low_confidence_notes['notes'])
            confidence_scores.extend(low_confidence_notes['scores'])
            warnings.extend(low_confidence_notes['warnings'])
            
            # Remove duplicates while preserving order
            unique_notes = []
            unique_scores = []
            seen = set()
            for note, score in zip(notes, confidence_scores):
                note_clean = note.strip().lower()
                if note_clean not in seen and len(note_clean) > 3:
                    unique_notes.append(note.strip())
                    unique_scores.append(score)
                    seen.add(note_clean)
            
            result = NotesExtractionResult(
                notes_raw=unique_notes,
                confidence_scores=unique_scores,
                warnings=warnings,
                total_notes=len(unique_notes),
                extraction_success=len(unique_notes) > 0
            )
            
            logger.info(
                "Notes extraction completed",
                description_length=len(description),
                total_notes=len(unique_notes),
                extraction_success=len(unique_notes) > 0,
                warnings_count=len(warnings)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Notes extraction failed",
                description=description[:100] + "..." if len(description) > 100 else description,
                error=str(e)
            )
            return NotesExtractionResult(
                notes_raw=[],
                confidence_scores=[],
                warnings=[f"Extraction error: {str(e)}"],
                total_notes=0,
                extraction_success=False
            )
    
    def _extract_with_patterns(
        self, 
        text: str, 
        patterns: List[str], 
        base_confidence: float
    ) -> Dict[str, Any]:
        """
        Extract notes using specific patterns with confidence scoring.
        
        Args:
            text: Text to extract from
            patterns: List of regex patterns
            base_confidence: Base confidence score for these patterns
            
        Returns:
            Dictionary with notes, scores, and warnings
        """
        notes = []
        scores = []
        warnings = []
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    if isinstance(match, tuple):
                        # Handle multiple groups
                        note = ' '.join(group for group in match if group)
                    else:
                        note = match
                    
                    if note and len(note.strip()) > 3:
                        # Parse individual flavor notes from the extracted text
                        individual_notes = self._parse_individual_notes(note)
                        for individual_note in individual_notes:
                            note_clean = self._clean_note(individual_note)
                            if note_clean:
                                notes.append(note_clean)
                                # Adjust confidence based on note quality
                                confidence = self._calculate_note_confidence(note_clean, base_confidence)
                                scores.append(confidence)
                        
            except re.error as e:
                warnings.append(f"Invalid regex pattern: {pattern} - {str(e)}")
                continue
        
        return {
            'notes': notes,
            'scores': scores,
            'warnings': warnings
        }
    
    def _parse_individual_notes(self, text: str) -> List[str]:
        """
        Parse individual flavor notes from a text string.
        
        Args:
            text: Text containing flavor notes
            
        Returns:
            List of individual flavor notes
        """
        individual_notes = []
        
        # Split by common delimiters
        delimiters = [',', ' and ', ' or ', ' with ', ' & ', ';']
        
        # First, try to find flavor lists with common patterns
        flavor_list_patterns = [
            r'notes?\s+of\s+([^.]*)',  # "notes of chocolate, caramel"
            r'flavou?rs?\s+of\s+([^.]*)',  # "flavors of chocolate, caramel"
            r'with\s+notes?\s+of\s+([^.]*)',  # "with notes of chocolate, caramel"
            r'featuring\s+([^.]*)',  # "featuring chocolate, caramel"
            r'including\s+([^.]*)',  # "including chocolate, caramel"
        ]
        
        for pattern in flavor_list_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Split the match by delimiters
                parts = re.split('|'.join(delimiters), match)
                for part in parts:
                    part = part.strip()
                    # Clean up common prefixes/suffixes
                    part = re.sub(r'^(of|with|and|or)\s+', '', part, flags=re.IGNORECASE)
                    part = re.sub(r'\s+(and|or|with)$', '', part, flags=re.IGNORECASE)
                    if part and len(part) > 2 and len(part) < 50:  # Reasonable length
                        individual_notes.append(part)
        
        # If no flavor lists found, look for individual flavor keywords
        if not individual_notes:
            # Find individual flavor keywords in the text
            for keyword in self.tasting_keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                    individual_notes.append(keyword)
        
        # If still no notes found, try to extract any comma-separated values
        if not individual_notes:
            # Look for any comma-separated lists
            comma_separated = re.findall(r'([^,]+(?:,\s*[^,]+)+)', text)
            for match in comma_separated:
                parts = [part.strip() for part in match.split(',')]
                for part in parts:
                    # Clean up common prefixes/suffixes
                    part = re.sub(r'^(of|with|and|or)\s+', '', part, flags=re.IGNORECASE)
                    part = re.sub(r'\s+(and|or|with)$', '', part, flags=re.IGNORECASE)
                    if part and len(part) > 2 and len(part) < 50:  # Reasonable length
                        individual_notes.append(part)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_notes = []
        for note in individual_notes:
            note_lower = note.lower().strip()
            if note_lower not in seen and note_lower:
                unique_notes.append(note.strip())
                seen.add(note_lower)
        
        # Sort notes for consistent output
        return sorted(unique_notes)
    
    def _clean_note(self, note: str) -> Optional[str]:
        """
        Clean and validate a tasting note.
        
        Args:
            note: Raw note text
            
        Returns:
            Cleaned note or None if invalid
        """
        if not note:
            return None
        
        # Clean the note
        note_clean = note.strip()
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            'tasting notes:', 'flavor notes:', 'aroma notes:', 'notes:',
            'tasting:', 'flavor:', 'aroma:', 'notes'
        ]
        
        for prefix in prefixes_to_remove:
            if note_clean.lower().startswith(prefix.lower()):
                note_clean = note_clean[len(prefix):].strip()
        
        # Remove trailing punctuation
        note_clean = note_clean.rstrip('.,;:')
        
        # Validate note quality
        if len(note_clean) < 3:
            return None
        
        # Check if note contains tasting keywords
        note_lower = note_clean.lower()
        has_tasting_keywords = any(
            keyword in note_lower for keyword in self.tasting_keywords
        )
        
        if not has_tasting_keywords:
            # Still include if it's short and seems relevant
            if len(note_clean) > 20:
                return None
        
        return note_clean
    
    def _calculate_note_confidence(self, note: str, base_confidence: float) -> float:
        """
        Calculate confidence score for a note based on its content.
        
        Args:
            note: Cleaned note text
            base_confidence: Base confidence score
            
        Returns:
            Adjusted confidence score
        """
        confidence = base_confidence
        note_lower = note.lower()
        
        # Increase confidence for notes with tasting keywords
        tasting_keyword_count = sum(
            1 for keyword in self.tasting_keywords if keyword in note_lower
        )
        
        if tasting_keyword_count > 0:
            confidence += min(0.2, tasting_keyword_count * 0.05)
        
        # Decrease confidence for very short or very long notes
        if len(note) < 10:
            confidence -= 0.1
        elif len(note) > 200:
            confidence -= 0.1
        
        # Increase confidence for notes with specific descriptors
        specific_descriptors = [
            'bright', 'clean', 'complex', 'balanced', 'full-bodied',
            'smooth', 'rich', 'bold', 'intense', 'delicate'
        ]
        
        if any(descriptor in note_lower for descriptor in specific_descriptors):
            confidence += 0.05
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    def batch_extract_notes(self, descriptions: List[str]) -> List[NotesExtractionResult]:
        """
        Extract notes from multiple descriptions in batch for performance optimization.
        
        Args:
            descriptions: List of description texts
            
        Returns:
            List of NotesExtractionResult objects
        """
        results = []
        for description in descriptions:
            result = self.extract_notes(description)
            results.append(result)
        
        total_notes = sum(result.total_notes for result in results)
        successful_extractions = sum(1 for result in results if result.extraction_success)
        
        logger.info(
            "Batch notes extraction completed",
            total_descriptions=len(descriptions),
            total_notes=total_notes,
            successful_extractions=successful_extractions,
            average_confidence=sum(
                sum(result.confidence_scores) / len(result.confidence_scores)
                for result in results if result.confidence_scores
            ) / len(results) if results else 0
        )
        
        return results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the service."""
        return {
            'service_version': '1.0.0',
            'tasting_patterns': len(self.tasting_patterns),
            'context_patterns': len(self.context_patterns),
            'tasting_keywords': len(self.tasting_keywords)
        }
