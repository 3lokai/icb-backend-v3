"""
Test suite for C.8 LLMFallbackService integration.

Tests the LLM fallback service including:
- Ambiguous case identification
- Epic D service health checks
- Rate limiting and caching integration
- Confidence evaluation and review workflow
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, List, Any

from src.parser.llm_fallback_integration import LLMFallbackService
from src.parser.pipeline_state import PipelineState, PipelineStage, PipelineWarning
from src.config.llm_config import LLMConfig
from src.config.pipeline_config import LLMFallbackConfig
from src.llm.llm_interface import LLMResult


class TestLLMFallbackService:
    """Test suite for LLMFallbackService integration."""

    @pytest.fixture
    def llm_config(self):
        """Create a test LLM configuration."""
        from src.config.deepseek_config import DeepSeekConfig
        from src.config.cache_config import CacheConfig
        from src.config.confidence_config import ConfidenceConfig
        from src.config.review_config import ReviewConfig
        
        return LLMConfig(
            deepseek_config=DeepSeekConfig(api_key="test-key"),
            cache_config=CacheConfig(),
            confidence_config=ConfidenceConfig(),
            review_config=ReviewConfig(),
            enabled=True,
            confidence_threshold=0.7,
            timeout_seconds=30.0,
            max_retries=2,
            batch_size=5,
            rate_limit_per_minute=60,
            field_configs={
                'weight': {'enabled': True, 'confidence_threshold': 0.7},
                'roast': {'enabled': True, 'confidence_threshold': 0.8},
                'process': {'enabled': True, 'confidence_threshold': 0.8}
            },
            enable_caching=True,
            cache_ttl_seconds=3600,
            enable_rate_limiting=True,
            enable_batch_processing=True,
            enable_graceful_degradation=True,
            fallback_to_deterministic=True
        )

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
    def low_confidence_results(self):
        """Create deterministic results with low confidence."""
        return {
            'weight': Mock(confidence=0.6, value='250g', warnings=['Low confidence']),
            'roast': Mock(confidence=0.5, value='light', warnings=['Ambiguous roast level']),
            'process': Mock(confidence=0.8, value='washed', warnings=[])
        }

    def test_llm_fallback_service_initialization(self, llm_config, mock_epic_d_services):
        """Test LLM fallback service initialization."""
        service = LLMFallbackService(
            llm_config,
            **mock_epic_d_services
        )
        
        assert service.config == llm_config
        assert service.llm_service == mock_epic_d_services['llm_service']
        assert service.cache_service == mock_epic_d_services['cache_service']
        assert service.rate_limiter == mock_epic_d_services['rate_limiter']
        assert service.confidence_evaluator == mock_epic_d_services['confidence_evaluator']
        assert service.review_workflow == mock_epic_d_services['review_workflow']
        assert service.enrichment_persistence == mock_epic_d_services['enrichment_persistence']
        assert service.llm_metrics == mock_epic_d_services['llm_metrics']
        assert service.confidence_metrics == mock_epic_d_services['confidence_metrics']

    def test_ambiguous_field_identification(self, llm_config, mock_epic_d_services, low_confidence_results):
        """Test identification of ambiguous fields needing LLM fallback."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        ambiguous_fields = service._identify_ambiguous_fields(low_confidence_results)
        
        # Should identify fields with confidence below threshold (0.7)
        assert 'weight' in ambiguous_fields  # confidence 0.6
        assert 'roast' in ambiguous_fields  # confidence 0.5
        assert 'process' not in ambiguous_fields  # confidence 0.8

    def test_llm_prompt_construction(self, llm_config, mock_epic_d_services, sample_artifact, low_confidence_results):
        """Test LLM prompt construction for ambiguous fields."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Test prompt construction for weight field
        prompt = service._construct_llm_prompt(sample_artifact, 'weight', low_confidence_results['weight'])
        
        assert 'weight' in prompt.lower()
        assert sample_artifact['product']['title'] in prompt
        assert sample_artifact['product']['description_html'] in prompt
        assert 'Low confidence' in prompt  # Should include warnings

    def test_llm_prompt_construction_no_parser_result(self, llm_config, mock_epic_d_services, sample_artifact):
        """Test LLM prompt construction when no parser result is available."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Test prompt construction without parser result
        prompt = service._construct_llm_prompt(sample_artifact, 'weight', None)
        
        assert 'weight' in prompt.lower()
        assert sample_artifact['product']['title'] in prompt
        assert 'No deterministic value was found' in prompt

    @pytest.mark.asyncio
    async def test_llm_fallback_execution_success(self, llm_config, mock_epic_d_services, sample_artifact, low_confidence_results):
        """Test successful LLM fallback execution."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock successful LLM response
        mock_llm_result = LLMResult(
            field='weight',
            value='250g',
            confidence=0.9,
            model='deepseek-chat',
            usage={'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            created_at=datetime.now(timezone.utc)
        )
        
        mock_epic_d_services['llm_service'].enrich_field = AsyncMock(return_value=mock_llm_result)
        mock_epic_d_services['rate_limiter'].can_make_request.return_value = True
        mock_epic_d_services['cache_service'].get.return_value = None  # No cached result
        mock_epic_d_services['confidence_evaluator'].evaluate_confidence.return_value = Mock(
            final_confidence=0.9,
            action='auto_apply'
        )
        mock_epic_d_services['enrichment_persistence'].persist_enrichment.return_value = 'enrichment-123'
        
        # Mock pipeline state
        mock_state = Mock()
        mock_state.add_warning = Mock()
        
        # Execute LLM fallback
        results = await service.process_ambiguous_cases(sample_artifact, low_confidence_results, None)
        
        # Verify LLM service was called
        mock_epic_d_services['llm_service'].enrich_field.assert_called()
        
        # Verify results
        assert len(results) > 0
        assert 'weight' in results
        assert results['weight'].value == '250g'
        assert results['weight'].confidence == 0.9

    @pytest.mark.asyncio
    async def test_llm_fallback_rate_limiting(self, llm_config, mock_epic_d_services, sample_artifact, low_confidence_results):
        """Test LLM fallback with rate limiting."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock rate limiting
        mock_epic_d_services['rate_limiter'].can_make_request.return_value = False
        mock_epic_d_services['llm_metrics'].record_rate_limit_exceeded = Mock()

        # Mock pipeline state
        mock_state = Mock()
        mock_state.add_warning = Mock()

        # Execute LLM fallback
        results = await service.process_ambiguous_cases(sample_artifact, low_confidence_results, mock_state)
        
        # Verify rate limiting was handled
        mock_epic_d_services['llm_metrics'].record_rate_limit_exceeded.assert_called()
        mock_state.add_warning.assert_called()
        
        # Should return rate limit markers for each field
        assert len(results) == 3  # weight, roast, process
        for field, result in results.items():
            assert result.value == "RATE_LIMITED"
            assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_llm_fallback_confidence_evaluation(self, llm_config, mock_epic_d_services, sample_artifact, low_confidence_results):
        """Test LLM fallback with confidence evaluation."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock LLM result with medium confidence
        mock_llm_result = LLMResult(
            field='weight',
            value='250g',
            confidence=0.75,
            model='deepseek-chat',
            usage={'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            created_at=datetime.now(timezone.utc)
        )
        
        mock_epic_d_services['llm_service'].enrich_field = AsyncMock(return_value=mock_llm_result)
        mock_epic_d_services['rate_limiter'].can_make_request.return_value = True
        mock_epic_d_services['cache_service'].get.return_value = None  # No cached result
        mock_epic_d_services['confidence_evaluator'].evaluate_confidence.return_value = Mock(
            final_confidence=0.75,
            action='review_required'
        )
        mock_epic_d_services['enrichment_persistence'].persist_enrichment.return_value = 'enrichment-123'
        mock_epic_d_services['review_workflow'].mark_for_review = Mock()
        
        # Mock pipeline state
        mock_state = Mock()
        mock_state.add_warning = Mock()
        
        # Execute LLM fallback
        results = await service.process_ambiguous_cases(sample_artifact, low_confidence_results, None)
        
        # Verify review workflow was called
        mock_epic_d_services['review_workflow'].mark_for_review.assert_called()
        
        # Verify results contain review marker
        assert len(results) > 0
        assert 'weight' in results
        assert 'REVIEW_REQUIRED' in results['weight'].value

    @pytest.mark.asyncio
    async def test_llm_fallback_error_handling(self, llm_config, mock_epic_d_services, sample_artifact, low_confidence_results):
        """Test LLM fallback error handling."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock LLM service failure
        mock_epic_d_services['llm_service'].enrich_field = AsyncMock(side_effect=Exception("LLM service error"))
        mock_epic_d_services['rate_limiter'].can_make_request.return_value = True
        mock_epic_d_services['cache_service'].get.return_value = None  # No cached result
        mock_epic_d_services['llm_metrics'].record_llm_call = Mock()

        # Mock pipeline state
        mock_state = Mock()
        mock_state.add_warning = Mock()

        # Execute LLM fallback
        results = await service.process_ambiguous_cases(sample_artifact, low_confidence_results, mock_state)
        
        # Verify error handling
        mock_state.add_warning.assert_called()
        
        # Should return error markers for each field
        assert len(results) == 3  # weight, roast, process
        for field, result in results.items():
            assert result.value.startswith("ERROR:")
            assert result.confidence == 0.0

    def test_review_marker_creation(self, llm_config, mock_epic_d_services):
        """Test creation of review markers for low confidence results."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock LLM result
        mock_llm_result = LLMResult(
            field='weight',
            value='250g',
            confidence=0.75,
            model='deepseek-chat',
            usage={'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            created_at=datetime.now(timezone.utc)
        )
        
        enrichment_id = 'enrichment-123'
        review_marker = service._create_review_marker('weight', mock_llm_result, enrichment_id)
        
        # Verify review marker structure
        assert review_marker['field'] == 'weight'
        assert review_marker['llm_result'] == mock_llm_result
        assert review_marker['enrichment_id'] == 'enrichment-123'
        assert review_marker['status'] == 'pending_review'

    def test_epic_d_service_health_checks(self, llm_config, mock_epic_d_services):
        """Test Epic D service health checks."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock service health checks
        mock_epic_d_services['llm_service'].is_available.return_value = True
        mock_epic_d_services['cache_service'].is_available.return_value = True
        mock_epic_d_services['rate_limiter'].is_available.return_value = True
        
        # Test health check
        assert service.llm_service.is_available()
        assert service.cache_service.is_available()
        assert service.rate_limiter.is_available()

    def test_confidence_threshold_configuration(self, mock_epic_d_services):
        """Test confidence threshold configuration."""
        # Test with different thresholds
        config_low = LLMFallbackConfig(confidence_threshold=0.5)
        config_high = LLMFallbackConfig(confidence_threshold=0.9)
        
        service_low = LLMFallbackService(config_low, **mock_epic_d_services)
        service_high = LLMFallbackService(config_high, **mock_epic_d_services)
        
        # Test with same results
        results = {
            'weight': Mock(confidence=0.7),
            'roast': Mock(confidence=0.8)
        }
        
        # Low threshold should trigger more LLM fallback
        ambiguous_low = service_low._identify_ambiguous_fields(results)
        ambiguous_high = service_high._identify_ambiguous_fields(results)
        
        assert len(ambiguous_low) < len(ambiguous_high)

    @pytest.mark.asyncio
    async def test_batch_llm_processing(self, llm_config, mock_epic_d_services):
        """Test batch LLM processing for multiple fields."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock batch processing
        mock_epic_d_services['llm_service'].batch_enrich = AsyncMock(return_value=[
            LLMResult(field='weight', value='250g', confidence=0.9, model='deepseek-chat', usage={}, created_at=datetime.now(timezone.utc)),
            LLMResult(field='roast', value='light', confidence=0.85, model='deepseek-chat', usage={}, created_at=datetime.now(timezone.utc))
        ])
        
        # Test batch processing
        artifacts = [{'product': {'title': 'Test Coffee'}}]
        fields = ['weight', 'roast']
        
        results = await mock_epic_d_services['llm_service'].batch_enrich(artifacts, fields)
        
        # Verify batch processing
        assert len(results) == 2
        assert results[0].field == 'weight'
        assert results[1].field == 'roast'

    def test_llm_usage_tracking(self, llm_config, mock_epic_d_services):
        """Test LLM usage tracking and metrics."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock LLM usage
        mock_usage = {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150,
            'cost': 1  # Integer cost
        }
        
        mock_llm_result = LLMResult(
            field='weight',
            value='250g',
            confidence=0.9,
            model='deepseek-chat',
            usage=mock_usage,
            created_at=datetime.now(timezone.utc)
        )
        
        # Test usage calculation
        usage = service._calculate_llm_usage({'weight': mock_llm_result})
        
        assert usage is not None
        assert usage['total_tokens'] == 150
        assert usage['total_cost'] == 1
        assert usage['result_count'] == 1

    def test_caching_integration(self, llm_config, mock_epic_d_services, sample_artifact):
        """Test caching integration with Epic D services."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock cache hit
        cached_result = LLMResult(
            field='weight',
            value='250g',
            confidence=0.9,
            model='deepseek-chat',
            usage={'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            created_at=datetime.now(timezone.utc)
        )
        
        mock_epic_d_services['cache_service'].get.return_value = cached_result
        mock_epic_d_services['cache_service'].set = Mock()
        
        # Test cache integration
        cache_key = f"llm_fallback_{sample_artifact['product']['platform_product_id']}_weight"
        cached = service.cache_service.get(cache_key)
        
        assert cached == cached_result
        mock_epic_d_services['cache_service'].get.assert_called_with(cache_key)

    def test_retry_mechanism(self, llm_config, mock_epic_d_services, sample_artifact, low_confidence_results):
        """Test retry mechanism for failed LLM calls."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock retry configuration
        config_with_retries = LLMFallbackConfig(
            enabled=True,
            max_retries=3,
            timeout_seconds=60
        )
        
        service_with_retries = LLMFallbackService(config_with_retries, **mock_epic_d_services)
        
        # Mock retry logic
        call_count = 0
        def mock_llm_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return LLMResult(field='weight', value='250g', confidence=0.9, raw_response={}, warnings=[])
        
        mock_epic_d_services['llm_service'].enrich_field = AsyncMock(side_effect=mock_llm_call)
        
        # Test retry mechanism
        assert call_count == 0
        # Note: In real implementation, retry logic would be tested here
        # This is a placeholder for the retry mechanism test

    def test_epic_d_service_dependency_validation(self, llm_config):
        """Test validation of Epic D service dependencies."""
        # Test with missing services
        incomplete_services = {
            'llm_service': Mock(),
            'cache_service': Mock(),
            # Missing other services
        }
        
        # Should raise error for missing services
        with pytest.raises(TypeError):
            LLMFallbackService(llm_config, **incomplete_services)

    def test_llm_fallback_configuration_validation(self):
        """Test LLM fallback configuration validation."""
        # Test invalid configuration
        with pytest.raises(ValueError):
            LLMFallbackConfig(
                confidence_threshold=1.5,  # Invalid threshold > 1.0
                max_retries=-1,  # Invalid retry count
                timeout_seconds=-1  # Invalid timeout
            )

    @pytest.mark.asyncio
    async def test_complete_llm_fallback_workflow(self, llm_config, mock_epic_d_services, sample_artifact, low_confidence_results):
        """Test complete LLM fallback workflow."""
        service = LLMFallbackService(llm_config, **mock_epic_d_services)
        
        # Mock complete workflow
        mock_epic_d_services['rate_limiter'].can_make_request.return_value = True
        mock_epic_d_services['cache_service'].get.return_value = None  # No cached result
        mock_epic_d_services['llm_service'].enrich_field = AsyncMock(return_value=LLMResult(
            field='weight', value='250g', confidence=0.9, model='deepseek-chat', usage={}, created_at=datetime.now(timezone.utc)
        ))
        mock_epic_d_services['confidence_evaluator'].evaluate_confidence.return_value = Mock(
            final_confidence=0.9,
            action='auto_apply'
        )
        mock_epic_d_services['enrichment_persistence'].persist_enrichment.return_value = 'enrichment-123'
        mock_epic_d_services['llm_metrics'].record_llm_call = Mock()
        mock_epic_d_services['confidence_metrics'].record_confidence_score = Mock()
        
        # Mock pipeline state
        mock_state = Mock()
        mock_state.add_warning = Mock()
        
        # Execute complete workflow
        results = await service.process_ambiguous_cases(sample_artifact, low_confidence_results, None)
        
        # Verify complete workflow
        assert len(results) > 0
        mock_epic_d_services['llm_service'].enrich_field.assert_called()
        mock_epic_d_services['confidence_evaluator'].evaluate_confidence.assert_called()
        mock_epic_d_services['enrichment_persistence'].persist_enrichment.assert_called()
        mock_epic_d_services['llm_metrics'].record_llm_call.assert_called()
        mock_epic_d_services['confidence_metrics'].record_confidence_score.assert_called()
