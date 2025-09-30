"""Unit tests for confidence evaluator service."""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.config.confidence_config import ConfidenceConfig, ConfidenceConfigBuilder
from src.llm.confidence_evaluator import ConfidenceEvaluator, ConfidenceEvaluation
from src.llm.llm_interface import LLMResult


class TestConfidenceEvaluator:
    """Test cases for confidence evaluator service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ConfidenceConfigBuilder.default()
        self.evaluator = ConfidenceEvaluator(self.config)
    
    def test_confidence_evaluation_auto_apply(self):
        """Test confidence evaluation with auto-apply result."""
        # Create LLM result with high confidence
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.85,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        # Evaluate confidence
        evaluation = self.evaluator.evaluate_confidence(llm_result)
        
        # Assertions
        assert evaluation.confidence_score == 0.85
        assert evaluation.final_confidence >= 0.85  # May be adjusted by rules
        assert evaluation.action == 'auto_apply'
        assert evaluation.status == 'approved'
        assert evaluation.threshold == 0.7
        assert evaluation.error_message is None
    
    def test_confidence_evaluation_manual_review(self):
        """Test confidence evaluation with manual review result."""
        # Create LLM result with low confidence
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.6,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        # Evaluate confidence
        evaluation = self.evaluator.evaluate_confidence(llm_result)
        
        # Assertions
        assert evaluation.confidence_score == 0.6
        assert evaluation.final_confidence < 0.7
        assert evaluation.action == 'manual_review'
        assert evaluation.status == 'review'
        assert evaluation.threshold == 0.7
        assert evaluation.error_message is None
    
    def test_field_specific_threshold(self):
        """Test field-specific confidence thresholds."""
        # Create config with field-specific thresholds
        config = ConfidenceConfig(
            confidence_threshold=0.7,
            field_thresholds={
                "roast_level": 0.9,
                "bean_species": 0.8
            }
        )
        evaluator = ConfidenceEvaluator(config)
        
        # Test roast_level with high threshold - use lower confidence to account for rule boost
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.8,  # Will be boosted to ~0.88 by rules, still below 0.9 threshold
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = evaluator.evaluate_confidence(llm_result)
        assert evaluation.threshold == 0.9
        assert evaluation.action == 'manual_review'
        
        # Test bean_species with medium threshold - use higher confidence
        llm_result.field = "bean_species"
        llm_result.confidence = 0.8  # Will be boosted to ~0.84 by rules, above 0.8 threshold
        
        evaluation = evaluator.evaluate_confidence(llm_result)
        assert evaluation.threshold == 0.8
        assert evaluation.action == 'auto_apply'
    
    def test_evaluation_rules_application(self):
        """Test that evaluation rules are applied correctly."""
        # Create LLM result for roast_level (should get rule boost)
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.8,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = self.evaluator.evaluate_confidence(llm_result)
        
        # Should have rules applied
        assert len(evaluation.evaluation_rules_applied) > 0
        assert "roast_level_high_confidence" in evaluation.evaluation_rules_applied
        assert evaluation.final_confidence > evaluation.original_confidence
    
    def test_batch_evaluation(self):
        """Test batch confidence evaluation."""
        # Create multiple LLM results
        llm_results = [
            LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.85,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            ),
            LLMResult(
                field="bean_species",
                value="arabica",
                confidence=0.6,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Evaluate batch
        evaluations = self.evaluator.batch_evaluate(llm_results)
        
        # Assertions
        assert len(evaluations) == 2
        assert evaluations[0].action == 'auto_apply'
        assert evaluations[1].action == 'manual_review'
    
    def test_confidence_stats(self):
        """Test confidence statistics calculation."""
        # Create test evaluations
        evaluations = [
            ConfidenceEvaluation(
                confidence_score=0.8,
                original_confidence=0.8,
                final_confidence=0.8,
                threshold=0.7,
                action='auto_apply',
                status='approved',
                evaluation_rules_applied=[],
                evaluation_time=0.01
            ),
            ConfidenceEvaluation(
                confidence_score=0.6,
                original_confidence=0.6,
                final_confidence=0.6,
                threshold=0.7,
                action='manual_review',
                status='review',
                evaluation_rules_applied=[],
                evaluation_time=0.01
            )
        ]
        
        # Get stats
        stats = self.evaluator.get_confidence_stats(evaluations)
        
        # Assertions
        assert stats['total_evaluations'] == 2
        assert stats['auto_apply_count'] == 1
        assert stats['review_count'] == 1
        assert stats['auto_apply_rate'] == 0.5
        assert stats['review_rate'] == 0.5
        assert stats['average_confidence'] == 0.7
    
    def test_error_handling(self):
        """Test error handling in confidence evaluation."""
        # Create invalid LLM result
        llm_result = Mock()
        llm_result.confidence = "invalid"  # Should cause error
        llm_result.field = "roast_level"
        
        # Evaluate confidence (should handle error gracefully)
        evaluation = self.evaluator.evaluate_confidence(llm_result)
        
        # Assertions
        assert evaluation.status == 'error'
        assert evaluation.action == 'manual_review'
        assert evaluation.error_message is not None
    
    def test_performance_requirements(self):
        """Test that confidence evaluation meets performance requirements."""
        # Create LLM result
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.8,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        # Measure evaluation time
        start_time = time.time()
        evaluation = self.evaluator.evaluate_confidence(llm_result)
        end_time = time.time()
        
        # Assertions
        assert evaluation.evaluation_time < 0.1  # < 100ms requirement
        assert (end_time - start_time) < 0.1
    
    def test_strict_configuration(self):
        """Test strict confidence configuration."""
        config = ConfidenceConfigBuilder.strict()
        evaluator = ConfidenceEvaluator(config)
        
        # Test with confidence that would pass default but fail strict
        # Use lower confidence to account for rule boost (0.75 * 1.1 = 0.825, still below 0.9 field threshold)
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.7,  # Will be boosted to ~0.77, below 0.9 field threshold
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = evaluator.evaluate_confidence(llm_result)
        assert evaluation.threshold == 0.9  # Field-specific threshold for roast_level
        assert evaluation.action == 'manual_review'
    
    def test_permissive_configuration(self):
        """Test permissive confidence configuration."""
        config = ConfidenceConfigBuilder.permissive()
        evaluator = ConfidenceEvaluator(config)
        
        # Test with confidence that would fail default but pass permissive
        # Use higher confidence to account for rule boost (0.65 * 1.1 = 0.715, above 0.7 field threshold)
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.65,  # Will be boosted to ~0.715, above 0.7 field threshold
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = evaluator.evaluate_confidence(llm_result)
        assert evaluation.threshold == 0.7  # Field-specific threshold for roast_level
        assert evaluation.action == 'auto_apply'


class TestConfidenceConfig:
    """Test cases for confidence configuration."""
    
    def test_default_configuration(self):
        """Test default configuration creation."""
        config = ConfidenceConfigBuilder.default()
        
        assert config.confidence_threshold == 0.7
        assert config.batch_size == 100
        assert config.evaluation_timeout == 0.1
        assert config.max_retries == 3
    
    def test_strict_configuration(self):
        """Test strict configuration creation."""
        config = ConfidenceConfigBuilder.strict()
        
        assert config.confidence_threshold == 0.8
        assert config.field_thresholds["roast_level"] == 0.9
        assert config.field_thresholds["bean_species"] == 0.9
    
    def test_permissive_configuration(self):
        """Test permissive configuration creation."""
        config = ConfidenceConfigBuilder.permissive()
        
        assert config.confidence_threshold == 0.6
        assert config.field_thresholds["roast_level"] == 0.7
        assert config.field_thresholds["bean_species"] == 0.7
    
    def test_custom_configuration(self):
        """Test custom configuration creation."""
        config = ConfidenceConfigBuilder.custom(
            threshold=0.75,
            field_thresholds={"roast_level": 0.85}
        )
        
        assert config.confidence_threshold == 0.75
        assert config.field_thresholds["roast_level"] == 0.85


if __name__ == "__main__":
    pytest.main([__file__])
