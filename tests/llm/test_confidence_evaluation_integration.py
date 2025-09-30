"""Integration tests for confidence evaluation service."""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.config.confidence_config import ConfidenceConfig, ConfidenceConfigBuilder
from src.llm.confidence_evaluator import ConfidenceEvaluator, ConfidenceEvaluation
from src.llm.llm_interface import LLMResult


class TestConfidenceEvaluationIntegration:
    """Integration tests for confidence evaluation service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ConfidenceConfigBuilder.default()
        self.evaluator = ConfidenceEvaluator(self.config)
    
    def test_complete_confidence_evaluation_workflow(self):
        """Test complete confidence evaluation workflow."""
        # Create test LLM results with different confidence levels
        llm_results = [
            LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.85,  # High confidence - should auto-apply
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            ),
            LLMResult(
                field="bean_species",
                value="arabica",
                confidence=0.6,  # Low confidence - should require review
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            ),
            LLMResult(
                field="process_method",
                value="washed",
                confidence=0.75,  # Medium confidence - should auto-apply
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Evaluate all results
        evaluations = self.evaluator.batch_evaluate(llm_results)
        
        # Assertions
        assert len(evaluations) == 3
        
        # First result should auto-apply
        assert evaluations[0].action == 'auto_apply'
        assert evaluations[0].status == 'approved'
        
        # Second result should require review
        assert evaluations[1].action == 'manual_review'
        assert evaluations[1].status == 'review'
        
        # Third result should auto-apply
        assert evaluations[2].action == 'auto_apply'
        assert evaluations[2].status == 'approved'
    
    def test_confidence_evaluation_with_field_specific_thresholds(self):
        """Test confidence evaluation with field-specific thresholds."""
        # Create config with field-specific thresholds
        config = ConfidenceConfig(
            confidence_threshold=0.7,
            field_thresholds={
                "roast_level": 0.9,  # Very high threshold
                "bean_species": 0.8,  # High threshold
                "process_method": 0.6  # Low threshold
            }
        )
        evaluator = ConfidenceEvaluator(config)
        
        # Create test results - use lower confidence to account for rule boost
        llm_results = [
            LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.8,  # Will be boosted to ~0.88, still below 0.9 threshold
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            ),
            LLMResult(
                field="bean_species",
                value="arabica",
                confidence=0.7,  # Will be boosted to ~0.735, still below 0.8 threshold
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            ),
            LLMResult(
                field="process_method",
                value="washed",
                confidence=0.65,  # Above field threshold (no rules for this field)
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Evaluate all results
        evaluations = evaluator.batch_evaluate(llm_results)
        
        # Assertions
        assert evaluations[0].threshold == 0.9
        assert evaluations[0].action == 'manual_review'
        
        assert evaluations[1].threshold == 0.8
        assert evaluations[1].action == 'manual_review'
        
        assert evaluations[2].threshold == 0.6
        assert evaluations[2].action == 'auto_apply'
    
    def test_confidence_evaluation_performance(self):
        """Test confidence evaluation performance requirements."""
        # Create test result
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
        assert evaluation is not None
        assert (end_time - start_time) < 0.1  # < 100ms requirement
        assert evaluation.evaluation_time < 0.1
    
    def test_confidence_evaluation_batch_performance(self):
        """Test batch confidence evaluation performance."""
        # Create multiple test results
        llm_results = []
        for i in range(100):  # Test with 100 results
            llm_result = LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.8,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            )
            llm_results.append(llm_result)
        
        # Measure batch evaluation time
        start_time = time.time()
        evaluations = self.evaluator.batch_evaluate(llm_results)
        end_time = time.time()
        
        # Assertions
        assert len(evaluations) == 100
        assert (end_time - start_time) < 1.0  # < 1 second for 100 evaluations
        assert all(e.evaluation_time < 0.1 for e in evaluations)
    
    def test_confidence_evaluation_error_handling(self):
        """Test confidence evaluation error handling."""
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
    
    def test_confidence_evaluation_statistics(self):
        """Test confidence evaluation statistics calculation."""
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
            ),
            ConfidenceEvaluation(
                confidence_score=0.9,
                original_confidence=0.9,
                final_confidence=0.9,
                threshold=0.7,
                action='auto_apply',
                status='approved',
                evaluation_rules_applied=[],
                evaluation_time=0.01
            )
        ]
        
        # Get statistics
        stats = self.evaluator.get_confidence_stats(evaluations)
        
        # Assertions
        assert stats['total_evaluations'] == 3
        assert stats['auto_apply_count'] == 2
        assert stats['review_count'] == 1
        assert stats['auto_apply_rate'] == 2/3
        assert stats['review_rate'] == 1/3
        assert abs(stats['average_confidence'] - 0.77) < 0.01  # Handle floating point precision
        assert stats['min_confidence'] == 0.6
        assert stats['max_confidence'] == 0.9
    
    def test_confidence_evaluation_configuration_variants(self):
        """Test confidence evaluation with different configurations."""
        # Test strict configuration
        strict_config = ConfidenceConfigBuilder.strict()
        strict_evaluator = ConfidenceEvaluator(strict_config)
        
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.75,  # Would pass default but fail strict
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = strict_evaluator.evaluate_confidence(llm_result)
        assert evaluation.threshold == 0.9  # Field-specific threshold
        assert evaluation.action == 'manual_review'
        
        # Test permissive configuration
        permissive_config = ConfidenceConfigBuilder.permissive()
        permissive_evaluator = ConfidenceEvaluator(permissive_config)
        
        llm_result.confidence = 0.65  # Would fail default but pass permissive
        evaluation = permissive_evaluator.evaluate_confidence(llm_result)
        assert evaluation.threshold == 0.7  # Field-specific threshold
        assert evaluation.action == 'auto_apply'
    
    def test_confidence_evaluation_rules_application(self):
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
        
        # Test with field that doesn't have rules
        llm_result.field = "unknown_field"
        evaluation = self.evaluator.evaluate_confidence(llm_result)
        
        # Should not have rules applied
        assert len(evaluation.evaluation_rules_applied) == 0
        assert evaluation.final_confidence == evaluation.original_confidence


if __name__ == "__main__":
    pytest.main([__file__])
