"""
Tests for notes extraction service.
"""

import pytest
from src.parser.notes_extraction import NotesExtractionService, NotesExtractionResult


class TestNotesExtractionService:
    """Test cases for NotesExtractionService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = NotesExtractionService()
    
    def test_initialization(self):
        """Test service initialization."""
        assert self.service is not None
        assert len(self.service.tasting_patterns) > 0
        assert len(self.service.context_patterns) > 0
        assert len(self.service.tasting_keywords) > 0
        assert len(self.service.high_confidence_patterns) > 0
        assert len(self.service.medium_confidence_patterns) > 0
        assert len(self.service.low_confidence_patterns) > 0
    
    def test_extract_notes_empty_input(self):
        """Test extraction with empty input."""
        result = self.service.extract_notes("")
        
        assert isinstance(result, NotesExtractionResult)
        assert result.notes_raw == []
        assert result.confidence_scores == []
        assert result.warnings == ['No description provided']
        assert result.total_notes == 0
        assert result.extraction_success is False
    
    def test_extract_notes_none_input(self):
        """Test extraction with None input."""
        result = self.service.extract_notes(None)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.notes_raw == []
        assert result.confidence_scores == []
        assert result.warnings == ['Invalid input type - expected string']
        assert result.total_notes == 0
        assert result.extraction_success is False
    
    def test_extract_notes_high_confidence_patterns(self):
        """Test extraction with high confidence patterns."""
        description = "Tasting notes: This coffee has chocolate and caramel flavors with a smooth finish."
        result = self.service.extract_notes(description)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.extraction_success is True
        assert result.total_notes > 0
        assert len(result.notes_raw) > 0
        assert len(result.confidence_scores) > 0
        assert all(score >= 0.8 for score in result.confidence_scores)
    
    def test_extract_notes_medium_confidence_patterns(self):
        """Test extraction with medium confidence patterns."""
        description = "This coffee features flavors of chocolate and caramel with hints of vanilla."
        result = self.service.extract_notes(description)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.extraction_success is True
        assert result.total_notes > 0
        assert len(result.notes_raw) > 0
        assert len(result.confidence_scores) > 0
    
    def test_extract_notes_low_confidence_patterns(self):
        """Test extraction with low confidence patterns."""
        description = "This coffee is smooth and rich with chocolate undertones."
        result = self.service.extract_notes(description)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.extraction_success is True
        assert result.total_notes > 0
        assert len(result.notes_raw) > 0
        assert len(result.confidence_scores) > 0
    
    def test_extract_notes_multiple_patterns(self):
        """Test extraction with multiple pattern types."""
        description = """
        Tasting notes: This coffee has chocolate and caramel flavors.
        It features hints of vanilla and a smooth finish.
        The coffee is rich and full-bodied with earthy undertones.
        """
        result = self.service.extract_notes(description)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.extraction_success is True
        assert result.total_notes > 0
        assert len(result.notes_raw) > 0
        assert len(result.confidence_scores) > 0
    
    def test_extract_notes_no_tasting_content(self):
        """Test extraction with no tasting content."""
        description = "This is a regular product description with no tasting notes."
        result = self.service.extract_notes(description)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.extraction_success is False
        assert result.total_notes == 0
        assert len(result.notes_raw) == 0
        assert len(result.confidence_scores) == 0
    
    def test_extract_notes_case_insensitive(self):
        """Test extraction is case insensitive."""
        description = "TASTING NOTES: This coffee has CHOCOLATE and CARAMEL flavors."
        result = self.service.extract_notes(description)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.extraction_success is True
        assert result.total_notes > 0
        assert len(result.notes_raw) > 0
    
    def test_extract_notes_whitespace_handling(self):
        """Test extraction handles whitespace correctly."""
        description = "   Tasting notes:   This coffee has chocolate and caramel flavors.   "
        result = self.service.extract_notes(description)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.extraction_success is True
        assert result.total_notes > 0
        # Check that extracted notes don't have extra whitespace
        for note in result.notes_raw:
            assert note == note.strip()
    
    def test_extract_notes_duplicate_removal(self):
        """Test extraction removes duplicates."""
        description = "Tasting notes: This coffee has chocolate and caramel flavors. It also has chocolate undertones."
        result = self.service.extract_notes(description)
        
        assert isinstance(result, NotesExtractionResult)
        assert result.extraction_success is True
        assert result.total_notes > 0
        # Check for no duplicates
        unique_notes = set(note.lower() for note in result.notes_raw)
        assert len(unique_notes) == len(result.notes_raw)
    
    def test_batch_extract_notes(self):
        """Test batch extraction."""
        descriptions = [
            "Tasting notes: This coffee has chocolate and caramel flavors.",
            "This coffee features hints of vanilla and a smooth finish.",
            "This is a regular product description with no tasting notes."
        ]
        results = self.service.batch_extract_notes(descriptions)
        
        assert len(results) == 3
        assert all(isinstance(result, NotesExtractionResult) for result in results)
        assert results[0].extraction_success is True
        assert results[1].extraction_success is True
        assert results[2].extraction_success is False
    
    def test_batch_extract_notes_empty_list(self):
        """Test batch extraction with empty list."""
        results = self.service.batch_extract_notes([])
        
        assert len(results) == 0
    
    def test_clean_note_valid_note(self):
        """Test note cleaning with valid note."""
        note = "  This coffee has chocolate and caramel flavors.  "
        cleaned = self.service._clean_note(note)
        
        assert cleaned == "This coffee has chocolate and caramel flavors"
        assert len(cleaned) > 3
    
    def test_clean_note_invalid_note(self):
        """Test note cleaning with invalid note."""
        note = "  "
        cleaned = self.service._clean_note(note)
        
        assert cleaned is None
    
    def test_clean_note_short_note(self):
        """Test note cleaning with short note."""
        note = "ok"
        cleaned = self.service._clean_note(note)
        
        assert cleaned is None
    
    def test_clean_note_prefix_removal(self):
        """Test note cleaning removes common prefixes."""
        note = "Tasting notes: This coffee has chocolate flavors."
        cleaned = self.service._clean_note(note)
        
        assert cleaned == "This coffee has chocolate flavors"
        assert not cleaned.lower().startswith('tasting notes')
    
    def test_calculate_note_confidence_high_quality(self):
        """Test confidence calculation for high quality note."""
        note = "This coffee has chocolate and caramel flavors with a smooth finish."
        confidence = self.service._calculate_note_confidence(note, 0.8)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence >= 0.8  # Should be at least base confidence
    
    def test_calculate_note_confidence_low_quality(self):
        """Test confidence calculation for low quality note."""
        note = "ok"
        confidence = self.service._calculate_note_confidence(note, 0.8)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.8  # Should be lower than base confidence
    
    def test_calculate_note_confidence_bounds(self):
        """Test confidence calculation stays within bounds."""
        note = "This coffee has chocolate flavors."
        confidence = self.service._calculate_note_confidence(note, 0.5)
        
        assert 0.0 <= confidence <= 1.0
    
    def test_extract_with_patterns_high_confidence(self):
        """Test pattern extraction with high confidence patterns."""
        text = "Tasting notes: This coffee has chocolate and caramel flavors."
        result = self.service._extract_with_patterns(
            text, 
            self.service.high_confidence_patterns, 
            0.9
        )
        
        assert 'notes' in result
        assert 'scores' in result
        assert 'warnings' in result
        assert len(result['notes']) > 0
        assert len(result['scores']) > 0
        assert all(score >= 0.8 for score in result['scores'])
    
    def test_extract_with_patterns_medium_confidence(self):
        """Test pattern extraction with medium confidence patterns."""
        text = "This coffee features flavors of chocolate and caramel."
        result = self.service._extract_with_patterns(
            text, 
            self.service.medium_confidence_patterns, 
            0.7
        )
        
        assert 'notes' in result
        assert 'scores' in result
        assert 'warnings' in result
        assert len(result['notes']) > 0
        assert len(result['scores']) > 0
    
    def test_extract_with_patterns_low_confidence(self):
        """Test pattern extraction with low confidence patterns."""
        text = "This coffee is smooth and rich with chocolate undertones."
        result = self.service._extract_with_patterns(
            text, 
            self.service.low_confidence_patterns, 
            0.5
        )
        
        assert 'notes' in result
        assert 'scores' in result
        assert 'warnings' in result
        assert len(result['notes']) > 0
        assert len(result['scores']) > 0
    
    def test_get_performance_metrics(self):
        """Test performance metrics."""
        metrics = self.service.get_performance_metrics()
        
        assert 'service_version' in metrics
        assert 'tasting_patterns' in metrics
        assert 'context_patterns' in metrics
        assert 'tasting_keywords' in metrics
        assert 'high_confidence_patterns' in metrics
        assert 'medium_confidence_patterns' in metrics
        assert 'low_confidence_patterns' in metrics
        
        assert metrics['service_version'] == '1.0.0'
        assert metrics['tasting_patterns'] > 0
        assert metrics['context_patterns'] > 0
        assert metrics['tasting_keywords'] > 0
        assert metrics['high_confidence_patterns'] > 0
        assert metrics['medium_confidence_patterns'] > 0
        assert metrics['low_confidence_patterns'] > 0
    
    def test_notes_extraction_result_serialization(self):
        """Test NotesExtractionResult serialization."""
        result = NotesExtractionResult(
            notes_raw=['chocolate', 'caramel'],
            confidence_scores=[0.9, 0.8],
            warnings=[],
            total_notes=2,
            extraction_success=True
        )
        
        # Test to_dict
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert 'notes_raw' in result_dict
        assert 'confidence_scores' in result_dict
        assert 'warnings' in result_dict
        assert 'total_notes' in result_dict
        assert 'extraction_success' in result_dict
        
        # Test from_dict
        restored_result = NotesExtractionResult.from_dict(result_dict)
        assert restored_result.notes_raw == result.notes_raw
        assert restored_result.confidence_scores == result.confidence_scores
        assert restored_result.warnings == result.warnings
        assert restored_result.total_notes == result.total_notes
        assert restored_result.extraction_success == result.extraction_success
    
    def test_error_handling(self):
        """Test error handling in extraction."""
        # Test with invalid input types
        result = self.service.extract_notes(123)
        assert isinstance(result, NotesExtractionResult)
        # Should handle gracefully without crashing
    
    def test_tasting_keywords_detection(self):
        """Test detection of tasting keywords."""
        description = "This coffee has chocolate, caramel, and vanilla flavors with a smooth finish."
        result = self.service.extract_notes(description)
        
        assert result.extraction_success is True
        assert result.total_notes > 0
        assert len(result.notes_raw) > 0
    
    def test_context_patterns_detection(self):
        """Test detection of context patterns."""
        description = "This coffee features a complex flavor profile with notes of chocolate and caramel."
        result = self.service.extract_notes(description)
        
        assert result.extraction_success is True
        assert result.total_notes > 0
        assert len(result.notes_raw) > 0
    
    def test_multiline_description(self):
        """Test extraction from multiline description."""
        description = """
        This is a premium coffee from Karnataka.
        
        Tasting notes: This coffee has chocolate and caramel flavors
        with a smooth finish and hints of vanilla.
        
        Brewing instructions: Use 1:15 ratio for best results.
        """
        result = self.service.extract_notes(description)
        
        assert result.extraction_success is True
        assert result.total_notes > 0
        assert len(result.notes_raw) > 0
