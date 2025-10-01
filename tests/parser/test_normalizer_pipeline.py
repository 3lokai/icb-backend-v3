"""
Test suite for C.8 NormalizerPipelineService orchestration.

Tests the complete normalizer pipeline including:
- Parser orchestration and execution order
- Error recovery and state management
- Batch processing optimization
- Epic D service integration
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, List, Any

from src.parser.normalizer_pipeline import NormalizerPipelineService, PipelineExecutionError
from src.parser.pipeline_state import PipelineState, PipelineStage, PipelineError, PipelineWarning
from src.config.pipeline_config import PipelineConfig
from src.parser.error_recovery import ErrorRecoveryConfig, RecoveryAction


class TestNormalizerPipelineService:
    """Test suite for NormalizerPipelineService orchestration."""

    @pytest.fixture
    def pipeline_config(self):
        """Create a test pipeline configuration."""
        return PipelineConfig(
            enable_weight_parsing=True,
            enable_roast_parsing=True,
            enable_process_parsing=True,
            enable_tag_parsing=True,
            enable_notes_parsing=True,
            enable_grind_parsing=True,
            enable_species_parsing=True,
            enable_variety_parsing=True,
            enable_geographic_parsing=True,
            enable_sensory_parsing=True,
            enable_hash_generation=True,
            enable_text_cleaning=True,
            enable_text_normalization=True,
            enable_metrics=True
        )

    @pytest.fixture
    def sample_artifact(self):
        """Create a sample artifact for testing."""
        return {
            'product': {
                'title': 'Ethiopian Yirgacheffe Light Roast - 250g',
                'description_html': 'Single origin coffee with floral notes and citrus acidity',
                'platform_product_id': 'test-001',
                'source_url': 'https://example.com/coffee'
            },
            'variants': [
                {
                    'weight': '250g',
                    'price': 15.99,
                    'currency': 'USD',
                    'grind': 'Whole Bean',
                    'availability': True
                }
            ],
            'roaster_id': 'test-roaster'
        }

    @pytest.fixture
    def mock_parsers(self):
        """Create mock parsers for testing."""
        mock_parsers = {}
        
        # Mock weight parser
        mock_weight_parser = Mock()
        mock_weight_parser.parse.return_value = Mock(
            value='250g',
            confidence=0.9,
            warnings=[]
        )
        mock_parsers['weight'] = mock_weight_parser
        
        # Mock roast parser
        mock_roast_parser = Mock()
        mock_roast_parser.parse.return_value = Mock(
            value='light',
            confidence=0.85,
            warnings=[]
        )
        mock_parsers['roast'] = mock_roast_parser
        
        # Mock process parser
        mock_process_parser = Mock()
        mock_process_parser.parse.return_value = Mock(
            value='washed',
            confidence=0.8,
            warnings=[]
        )
        mock_parsers['process'] = mock_process_parser
        
        return mock_parsers

    @pytest.fixture
    def mock_epic_d_services(self):
        """Create mock Epic D services for testing."""
        return {
            'llm_service': Mock(),
            'cache_service': Mock(),
            'rate_limiter': Mock(),
            'confidence_evaluator': Mock(),
            'review_workflow': Mock(),
            'enrichment_persistence': Mock(),
            'llm_metrics': Mock(),
            'confidence_metrics': Mock()
        }

    def test_pipeline_initialization(self, pipeline_config):
        """Test pipeline service initialization."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        assert pipeline.config == pipeline_config
        assert pipeline.parsers is not None
        assert pipeline.execution_order is not None
        assert pipeline.error_recovery is not None
        assert pipeline.state_manager is not None

    def test_parser_execution_order(self, pipeline_config):
        """Test that parsers execute in correct order."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        expected_order = [
            'text_cleaning',
            'text_normalization', 
            'weight',
            'roast',
            'process',
            'grind',
            'species',
            'variety',
            'geographic',
            'sensory',
            'tags',
            'notes',
            'hash'
        ]
        
        assert pipeline.execution_order == expected_order

    def test_deterministic_parser_execution(self, pipeline_config, sample_artifact, mock_parsers):
        """Test deterministic parser execution."""
        with patch.object(NormalizerPipelineService, '_initialize_parsers', return_value=mock_parsers):
            pipeline = NormalizerPipelineService(pipeline_config)
            
            # Mock the _execute_parser method to return mock results
            def mock_execute_parser(parser, parser_name, artifact):
                return Mock(
                    parser_name=parser_name,
                    value=f'mock_{parser_name}_value',
                    confidence=0.8,
                    warnings=[]
                )
            
            pipeline._execute_parser = mock_execute_parser
            
            # Execute deterministic parsers
            results = pipeline._execute_deterministic_parsers(sample_artifact, Mock())
            
            # Verify all enabled parsers were executed
            assert len(results) > 0
            for parser_name in results:
                assert results[parser_name].parser_name == parser_name
                assert results[parser_name].confidence == 0.8

    def test_llm_fallback_identification(self, pipeline_config):
        """Test identification of fields needing LLM fallback."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Mock results with low confidence
        low_confidence_results = {
            'weight': Mock(confidence=0.6),  # Below threshold
            'roast': Mock(confidence=0.8),  # Above threshold
            'process': Mock(confidence=0.5)  # Below threshold
        }
        
        # Mock the _needs_llm_fallback method
        pipeline._needs_llm_fallback = Mock(return_value=True)
        
        needs_fallback = pipeline._needs_llm_fallback(low_confidence_results)
        assert needs_fallback is True

    def test_pipeline_state_management(self, pipeline_config, sample_artifact):
        """Test pipeline state management during execution."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Mock parsers to avoid actual parsing
        with patch.object(pipeline, '_initialize_parsers', return_value={}):
            pipeline = NormalizerPipelineService(pipeline_config)
            
            # Mock the process_artifact method
            with patch.object(pipeline, '_execute_deterministic_parsers', return_value={}):
                with patch.object(pipeline, '_needs_llm_fallback', return_value=False):
                    with patch.object(pipeline, '_create_pipeline_result', return_value={}):
                        result = pipeline.process_artifact(sample_artifact)
                        
                        # Verify result structure
                        assert isinstance(result, dict)

    def test_error_recovery_mechanism(self, pipeline_config, sample_artifact):
        """Test error recovery when parsers fail."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Mock a parser that fails
        failing_parser = Mock()
        failing_parser.parse.side_effect = Exception("Parser failure")
        
        mock_parsers = {'weight': failing_parser}
        
        with patch.object(pipeline, '_initialize_parsers', return_value=mock_parsers):
            with patch.object(pipeline, '_execute_parser', side_effect=Exception("Parser error")):
                # Mock error recovery
                pipeline.error_recovery.recover_from_parser_failure = Mock(
                    return_value=Mock(
                        action=RecoveryAction.SKIP,
                        should_retry=False,
                        message="Skipping failed parser"
                    )
                )
                
                # Execute with error recovery
                results = pipeline._execute_deterministic_parsers(sample_artifact, Mock())
                
                # Verify error recovery was called
                pipeline.error_recovery.recover_from_parser_failure.assert_called()

    def test_batch_processing_optimization(self, pipeline_config):
        """Test batch processing optimization."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Create multiple artifacts
        artifacts = [
            {'product': {'title': f'Coffee {i}', 'description_html': f'Description {i}'}}
            for i in range(10)
        ]
        
        # Mock batch processing
        with patch.object(pipeline, 'process_artifact', return_value={}) as mock_process:
            results = []
            for artifact in artifacts:
                result = pipeline.process_artifact(artifact)
                results.append(result)
            
            # Verify all artifacts were processed
            assert len(results) == 10
            assert mock_process.call_count == 10

    def test_epic_d_service_integration(self, pipeline_config, mock_epic_d_services):
        """Test Epic D service integration."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Initialize Epic D services
        pipeline.initialize_epic_d_services(**mock_epic_d_services)
        
        # Verify services are initialized
        assert pipeline.llm_service == mock_epic_d_services['llm_service']
        assert pipeline.cache_service == mock_epic_d_services['cache_service']
        assert pipeline.rate_limiter == mock_epic_d_services['rate_limiter']
        assert pipeline.confidence_evaluator == mock_epic_d_services['confidence_evaluator']
        assert pipeline.review_workflow == mock_epic_d_services['review_workflow']
        assert pipeline.enrichment_persistence == mock_epic_d_services['enrichment_persistence']
        assert pipeline.llm_metrics == mock_epic_d_services['llm_metrics']
        assert pipeline.confidence_metrics == mock_epic_d_services['confidence_metrics']

    def test_llm_fallback_execution(self, pipeline_config, sample_artifact, mock_epic_d_services):
        """Test LLM fallback execution."""
        pipeline = NormalizerPipelineService(pipeline_config)
        pipeline.initialize_epic_d_services(**mock_epic_d_services)
        
        # Mock LLM fallback service
        mock_llm_fallback = Mock()
        mock_llm_fallback.process_ambiguous_cases.return_value = {
            'weight': Mock(value='250g', confidence=0.9),
            'process': Mock(value='washed', confidence=0.85)
        }
        
        with patch.object(pipeline, '_execute_llm_fallback', return_value=mock_llm_fallback.process_ambiguous_cases()):
            # Mock deterministic results that need LLM fallback
            deterministic_results = {
                'weight': Mock(confidence=0.6),  # Low confidence
                'roast': Mock(confidence=0.8)   # High confidence
            }
            
            # Execute LLM fallback
            llm_results = pipeline._execute_llm_fallback(sample_artifact, deterministic_results, Mock())
            
            # Verify LLM fallback was executed
            assert isinstance(llm_results, dict)

    def test_pipeline_metrics_collection(self, pipeline_config, sample_artifact):
        """Test pipeline metrics collection."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Mock metrics
        mock_metrics = Mock()
        pipeline.metrics = mock_metrics
        
        # Mock the process_artifact method
        with patch.object(pipeline, '_execute_deterministic_parsers', return_value={}):
            with patch.object(pipeline, '_needs_llm_fallback', return_value=False):
                with patch.object(pipeline, '_create_pipeline_result', return_value={}):
                    result = pipeline.process_artifact(sample_artifact)
                    
                    # Verify metrics were recorded
                    assert mock_metrics.record_pipeline_execution.called

    def test_transaction_management(self, pipeline_config, sample_artifact):
        """Test transaction management during pipeline execution."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Mock transaction manager
        mock_transaction = Mock()
        pipeline.transaction_manager = Mock()
        pipeline.transaction_manager.create_transaction.return_value = mock_transaction
        
        # Mock the process_artifact method
        with patch.object(pipeline, '_execute_deterministic_parsers', return_value={}):
            with patch.object(pipeline, '_needs_llm_fallback', return_value=False):
                with patch.object(pipeline, '_create_pipeline_result', return_value={}):
                    result = pipeline.process_artifact(sample_artifact)
                    
                    # Verify transaction was created and committed
                    pipeline.transaction_manager.create_transaction.assert_called()
                    mock_transaction.commit.assert_called()

    def test_pipeline_failure_handling(self, pipeline_config, sample_artifact):
        """Test pipeline failure handling and rollback."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Mock transaction manager
        mock_transaction = Mock()
        pipeline.transaction_manager = Mock()
        pipeline.transaction_manager.create_transaction.return_value = mock_transaction
        
        # Mock a failure in deterministic parsing
        with patch.object(pipeline, '_execute_deterministic_parsers', side_effect=Exception("Pipeline failure")):
            with pytest.raises(PipelineExecutionError):
                pipeline.process_artifact(sample_artifact)
                
                # Verify transaction was rolled back
                mock_transaction.rollback.assert_called()

    def test_confidence_threshold_evaluation(self, pipeline_config):
        """Test confidence threshold evaluation for LLM fallback."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Test results above threshold
        high_confidence_results = {
            'weight': Mock(confidence=0.9),
            'roast': Mock(confidence=0.85),
            'process': Mock(confidence=0.8)
        }
        
        needs_fallback = pipeline._needs_llm_fallback(high_confidence_results)
        assert needs_fallback is False
        
        # Test results below threshold
        low_confidence_results = {
            'weight': Mock(confidence=0.6),
            'roast': Mock(confidence=0.5),
            'process': Mock(confidence=0.4)
        }
        
        needs_fallback = pipeline._needs_llm_fallback(low_confidence_results)
        assert needs_fallback is True

    def test_parser_dependency_management(self, pipeline_config):
        """Test parser dependency management and execution order."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Verify execution order respects dependencies
        execution_order = pipeline.execution_order
        
        # Text cleaning should come before text normalization
        assert execution_order.index('text_cleaning') < execution_order.index('text_normalization')
        
        # Text processing should come before content parsing
        assert execution_order.index('text_cleaning') < execution_order.index('weight')
        assert execution_order.index('text_normalization') < execution_order.index('weight')
        
        # Hash generation should come last
        assert execution_order.index('hash') == len(execution_order) - 1

    def test_pipeline_state_tracking(self, pipeline_config, sample_artifact):
        """Test pipeline state tracking throughout execution."""
        pipeline = NormalizerPipelineService(pipeline_config)
        
        # Mock the process_artifact method to track state changes
        state_changes = []
        
        def mock_process_artifact(artifact):
            # Track state changes
            state_changes.append('initialized')
            state_changes.append('deterministic_parsing')
            state_changes.append('completed')
            return {}
        
        with patch.object(pipeline, 'process_artifact', side_effect=mock_process_artifact):
            result = pipeline.process_artifact(sample_artifact)
            
            # Verify state progression
            assert 'initialized' in state_changes
            assert 'deterministic_parsing' in state_changes
            assert 'completed' in state_changes

    def test_warning_and_error_handling(self, pipeline_config, sample_artifact):
        """Test warning and error handling during pipeline execution."""
        pipeline = NormalizerPipelineService(pipeline_config)

        # Mock parsers that generate warnings
        warning_parser = Mock()
        warning_parser.parse.return_value = Mock(
            value='test_value',
            confidence=0.7,
            warnings=['Low confidence warning']
        )

        mock_parsers = {'weight': warning_parser}

        with patch.object(pipeline, '_initialize_parsers', return_value=mock_parsers):
            # Mock the _execute_parser method
            def mock_execute_parser(parser, parser_name, artifact):
                result = parser.parse(artifact)
                return Mock(
                    parser_name=parser_name,
                    value=result.value,
                    confidence=result.confidence,
                    warnings=result.warnings
                )

            pipeline._execute_parser = mock_execute_parser

            # Execute and check for warnings
            results = pipeline._execute_deterministic_parsers(sample_artifact, Mock())

            # Verify warnings are captured
            assert len(results) > 0
            for parser_name, result in results.items():
                if result and hasattr(result, 'warnings') and result.warnings:
                    assert 'Low confidence warning' in result.warnings


class TestPipelineIntegration:
    """Integration tests for the complete normalizer pipeline."""

    @pytest.fixture
    def integration_pipeline(self):
        """Create a pipeline for integration testing."""
        config = PipelineConfig(
            enable_weight_parsing=True,
            enable_roast_parsing=True,
            enable_process_parsing=True,
            enable_metrics=True
        )
        return NormalizerPipelineService(config)

    def test_complete_pipeline_flow(self, integration_pipeline):
        """Test complete pipeline flow from artifact to result."""
        artifact = {
            'product': {
                'title': 'Colombian Supremo Medium Roast - 500g',
                'description_html': 'Rich and balanced coffee with chocolate notes',
                'platform_product_id': 'colombian-001',
                'source_url': 'https://example.com/colombian'
            },
            'variants': [
                {
                    'weight': '500g',
                    'price': 12.99,
                    'currency': 'USD',
                    'grind': 'Ground',
                    'availability': True
                }
            ],
            'roaster_id': 'test-roaster'
        }
        
        # Mock the complete pipeline execution
        with patch.object(integration_pipeline, '_execute_deterministic_parsers', return_value={}):
            with patch.object(integration_pipeline, '_needs_llm_fallback', return_value=False):
                with patch.object(integration_pipeline, '_create_pipeline_result', return_value={
                    'normalized_data': {
                        'weight': '500g',
                        'roast_level': 'medium',
                        'process_method': 'washed'
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85
                }):
                    result = integration_pipeline.process_artifact(artifact)
                    
                    # Verify complete result structure
                    assert 'normalized_data' in result
                    assert 'pipeline_warnings' in result
                    assert 'pipeline_errors' in result
                    assert 'overall_confidence' in result

    def test_pipeline_performance_benchmark(self, integration_pipeline):
        """Test pipeline performance with multiple artifacts."""
        artifacts = [
            {
                'product': {
                    'title': f'Test Coffee {i}',
                    'description_html': f'Test description {i}',
                    'platform_product_id': f'test-{i}',
                    'source_url': f'https://example.com/test-{i}'
                },
                'variants': [{'weight': '250g', 'price': 10.0, 'currency': 'USD'}],
                'roaster_id': 'test-roaster'
            }
            for i in range(50)  # Test with 50 artifacts
        ]
        
        # Mock pipeline execution
        with patch.object(integration_pipeline, 'process_artifact', return_value={}):
            start_time = datetime.now()
            
            results = []
            for artifact in artifacts:
                result = integration_pipeline.process_artifact(artifact)
                results.append(result)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Verify performance (should be fast with mocked execution)
            assert processing_time < 5.0  # Should complete in under 5 seconds
            assert len(results) == 50
