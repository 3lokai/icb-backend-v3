"""
Comprehensive tests for error_recovery.py to achieve 90%+ coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from src.parser.error_recovery import (
    RecoveryAction, RecoveryDecision, PipelineErrorRecovery
)
from src.parser.pipeline_state import PipelineState, PipelineStage, PipelineError, ParserResult


@dataclass
class MockErrorRecoveryConfig:
    """Mock configuration for error recovery."""
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_backoff: bool = True
    graceful_degradation: bool = True


class TestRecoveryDecision:
    """Test RecoveryDecision dataclass."""
    
    def test_recovery_decision_creation(self):
        """Test creating a RecoveryDecision."""
        decision = RecoveryDecision(
            action=RecoveryAction.RETRY,
            should_retry=True,
            retry_delay=2.0,
            max_retries=3,
            reason="Test retry",
            fallback_strategy="test_fallback"
        )
        
        assert decision.action == RecoveryAction.RETRY
        assert decision.should_retry is True
        assert decision.retry_delay == 2.0
        assert decision.max_retries == 3
        assert decision.reason == "Test retry"
        assert decision.fallback_strategy == "test_fallback"
    
    def test_recovery_decision_properties(self):
        """Test RecoveryDecision properties."""
        decision = RecoveryDecision(
            action=RecoveryAction.SKIP,
            should_retry=False,
            retry_delay=1.5,
            max_retries=2,
            reason="Test skip"
        )
        
        assert decision.retry_delay_seconds == 1.5
        assert decision.message == "Test skip"


class TestPipelineErrorRecovery:
    """Test PipelineErrorRecovery class."""
    
    def test_initialization(self):
        """Test PipelineErrorRecovery initialization."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        assert recovery.config == config
        assert recovery.retry_counts == {}
        assert recovery.error_history == []
    
    def test_is_recoverable_recoverable_errors(self):
        """Test is_recoverable with recoverable error messages."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        # Test recoverable error messages
        recoverable_errors = [
            "Connection timeout occurred",
            "Rate limit exceeded",
            "Network error",
            "Service temporarily unavailable",
            "Temporary failure"
        ]
        
        for error_msg in recoverable_errors:
            error = Exception(error_msg)
            assert recovery.is_recoverable(error) is True
    
    def test_is_recoverable_non_recoverable_errors(self):
        """Test is_recoverable with non-recoverable error messages."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        # Test non-recoverable error messages
        non_recoverable_errors = [
            "Invalid data format",
            "Authentication failed",
            "Permission denied",
            "File not found"
        ]
        
        for error_msg in non_recoverable_errors:
            error = Exception(error_msg)
            assert recovery.is_recoverable(error) is False
    
    def test_is_recoverable_recoverable_types(self):
        """Test is_recoverable with recoverable error types."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        # Test recoverable error types
        recoverable_errors = [
            ValueError("Test value error"),
            TypeError("Test type error"),
            ConnectionError("Test connection error"),
            TimeoutError("Test timeout error")
        ]
        
        for error in recoverable_errors:
            assert recovery.is_recoverable(error) is True
    
    def test_recover_from_parser_failure_max_retries_exceeded(self):
        """Test parser failure recovery when max retries exceeded."""
        config = MockErrorRecoveryConfig(max_retries=2)
        recovery = PipelineErrorRecovery(config)
        recovery.retry_counts["test_parser"] = 2
        
        error = Exception("Test error")
        decision = recovery.recover_from_parser_failure("test_parser", error)
        
        assert decision.action == RecoveryAction.SKIP
        assert decision.should_retry is False
        assert decision.retry_delay == 0.0
        assert "Max retries exceeded" in decision.reason
    
    def test_recover_from_parser_failure_non_recoverable_graceful_degradation(self):
        """Test parser failure recovery with non-recoverable error and graceful degradation."""
        config = MockErrorRecoveryConfig(graceful_degradation=True)
        recovery = PipelineErrorRecovery(config)
        
        error = Exception("Invalid data format")
        decision = recovery.recover_from_parser_failure("test_parser", error)
        
        assert decision.action == RecoveryAction.SKIP
        assert decision.should_retry is False
        assert "Non-recoverable error" in decision.reason
    
    def test_recover_from_parser_failure_non_recoverable_no_graceful_degradation(self):
        """Test parser failure recovery with non-recoverable error and no graceful degradation."""
        config = MockErrorRecoveryConfig(graceful_degradation=False)
        recovery = PipelineErrorRecovery(config)
        
        error = Exception("Invalid data format")
        decision = recovery.recover_from_parser_failure("test_parser", error)
        
        assert decision.action == RecoveryAction.FAIL
        assert decision.should_retry is False
        assert "Non-recoverable error" in decision.reason
    
    def test_recover_from_parser_failure_recoverable_retry(self):
        """Test parser failure recovery with recoverable error."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        error = Exception("Connection timeout")
        decision = recovery.recover_from_parser_failure("test_parser", error)
        
        assert decision.action == RecoveryAction.RETRY
        assert decision.should_retry is True
        assert decision.retry_delay > 0
        assert "Retrying" in decision.reason
        assert recovery.retry_counts["test_parser"] == 1
    
    def test_recover_from_llm_failure_max_retries_exceeded(self):
        """Test LLM failure recovery when max retries exceeded."""
        config = MockErrorRecoveryConfig(max_retries=1)
        recovery = PipelineErrorRecovery(config)
        recovery.retry_counts["llm_test_field"] = 1
        
        error = Exception("Test error")
        decision = recovery.recover_from_llm_failure("test_field", error)
        
        assert decision.action == RecoveryAction.SKIP
        assert decision.should_retry is False
        assert "Max retries exceeded" in decision.reason
    
    def test_recover_from_llm_failure_non_recoverable(self):
        """Test LLM failure recovery with non-recoverable error."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        error = Exception("Invalid data format")
        decision = recovery.recover_from_llm_failure("test_field", error)
        
        assert decision.action == RecoveryAction.FAIL
        assert decision.should_retry is False
        assert "Non-recoverable LLM error" in decision.reason
    
    def test_recover_from_llm_failure_recoverable_retry(self):
        """Test LLM failure recovery with recoverable error."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        error = Exception("Connection timeout")
        decision = recovery.recover_from_llm_failure("test_field", error)
        
        assert decision.action == RecoveryAction.RETRY
        assert decision.should_retry is True
        assert decision.retry_delay > 0
        assert "Retrying LLM field" in decision.reason
        assert recovery.retry_counts["llm_test_field"] == 1
    
    def test_recover_from_pipeline_failure_with_partial_results(self):
        """Test pipeline failure recovery with partial results."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        result = ParserResult(
            parser_name="test_parser",
            success=True,
            confidence=0.8
        )
        state.add_parser_result("test_parser", result)
        
        error = Exception("Pipeline error")
        decision = recovery.recover_from_pipeline_failure(state, error)
        
        assert decision.action == RecoveryAction.FALLBACK
        assert decision.should_retry is False
        assert decision.fallback_strategy == "use_partial_results"
        assert "partial results available" in decision.reason
    
    def test_recover_from_pipeline_failure_non_recoverable(self):
        """Test pipeline failure recovery with non-recoverable error."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        error = Exception("Invalid data format")
        decision = recovery.recover_from_pipeline_failure(state, error)
        
        assert decision.action == RecoveryAction.FAIL
        assert decision.should_retry is False
        assert "Non-recoverable pipeline error" in decision.reason
    
    def test_recover_from_pipeline_failure_recoverable_graceful_degradation(self):
        """Test pipeline failure recovery with recoverable error and graceful degradation."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        error = Exception("Connection timeout")
        decision = recovery.recover_from_pipeline_failure(state, error)
        
        assert decision.action == RecoveryAction.FALLBACK
        assert decision.should_retry is False
        assert decision.fallback_strategy == "graceful_degradation"
        assert "graceful degradation" in decision.reason
    
    def test_calculate_retry_delay_no_exponential_backoff(self):
        """Test retry delay calculation without exponential backoff."""
        config = MockErrorRecoveryConfig(exponential_backoff=False, retry_delay_seconds=2.0)
        recovery = PipelineErrorRecovery(config)
        
        delay = recovery._calculate_retry_delay(3)
        assert delay == 2.0
    
    def test_calculate_retry_delay_with_exponential_backoff(self):
        """Test retry delay calculation with exponential backoff."""
        config = MockErrorRecoveryConfig(
            exponential_backoff=True,
            retry_delay_seconds=1.0,
            max_delay_seconds=10.0
        )
        recovery = PipelineErrorRecovery(config)
        
        # Test exponential backoff
        delay1 = recovery._calculate_retry_delay(0)
        delay2 = recovery._calculate_retry_delay(1)
        delay3 = recovery._calculate_retry_delay(2)
        
        assert delay1 == 1.0  # 1 * 2^0
        assert delay2 == 2.0  # 1 * 2^1
        assert delay3 == 4.0  # 1 * 2^2
    
    def test_calculate_retry_delay_max_delay_limit(self):
        """Test retry delay calculation with max delay limit."""
        config = MockErrorRecoveryConfig(
            exponential_backoff=True,
            retry_delay_seconds=1.0,
            max_delay_seconds=5.0
        )
        recovery = PipelineErrorRecovery(config)
        
        # Test that delay is capped at max_delay_seconds
        delay = recovery._calculate_retry_delay(10)  # Would be 1024 without cap
        assert delay == 5.0
    
    @patch('src.parser.error_recovery.logger')
    def test_reset_retry_counts(self, mock_logger):
        """Test resetting retry counts."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        recovery.retry_counts["parser1"] = 2
        recovery.retry_counts["parser2"] = 1
        
        recovery.reset_retry_counts()
        
        assert recovery.retry_counts == {}
        mock_logger.info.assert_called_once_with("Retry counts reset")
    
    def test_get_retry_count(self):
        """Test getting retry count for specific parser."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        recovery.retry_counts["test_parser"] = 3
        
        assert recovery.get_retry_count("test_parser") == 3
        assert recovery.get_retry_count("nonexistent_parser") == 0
    
    @patch('src.parser.error_recovery.logger')
    def test_record_error(self, mock_logger):
        """Test recording an error."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        
        recovery.record_error(error)
        
        assert len(recovery.error_history) == 1
        assert recovery.error_history[0] == error
        mock_logger.warning.assert_called_once()
    
    def test_get_error_summary_no_errors(self):
        """Test getting error summary with no errors."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        summary = recovery.get_error_summary()
        
        assert summary["total_errors"] == 0
        assert summary["error_types"] == {}
        assert summary["recoverable_errors"] == 0
    
    def test_get_error_summary_with_errors(self):
        """Test getting error summary with errors."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        # Add some errors
        error1 = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Error 1",
            recoverable=True
        )
        error2 = PipelineError(
            stage=PipelineStage.LLM_FALLBACK,
            error_type="LLMError",
            message="Error 2",
            recoverable=False
        )
        error3 = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Error 3",
            recoverable=True
        )
        
        recovery.record_error(error1)
        recovery.record_error(error2)
        recovery.record_error(error3)
        
        summary = recovery.get_error_summary()
        
        assert summary["total_errors"] == 3
        assert summary["error_types"]["ParseError"] == 2
        assert summary["error_types"]["LLMError"] == 1
        assert summary["recoverable_errors"] == 2
        assert summary["recovery_rate"] == 2/3
    
    def test_should_continue_processing_no_graceful_degradation(self):
        """Test should_continue_processing without graceful degradation."""
        config = MockErrorRecoveryConfig(graceful_degradation=False)
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        # No errors
        assert recovery.should_continue_processing(state) is True
        
        # With errors
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        state.add_error(error)
        assert recovery.should_continue_processing(state) is False
    
    def test_should_continue_processing_with_graceful_degradation_success(self):
        """Test should_continue_processing with graceful degradation and success."""
        config = MockErrorRecoveryConfig(graceful_degradation=True)
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        
        # Add successful results (60% success rate)
        result1 = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.8
        )
        result2 = ParserResult(
            parser_name="parser2",
            success=True,
            confidence=0.7
        )
        result3 = ParserResult(
            parser_name="parser3",
            success=False,
            confidence=0.3
        )
        
        state.add_parser_result("parser1", result1)
        state.add_parser_result("parser2", result2)
        state.add_parser_result("parser3", result3)
        
        assert recovery.should_continue_processing(state) is True
    
    def test_should_continue_processing_with_graceful_degradation_failure(self):
        """Test should_continue_processing with graceful degradation and failure."""
        config = MockErrorRecoveryConfig(graceful_degradation=True)
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        
        # Add mostly failed results (30% success rate)
        result1 = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.8
        )
        result2 = ParserResult(
            parser_name="parser2",
            success=False,
            confidence=0.3
        )
        result3 = ParserResult(
            parser_name="parser3",
            success=False,
            confidence=0.2
        )
        
        state.add_parser_result("parser1", result1)
        state.add_parser_result("parser2", result2)
        state.add_parser_result("parser3", result3)
        
        assert recovery.should_continue_processing(state) is False
    
    def test_should_continue_processing_no_parsers(self):
        """Test should_continue_processing with no parsers."""
        config = MockErrorRecoveryConfig(graceful_degradation=True)
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        assert recovery.should_continue_processing(state) is False
    
    def test_get_fallback_strategy_no_errors(self):
        """Test get_fallback_strategy with no errors."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        strategy = recovery.get_fallback_strategy(state)
        
        assert strategy is None
    
    def test_get_fallback_strategy_high_success_rate(self):
        """Test get_fallback_strategy with high success rate."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        
        # Add mostly successful results (70% success rate)
        result1 = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.8
        )
        result2 = ParserResult(
            parser_name="parser2",
            success=True,
            confidence=0.7
        )
        result3 = ParserResult(
            parser_name="parser3",
            success=False,
            confidence=0.3
        )
        
        state.add_parser_result("parser1", result1)
        state.add_parser_result("parser2", result2)
        state.add_parser_result("parser3", result3)
        
        # Add an error to trigger fallback strategy
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        state.add_error(error)
        
        strategy = recovery.get_fallback_strategy(state)
        assert strategy == "use_partial_results"
    
    def test_get_fallback_strategy_low_success_rate(self):
        """Test get_fallback_strategy with low success rate."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        
        # Add mostly failed results (30% success rate)
        result1 = ParserResult(
            parser_name="parser1",
            success=True,
            confidence=0.8
        )
        result2 = ParserResult(
            parser_name="parser2",
            success=False,
            confidence=0.3
        )
        result3 = ParserResult(
            parser_name="parser3",
            success=False,
            confidence=0.2
        )
        
        state.add_parser_result("parser1", result1)
        state.add_parser_result("parser2", result2)
        state.add_parser_result("parser3", result3)
        
        # Add an error to trigger fallback strategy
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        state.add_error(error)
        
        strategy = recovery.get_fallback_strategy(state)
        assert strategy == "minimal_processing"
    
    def test_get_fallback_strategy_no_success(self):
        """Test get_fallback_strategy with no successful results."""
        config = MockErrorRecoveryConfig()
        recovery = PipelineErrorRecovery(config)
        
        state = PipelineState()
        
        # Add all failed results
        result1 = ParserResult(
            parser_name="parser1",
            success=False,
            confidence=0.3
        )
        result2 = ParserResult(
            parser_name="parser2",
            success=False,
            confidence=0.2
        )
        
        state.add_parser_result("parser1", result1)
        state.add_parser_result("parser2", result2)
        
        # Add an error to trigger fallback strategy
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="ParseError",
            message="Test error"
        )
        state.add_error(error)
        
        strategy = recovery.get_fallback_strategy(state)
        assert strategy == "skip_processing"
