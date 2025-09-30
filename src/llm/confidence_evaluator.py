"""Confidence evaluation service for LLM results."""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

from src.config.confidence_config import ConfidenceConfig, EvaluationRule
from src.llm.llm_interface import LLMResult

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceEvaluation:
    """Result of confidence evaluation."""
    
    confidence_score: float
    original_confidence: float
    final_confidence: float
    threshold: float
    action: str  # 'auto_apply' or 'manual_review'
    status: str  # 'approved', 'review', 'error'
    evaluation_rules_applied: List[str]
    error_message: Optional[str] = None
    evaluation_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'confidence_score': self.confidence_score,
            'original_confidence': self.original_confidence,
            'final_confidence': self.final_confidence,
            'threshold': self.threshold,
            'action': self.action,
            'status': self.status,
            'evaluation_rules_applied': self.evaluation_rules_applied,
            'error_message': self.error_message,
            'evaluation_time': self.evaluation_time
        }


class ConfidenceEvaluator:
    """Service for evaluating LLM result confidence and determining actions."""
    
    def __init__(self, config: ConfidenceConfig):
        """Initialize confidence evaluator with configuration."""
        self.config = config
        self.threshold = config.confidence_threshold
        self.evaluation_rules = self._build_evaluation_rules()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _build_evaluation_rules(self) -> List[EvaluationRule]:
        """Build evaluation rules from configuration."""
        rules = []
        
        # Default rules for common fields
        default_rules = [
            EvaluationRule(
                name="roast_level_high_confidence",
                field_pattern="roast_level",
                confidence_multiplier=1.1,
                min_confidence=0.0,
                max_confidence=1.0
            ),
            EvaluationRule(
                name="species_high_confidence", 
                field_pattern="bean_species",
                confidence_multiplier=1.05,
                min_confidence=0.0,
                max_confidence=1.0
            ),
            EvaluationRule(
                name="varieties_moderate_confidence",
                field_pattern="varieties",
                confidence_multiplier=0.95,
                min_confidence=0.0,
                max_confidence=1.0
            ),
            EvaluationRule(
                name="geographic_data_moderate_confidence",
                field_pattern="geographic_data",
                confidence_multiplier=0.9,
                min_confidence=0.0,
                max_confidence=1.0
            )
        ]
        
        return default_rules
    
    def evaluate_confidence(self, llm_result: LLMResult) -> ConfidenceEvaluation:
        """Evaluate LLM result confidence and determine action."""
        start_time = time.time()
        
        try:
            # Extract confidence score from LLM result
            confidence_score = llm_result.confidence
            
            # Apply evaluation rules
            evaluation = self._apply_evaluation_rules(llm_result, confidence_score)
            
            # Get field-specific threshold
            field_threshold = self._get_field_threshold(llm_result.field)
            
            # Determine action based on confidence
            if evaluation.final_confidence >= field_threshold:
                evaluation.action = 'auto_apply'
                evaluation.status = 'approved'
            else:
                evaluation.action = 'manual_review'
                evaluation.status = 'review'
            
            evaluation.threshold = field_threshold
            evaluation.evaluation_time = time.time() - start_time
            
            # Log evaluation if configured
            if self.config.log_evaluations:
                self.logger.info(
                    f"Confidence evaluation: field={llm_result.field}, "
                    f"confidence={evaluation.final_confidence:.3f}, "
                    f"threshold={field_threshold:.3f}, "
                    f"action={evaluation.action}"
                )
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Confidence evaluation failed: {str(e)}")
            return ConfidenceEvaluation(
                confidence_score=0.0,
                original_confidence=llm_result.confidence,
                final_confidence=0.0,
                threshold=self.threshold,
                action='manual_review',
                status='error',
                evaluation_rules_applied=[],
                error_message=str(e),
                evaluation_time=time.time() - start_time
            )
    
    def _apply_evaluation_rules(self, llm_result: LLMResult, confidence_score: float) -> ConfidenceEvaluation:
        """Apply custom evaluation rules to confidence score."""
        evaluation = ConfidenceEvaluation(
            confidence_score=confidence_score,
            original_confidence=confidence_score,
            final_confidence=confidence_score,
            threshold=self.threshold,
            action='manual_review',
            status='review',
            evaluation_rules_applied=[]
        )
        
        # Apply field-specific rules
        for rule in self.evaluation_rules:
            if rule.matches(llm_result.field):
                confidence_score = rule.apply(confidence_score)
                evaluation.evaluation_rules_applied.append(rule.name)
        
        evaluation.final_confidence = confidence_score
        return evaluation
    
    def _get_field_threshold(self, field: str) -> float:
        """Get confidence threshold for specific field."""
        return self.config.field_thresholds.get(field, self.threshold)
    
    def batch_evaluate(self, llm_results: List[LLMResult]) -> List[ConfidenceEvaluation]:
        """Evaluate confidence for multiple LLM results in batch."""
        evaluations = []
        
        for llm_result in llm_results:
            evaluation = self.evaluate_confidence(llm_result)
            evaluations.append(evaluation)
        
        return evaluations
    
    def get_confidence_stats(self, evaluations: List[ConfidenceEvaluation]) -> Dict[str, Any]:
        """Get statistics from confidence evaluations."""
        if not evaluations:
            return {}
        
        auto_apply_count = sum(1 for e in evaluations if e.action == 'auto_apply')
        review_count = sum(1 for e in evaluations if e.action == 'manual_review')
        error_count = sum(1 for e in evaluations if e.status == 'error')
        
        confidence_scores = [e.final_confidence for e in evaluations if e.status != 'error']
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            'total_evaluations': len(evaluations),
            'auto_apply_count': auto_apply_count,
            'review_count': review_count,
            'error_count': error_count,
            'auto_apply_rate': auto_apply_count / len(evaluations) if evaluations else 0.0,
            'review_rate': review_count / len(evaluations) if evaluations else 0.0,
            'error_rate': error_count / len(evaluations) if evaluations else 0.0,
            'average_confidence': avg_confidence,
            'min_confidence': min(confidence_scores) if confidence_scores else 0.0,
            'max_confidence': max(confidence_scores) if confidence_scores else 0.0
        }
