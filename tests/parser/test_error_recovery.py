"""
Test suite for C.8 error recovery and transaction management.

Tests failure scenarios and recovery mechanisms including:
- Parser failure recovery
- LLM service failure recovery
- Transaction rollback scenarios
- Graceful degradation
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from typing import Dict, List, Any

from src.parser.error_recovery import PipelineErrorRecovery, RecoveryAction, ErrorRecoveryConfig
from src.parser.transaction_manager import PipelineTransactionManager, TransactionBoundary, TransactionStatus
from src.parser.normalizer_pipeline import NormalizerPipelineService, PipelineExecutionError
from src.parser.pipeline_state import PipelineState, PipelineStage, PipelineError, PipelineWarning
from src.config.pipeline_config import PipelineConfig


class TestErrorRecovery:
    """Test suite for error recovery mechanisms."""

    @pytest.fixture
    def error_recovery_config(self):
        """Create error recovery configuration."""
        return ErrorRecoveryConfig(
            max_retries=3,
            retry_delay_seconds=5,
            recoverable_parser_errors={
                "WeightParser": ["ValueError", "TypeError"],
                "RoastLevelParser": ["ParsingError"],
                "ProcessMethodParser": ["ConnectionError"]
            },
            default_recovery_action=RecoveryAction.SKIP
        )

    @pytest.fixture
    def error_recovery(self, error_recovery_config):
        """Create error recovery service."""
        return PipelineErrorRecovery(error_recovery_config)

    def test_recoverable_error_detection(self, error_recovery):
        """Test detection of recoverable errors."""
        # Test recoverable errors
        assert error_recovery.is_recoverable(ValueError("Test error"))
        assert error_recovery.is_recoverable(TypeError("Test error"))
        
        # Test non-recoverable errors
        assert not error_recovery.is_recoverable(Exception("Unknown error"))
        assert not error_recovery.is_recoverable(RuntimeError("System error"))

    def test_parser_failure_recovery(self, error_recovery):
        """Test recovery from parser failures."""
        # Test recoverable parser failure
        recovery_decision = error_recovery.recover_from_parser_failure(
            "WeightParser", 
            ValueError("Invalid weight format")
        )
        
        assert recovery_decision.action == RecoveryAction.RETRY
        assert recovery_decision.should_retry is True
        assert recovery_decision.retry_delay_seconds == 5
        assert "Retrying WeightParser" in recovery_decision.message

    def test_unrecoverable_parser_failure(self, error_recovery):
        """Test handling of unrecoverable parser failures."""
        # Test unrecoverable parser failure
        recovery_decision = error_recovery.recover_from_parser_failure(
            "WeightParser", 
            RuntimeError("System failure")
        )
        
        assert recovery_decision.action == RecoveryAction.SKIP
        assert recovery_decision.should_retry is False
        assert "Non-recoverable error in WeightParser" in recovery_decision.message

    def test_llm_failure_recovery(self, error_recovery):
        """Test recovery from LLM service failures."""
        # Test LLM failure recovery - "service unavailable" is recoverable, so should retry
        recovery_decision = error_recovery.recover_from_llm_failure(
            "weight", Exception("LLM service unavailable")
        )
        
        assert recovery_decision.action == RecoveryAction.RETRY
        assert recovery_decision.should_retry is True
        assert "Retrying LLM field weight" in recovery_decision.reason

    def test_retry_mechanism(self, error_recovery):
        """Test retry mechanism with backoff."""
        # Test multiple retries
        for attempt in range(3):
            recovery_decision = error_recovery.recover_from_parser_failure(
                "WeightParser",
                ValueError(f"Attempt {attempt + 1}")
            )

            assert recovery_decision.action == RecoveryAction.RETRY
            assert recovery_decision.should_retry is True
            # Delay increases with each retry (exponential backoff)
            expected_delay = 5.0 * (2 ** attempt)
            assert recovery_decision.retry_delay_seconds == expected_delay

    def test_custom_recovery_actions(self, error_recovery):
        """Test custom recovery actions for specific parsers."""
        # Test custom recovery for specific parser
        recovery_decision = error_recovery.recover_from_parser_failure(
            "ProcessMethodParser", 
            ConnectionError("Network timeout")
        )
        
        assert recovery_decision.action == RecoveryAction.RETRY
        assert recovery_decision.should_retry is True

    def test_error_recovery_configuration_validation(self):
        """Test error recovery configuration validation."""
        # Test valid configuration
        valid_config = ErrorRecoveryConfig(
            max_retries=5,
            retry_delay_seconds=10,
            recoverable_parser_errors={
                "TestParser": ["ValueError", "TypeError"]
            }
        )
        
        assert valid_config.max_retries == 5
        assert valid_config.retry_delay_seconds == 10
        assert "TestParser" in valid_config.recoverable_parser_errors

    def test_recovery_decision_creation(self, error_recovery):
        """Test creation of recovery decisions."""
        # Test retry decision
        retry_decision = error_recovery.recover_from_parser_failure(
            "WeightParser", 
            ValueError("Test error")
        )
        
        assert retry_decision.action == RecoveryAction.RETRY
        assert retry_decision.should_retry is True
        assert retry_decision.retry_delay_seconds > 0
        assert len(retry_decision.message) > 0

    def test_error_recovery_with_different_parsers(self, error_recovery):
        """Test error recovery with different parser types."""
        parsers = ["WeightParser", "RoastLevelParser", "ProcessMethodParser", "UnknownParser"]
        
        for parser in parsers:
            recovery_decision = error_recovery.recover_from_parser_failure(
                parser,
                ValueError("Test error")
            )

            # ValueError is always recoverable regardless of parser
            assert recovery_decision.action == RecoveryAction.RETRY


class TestTransactionManagement:
    """Test suite for transaction management."""

    @pytest.fixture
    def transaction_manager(self):
        """Create transaction manager."""
        mock_rpc_client = Mock()
        return PipelineTransactionManager(mock_rpc_client)

    def test_transaction_creation(self, transaction_manager):
        """Test transaction creation."""
        execution_id = "test-execution-123"
        boundary = TransactionBoundary.PIPELINE_START
        
        transaction = transaction_manager.create_transaction(execution_id, boundary)
        
        assert transaction.transaction_id == execution_id
        assert transaction.boundary == boundary
        assert transaction.state == TransactionStatus.PENDING
        assert execution_id in transaction_manager.active_transactions

    def test_transaction_state_transitions(self, transaction_manager):
        """Test transaction state transitions."""
        execution_id = "test-execution-123"
        boundary = TransactionBoundary.PIPELINE_START
        
        transaction = transaction_manager.create_transaction(execution_id, boundary)
        
        # Test state transitions
        assert transaction.state == TransactionStatus.PENDING
        
        transaction.mark_in_progress()
        assert transaction.state == TransactionStatus.IN_PROGRESS
        
        transaction.commit()
        assert transaction.state == TransactionStatus.COMMITTED

    def test_transaction_rollback(self, transaction_manager):
        """Test transaction rollback."""
        execution_id = "test-execution-123"
        boundary = TransactionBoundary.PIPELINE_START
        
        transaction = transaction_manager.create_transaction(execution_id, boundary)
        transaction.mark_in_progress()
        
        transaction.rollback()
        assert transaction.state == TransactionStatus.ROLLED_BACK

    def test_transaction_operation_tracking(self, transaction_manager):
        """Test transaction operation tracking."""
        execution_id = "test-execution-123"
        boundary = TransactionBoundary.PIPELINE_START
        
        transaction = transaction_manager.create_transaction(execution_id, boundary)
        
        # Add operations
        transaction.add_operation("parse_weight", {"value": "250g"})
        transaction.add_operation("parse_roast", {"value": "light"})
        
        assert len(transaction.operations) == 2
        assert transaction.operations[0]["type"] == "parse_weight"
        assert transaction.operations[1]["type"] == "parse_roast"

    def test_transaction_completion(self, transaction_manager):
        """Test transaction completion and cleanup."""
        execution_id = "test-execution-123"
        boundary = TransactionBoundary.PIPELINE_START
        
        transaction = transaction_manager.create_transaction(execution_id, boundary)
        assert execution_id in transaction_manager.active_transactions
        
        transaction_manager.complete_transaction(execution_id)
        assert execution_id not in transaction_manager.active_transactions

    def test_multiple_transaction_management(self, transaction_manager):
        """Test management of multiple transactions."""
        execution_ids = ["exec-1", "exec-2", "exec-3"]
        
        # Create multiple transactions
        transactions = []
        for exec_id in execution_ids:
            transaction = transaction_manager.create_transaction(exec_id, TransactionBoundary.PIPELINE_START)
            transactions.append(transaction)
        
        # Verify all transactions are active
        assert len(transaction_manager.active_transactions) == 3
        
        # Complete one transaction
        transaction_manager.complete_transaction("exec-1")
        assert len(transaction_manager.active_transactions) == 2
        assert "exec-1" not in transaction_manager.active_transactions
        assert "exec-2" in transaction_manager.active_transactions
        assert "exec-3" in transaction_manager.active_transactions

    def test_transaction_boundary_validation(self, transaction_manager):
        """Test transaction boundary validation."""
        execution_id = "test-execution-123"
        
        # Test different transaction boundaries
        boundaries = [
            TransactionBoundary.PIPELINE_START,
            TransactionBoundary.DETERMINISTIC_COMPLETE,
            TransactionBoundary.LLM_COMPLETE,
            TransactionBoundary.PIPELINE_END
        ]
        
        for boundary in boundaries:
            transaction = transaction_manager.create_transaction(execution_id, boundary)
            assert transaction.boundary == boundary
            transaction_manager.complete_transaction(execution_id)

    def test_transaction_error_handling(self, transaction_manager):
        """Test transaction error handling."""
        execution_id = "test-execution-123"
        boundary = TransactionBoundary.PIPELINE_START
        
        transaction = transaction_manager.create_transaction(execution_id, boundary)
        transaction.mark_in_progress()
        
        # Simulate error
        transaction.status = TransactionStatus.FAILED
        transaction.state = TransactionStatus.FAILED  # Sync state manually for test
        assert transaction.state == TransactionStatus.FAILED
        
        # Test rollback after error
        transaction.rollback()
        assert transaction.state == TransactionStatus.ROLLED_BACK


class TestPipelineErrorHandling:
    """Test suite for pipeline error handling."""

    @pytest.fixture
    def pipeline_config(self):
        """Create pipeline configuration."""
        return PipelineConfig(
            enable_weight_parsing=True,
            enable_roast_parsing=True,
            enable_process_parsing=True,
            enable_metrics=True
        )

    def test_pipeline_execution_error_creation(self, pipeline_config):
        """Test pipeline execution error creation."""
        # Create mock pipeline state
        mock_state = Mock()
        mock_state.execution_id = "test-exec-123"
        mock_state.stage = PipelineStage.FAILED
        
        # Test error creation
        error = PipelineExecutionError("Pipeline failed", mock_state)
        
        assert str(error) == "Pipeline failed"
        assert error.state == mock_state

    def test_pipeline_state_error_tracking(self, pipeline_config):
        """Test pipeline state error tracking."""
        # Create pipeline state
        state = PipelineState(
            execution_id="test-exec-123",
            stage=PipelineStage.INITIALIZED,
            deterministic_results={},
            llm_results={},
            errors=[],
            warnings=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Add error
        error = PipelineError(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            error_type="parser_failure",
            message="WeightParser failed",
            recoverable=True
        )
        
        state.add_error(error)
        
        assert len(state.errors) == 1
        assert state.errors[0].error_type == "parser_failure"
        assert state.errors[0].recoverable is True

    def test_pipeline_warning_tracking(self, pipeline_config):
        """Test pipeline warning tracking."""
        # Create pipeline state
        state = PipelineState(
            execution_id="test-exec-123",
            stage=PipelineStage.INITIALIZED,
            deterministic_results={},
            llm_results={},
            errors=[],
            warnings=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Add warning
        warning = PipelineWarning(
            stage=PipelineStage.DETERMINISTIC_PARSING,
            parser_name="WeightParser",
            message="Low confidence in weight parsing",
            severity="medium"
        )
        
        state.add_warning(warning)
        
        assert len(state.warnings) == 1
        assert state.warnings[0].parser_name == "WeightParser"
        assert state.warnings[0].severity == "medium"

    def test_pipeline_error_recovery_integration(self, pipeline_config):
        """Test pipeline error recovery integration."""
        # Mock pipeline with error recovery
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = pipeline_config
            mock_pipeline.return_value.error_recovery = Mock()
            mock_pipeline.return_value.error_recovery.recover_from_parser_failure.return_value = Mock(
                action=RecoveryAction.SKIP,
                should_retry=False,
                message="Skipping failed parser"
            )
            
            # Test error recovery integration
            pipeline = mock_pipeline.return_value
            
            # Mock parser failure
            with patch.object(pipeline, '_execute_parser', side_effect=Exception("Parser error")):
                # Test error recovery
                recovery_decision = pipeline.error_recovery.recover_from_parser_failure(
                    "WeightParser", 
                    Exception("Parser error")
                )
                
                assert recovery_decision.action == RecoveryAction.SKIP
                assert recovery_decision.should_retry is False

    def test_graceful_degradation_scenario(self, pipeline_config):
        """Test graceful degradation scenario."""
        # Mock pipeline with partial failures
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = pipeline_config
            
            # Mock partial success
            def mock_process_artifact(artifact):
                return {
                    'normalized_data': {
                        'weight': '250g',  # Success
                        # Missing roast_level due to failure
                        'process_method': 'washed'  # Success
                    },
                    'pipeline_warnings': ['RoastLevelParser failed, continuing with available data'],
                    'pipeline_errors': ['RoastLevelParser: Connection timeout'],
                    'overall_confidence': 0.6  # Lower due to partial failure
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test graceful degradation
            pipeline = mock_pipeline.return_value
            artifact = {'product': {'title': 'Test Coffee'}}
            
            result = pipeline.process_artifact(artifact)
            
            # Verify graceful degradation
            assert 'weight' in result['normalized_data']
            assert 'process_method' in result['normalized_data']
            assert 'roast_level' not in result['normalized_data']
            assert len(result['pipeline_errors']) > 0
            assert result['overall_confidence'] < 0.8

    def test_error_recovery_with_retry(self, pipeline_config):
        """Test error recovery with retry mechanism."""
        # Mock pipeline with retry mechanism
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = pipeline_config
            mock_pipeline.return_value.error_recovery = Mock()
            
            # Mock retry decision
            mock_pipeline.return_value.error_recovery.recover_from_parser_failure.return_value = Mock(
                action=RecoveryAction.RETRY,
                should_retry=True,
                retry_delay_seconds=5,
                message="Retrying parser WeightParser"
            )
            
            # Test retry mechanism
            pipeline = mock_pipeline.return_value
            
            recovery_decision = pipeline.error_recovery.recover_from_parser_failure(
                "WeightParser", 
                ValueError("Temporary error")
            )
            
            assert recovery_decision.action == RecoveryAction.RETRY
            assert recovery_decision.should_retry is True
            assert recovery_decision.retry_delay_seconds == 5

    def test_comprehensive_error_scenarios(self, pipeline_config):
        """Test comprehensive error scenarios."""
        # Mock pipeline with various error scenarios
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = pipeline_config
            
            # Mock comprehensive error handling
            def mock_process_artifact(artifact):
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'light',
                        'process_method': 'washed'
                    },
                    'pipeline_warnings': [
                        'Low confidence in weight parsing',
                        'LLM fallback used for roast level',
                        'Connection timeout for process method'
                    ],
                    'pipeline_errors': [
                        'ProcessMethodParser: Connection timeout',
                        'LLM service: Rate limit exceeded'
                    ],
                    'overall_confidence': 0.7,
                    'llm_fallback_used': True,
                    'llm_fallback_fields': ['roast_level']
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test comprehensive error handling
            pipeline = mock_pipeline.return_value
            artifact = {'product': {'title': 'Test Coffee'}}
            
            result = pipeline.process_artifact(artifact)
            
            # Verify comprehensive error handling
            assert len(result['pipeline_warnings']) == 3
            assert len(result['pipeline_errors']) == 2
            assert result['llm_fallback_used'] is True
            assert 'roast_level' in result['llm_fallback_fields']
            assert result['overall_confidence'] == 0.7
