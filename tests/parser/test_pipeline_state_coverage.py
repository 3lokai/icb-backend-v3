"""
Comprehensive tests for pipeline_state.py to achieve 90%+ coverage.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.parser.pipeline_state import (
    PipelineStage, PipelineError, PipelineWarning, ParserResult, 
    LLMResult, PipelineState
)


class TestPipelineError:
    """Test PipelineError model."""
    
    def test_pipeline_error_creation(self):
        """Test creating a PipelineError."""
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Failed to parse data",
            recoverable=True,
            parser_name="test_parser"
        )
        
        assert error.stage == PipelineStage.DETERMINISTIC_PARSING
        assert error.error_type == "ParseError"
        assert error.message == "Failed to parse data"
        assert error.recoverable is True
        assert error.parser_name == "test_parser"
        assert isinstance(error.timestamp, datetime)
    
    def test_pipeline_error_to_dict(self):
        """Test converting PipelineError to dictionary."""
        error = PipelineError(
            stage=PipelineStage.LLM_FALLBACK,
            error_type="LLMError",
            message="LLM processing failed"
        )
        
        result = error.to_dict()
        
        assert isinstance(result, dict)
        assert result['stage'] == PipelineStage.LLM_FALLBACK
        assert result['error_type'] == "LLMError"
        assert result['message'] == "LLM processing failed"
        assert result['recoverable'] is True  # default value
        assert result['parser_name'] is None  # default value
        assert 'timestamp' in result


class TestPipelineWarning:
    """Test PipelineWarning model."""
    
    def test_pipeline_warning_creation(self):
        """Test creating a PipelineWarning."""
        warning = PipelineWarning(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            parser_name="test_parser",
            message="Low confidence parsing",
            severity="medium"
        )
        
        assert warning.stage == PipelineStage.DETERMINISTIC_PARSING
        assert warning.parser_name == "test_parser"
        assert warning.message == "Low confidence parsing"
        assert warning.severity == "medium"
        assert isinstance(warning.timestamp, datetime)
    
    def test_pipeline_warning_to_dict(self):
        """Test converting PipelineWarning to dictionary."""
        warning = PipelineWarning(
            stage=PipelineStage.COMPLETED,
            message="Processing completed with warnings"
        )
        
        result = warning.to_dict()
        
        assert isinstance(result, dict)
        assert result['stage'] == PipelineStage.COMPLETED
        assert result['message'] == "Processing completed with warnings"
        assert result['parser_name'] is None  # default value
        assert result['severity'] == "low"  # default value
        assert 'timestamp' in result


class TestParserResult:
    """Test ParserResult model."""
    
    def test_parser_result_creation(self):
        """Test creating a ParserResult."""
        result = ParserResult(
            parser_name="test_parser",
            success=True,
            confidence=0.85,
            result_data={"field": "value"},
            warnings=["Low confidence"],
            execution_time=1.5
        )
        
        assert result.parser_name == "test_parser"
        assert result.success is True
        assert result.confidence == 0.85
        assert result.result_data == {"field": "value"}
        assert result.warnings == ["Low confidence"]
        assert result.execution_time == 1.5
        assert isinstance(result.timestamp, datetime)
    
    def test_parser_result_to_dict(self):
        """Test converting ParserResult to dictionary."""
        result = ParserResult(
            parser_name="test_parser",
            success=False,
            confidence=0.3
        )
        
        dict_result = result.to_dict()
        
        assert isinstance(dict_result, dict)
        assert dict_result['parser_name'] == "test_parser"
        assert dict_result['success'] is False
        assert dict_result['confidence'] == 0.3
        assert dict_result['result_data'] == {}  # default value
        assert dict_result['warnings'] == []  # default value
        assert dict_result['execution_time'] == 0.0  # default value
        assert 'timestamp' in dict_result


class TestLLMResult:
    """Test LLMResult model."""
    
    def test_llm_result_creation(self):
        """Test creating an LLMResult."""
        result = LLMResult(
            field_name="test_field",
            success=True,
            confidence=0.9,
            result_data={"parsed": "data"},
            warnings=["High confidence"],
            execution_time=2.0
        )
        
        assert result.field_name == "test_field"
        assert result.success is True
        assert result.confidence == 0.9
        assert result.result_data == {"parsed": "data"}
        assert result.warnings == ["High confidence"]
        assert result.execution_time == 2.0
        assert isinstance(result.timestamp, datetime)
    
    def test_llm_result_to_dict(self):
        """Test converting LLMResult to dictionary."""
        result = LLMResult(
            field_name="test_field",
            success=False,
            confidence=0.2
        )
        
        dict_result = result.to_dict()
        
        assert isinstance(dict_result, dict)
        assert dict_result['field_name'] == "test_field"
        assert dict_result['success'] is False
        assert dict_result['confidence'] == 0.2
        assert dict_result['result_data'] == {}  # default value
        assert dict_result['warnings'] == []  # default value
        assert dict_result['execution_time'] == 0.0  # default value
        assert 'timestamp' in dict_result


class TestPipelineState:
    """Test PipelineState model."""
    
    def test_pipeline_state_creation(self):
        """Test creating a PipelineState."""
        state = PipelineState()
        
        assert isinstance(state.execution_id, str)
        assert state.stage == PipelineStage.INITIALIZED
        assert state.deterministic_results == {}
        assert state.llm_results == {}
        assert state.errors == []
        assert state.warnings == []
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime)
    
    @patch('src.parser.pipeline_state.logger')
    def test_add_error(self, mock_logger):
        """Test adding an error to pipeline state."""
        state = PipelineState()
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        
        state.add_error(error)
        
        assert len(state.errors) == 1
        assert state.errors[0] == error
        assert isinstance(state.updated_at, datetime)
        mock_logger.warning.assert_called_once()
    
    @patch('src.parser.pipeline_state.logger')
    def test_add_warning(self, mock_logger):
        """Test adding a warning to pipeline state."""
        state = PipelineState()
        warning = PipelineWarning(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            message="Test warning"
        )
        
        state.add_warning(warning)
        
        assert len(state.warnings) == 1
        assert state.warnings[0] == warning
        assert isinstance(state.updated_at, datetime)
        mock_logger.info.assert_called_once()
    
    @patch('src.parser.pipeline_state.logger')
    def test_add_parser_result(self, mock_logger):
        """Test adding a parser result."""
        state = PipelineState()
        result = ParserResult(
            parser_name="test_parser",
            success=True,
            confidence=0.8
        )
        
        state.add_parser_result("test_parser", result)
        
        assert "test_parser" in state.deterministic_results
        assert state.deterministic_results["test_parser"] == result
        assert isinstance(state.updated_at, datetime)
        mock_logger.debug.assert_called_once()
    
    @patch('src.parser.pipeline_state.logger')
    def test_add_llm_result(self, mock_logger):
        """Test adding an LLM result."""
        state = PipelineState()
        result = LLMResult(
            field_name="test_field",
            success=True,
            confidence=0.9
        )
        
        state.add_llm_result("test_field", result)
        
        assert "test_field" in state.llm_results
        assert state.llm_results["test_field"] == result
        assert isinstance(state.updated_at, datetime)
        mock_logger.debug.assert_called_once()
    
    def test_get_overall_confidence_no_results(self):
        """Test overall confidence with no results."""
        state = PipelineState()
        
        assert state.get_overall_confidence() == 0.0
    
    def test_get_overall_confidence_with_deterministic_results(self):
        """Test overall confidence with deterministic results."""
        state = PipelineState()
        
        result1 = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.8
        )
        result2 = ParserResult(
            parser_name="parser2",
            success=True,
            confidence=0.6
        )
        
        state.add_parser_result("parser1", result1)
        state.add_parser_result("parser2", result2)
        
        assert state.get_overall_confidence() == 0.7  # (0.8 + 0.6) / 2
    
    def test_get_overall_confidence_with_llm_results(self):
        """Test overall confidence with LLM results."""
        state = PipelineState()
        
        result1 = LLMResult(
            field_name="field1",
            success=True,
            confidence=0.9
        )
        result2 = LLMResult(
            field_name="field2",
            success=True,
            confidence=0.7
        )
        
        state.add_llm_result("field1", result1)
        state.add_llm_result("field2", result2)
        
        assert state.get_overall_confidence() == 0.8  # (0.9 + 0.7) / 2
    
    def test_get_overall_confidence_mixed_results(self):
        """Test overall confidence with both deterministic and LLM results."""
        state = PipelineState()
        
        parser_result = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.6
        )
        llm_result = LLMResult(
            field_name="field1",
            success=True,
            confidence=0.8
        )
        
        state.add_parser_result("parser1", parser_result)
        state.add_llm_result("field1", llm_result)
        
        assert state.get_overall_confidence() == 0.7  # (0.6 + 0.8) / 2
    
    def test_get_deterministic_confidence_no_results(self):
        """Test deterministic confidence with no results."""
        state = PipelineState()
        
        assert state.get_deterministic_confidence() == 0.0
    
    def test_get_deterministic_confidence_with_results(self):
        """Test deterministic confidence with results."""
        state = PipelineState()
        
        result1 = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.8
        )
        result2 = ParserResult(
            parser_name="parser2",
            success=True,
            confidence=0.6
        )
        
        state.add_parser_result("parser1", result1)
        state.add_parser_result("parser2", result2)
        
        assert state.get_deterministic_confidence() == 0.7
    
    def test_get_llm_confidence_no_results(self):
        """Test LLM confidence with no results."""
        state = PipelineState()
        
        assert state.get_llm_confidence() == 0.0
    
    def test_get_llm_confidence_with_results(self):
        """Test LLM confidence with results."""
        state = PipelineState()
        
        result1 = LLMResult(
            field_name="field1",
            success=True,
            confidence=0.9
        )
        result2 = LLMResult(
            field_name="field2",
            success=True,
            confidence=0.7
        )
        
        state.add_llm_result("field1", result1)
        state.add_llm_result("field2", result2)
        
        assert state.get_llm_confidence() == 0.8
    
    def test_has_errors_no_errors(self):
        """Test has_errors with no errors."""
        state = PipelineState()
        
        assert state.has_errors() is False
    
    def test_has_errors_with_errors(self):
        """Test has_errors with errors."""
        state = PipelineState()
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        state.add_error(error)
        
        assert state.has_errors() is True
    
    def test_has_warnings_no_warnings(self):
        """Test has_warnings with no warnings."""
        state = PipelineState()
        
        assert state.has_warnings() is False
    
    def test_has_warnings_with_warnings(self):
        """Test has_warnings with warnings."""
        state = PipelineState()
        warning = PipelineWarning(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            message="Test warning"
        )
        state.add_warning(warning)
        
        assert state.has_warnings() is True
    
    def test_is_completed_success(self):
        """Test is_completed with successful completion."""
        state = PipelineState()
        state.stage = PipelineStage.COMPLETED
        
        assert state.is_completed() is True
    
    def test_is_completed_with_errors(self):
        """Test is_completed with errors."""
        state = PipelineState()
        state.stage = PipelineStage.COMPLETED
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        state.add_error(error)
        
        assert state.is_completed() is False
    
    def test_is_completed_not_completed_stage(self):
        """Test is_completed with non-completed stage."""
        state = PipelineState()
        state.stage = PipelineStage.DETERMINISTIC_PARSING
        
        assert state.is_completed() is False
    
    def test_needs_llm_fallback_high_confidence(self):
        """Test needs_llm_fallback with high confidence."""
        state = PipelineState()
        
        result = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.9
        )
        state.add_parser_result("parser1", result)
        
        assert state.needs_llm_fallback(threshold=0.7) is False
    
    def test_needs_llm_fallback_low_confidence(self):
        """Test needs_llm_fallback with low confidence."""
        state = PipelineState()
        
        result = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.5
        )
        state.add_parser_result("parser1", result)
        
        assert state.needs_llm_fallback(threshold=0.7) is True
    
    def test_needs_llm_fallback_no_results(self):
        """Test needs_llm_fallback with no results."""
        state = PipelineState()
        
        assert state.needs_llm_fallback(threshold=0.7) is True
    
    def test_to_dict(self):
        """Test converting PipelineState to dictionary."""
        state = PipelineState()
        
        # Add some data
        parser_result = ParserResult(
            parser_name="test_parser",
            success=True,
            confidence=0.8
        )
        state.add_parser_result("test_parser", parser_result)
        
        llm_result = LLMResult(
            field_name="test_field",
            success=True,
            confidence=0.9
        )
        state.add_llm_result("test_field", llm_result)
        
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        state.add_error(error)
        
        warning = PipelineWarning(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            message="Test warning"
        )
        state.add_warning(warning)
        
        result = state.to_dict()
        
        assert isinstance(result, dict)
        assert 'execution_id' in result
        assert result['stage'] == PipelineStage.INITIALIZED.value
        assert 'deterministic_results' in result
        assert 'llm_results' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'created_at' in result
        assert 'updated_at' in result
    
    def test_from_dict(self):
        """Test creating PipelineState from dictionary."""
        data = {
            'execution_id': 'test-id',
            'stage': 'initialized',
            'deterministic_results': {
                'test_parser': {
                    'parser_name': 'test_parser',
                    'success': True,
                    'confidence': 0.8,
                    'result_data': {},
                    'warnings': [],
                    'execution_time': 0.0,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            },
            'llm_results': {
                'test_field': {
                    'field_name': 'test_field',
                    'success': True,
                    'confidence': 0.9,
                    'result_data': {},
                    'warnings': [],
                    'execution_time': 0.0,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            },
            'errors': [{
                'stage': 'deterministic_parsing',
                'error_type': 'ParseError',
                'message': 'Test error',
                'recoverable': True,
                'parser_name': None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }],
            'warnings': [{
                'stage': 'deterministic_parsing',
                'parser_name': None,
                'message': 'Test warning',
                'severity': 'low',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        state = PipelineState.from_dict(data)
        
        assert state.execution_id == 'test-id'
        assert state.stage == PipelineStage.INITIALIZED
        assert len(state.deterministic_results) == 1
        assert len(state.llm_results) == 1
        assert len(state.errors) == 1
        assert len(state.warnings) == 1
    
    def test_from_dict_with_stage_enum(self):
        """Test from_dict with stage already as enum."""
        data = {
            'execution_id': 'test-id',
            'stage': PipelineStage.COMPLETED,
            'deterministic_results': {},
            'llm_results': {},
            'errors': [],
            'warnings': [],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        state = PipelineState.from_dict(data)
        
        assert state.stage == PipelineStage.COMPLETED
