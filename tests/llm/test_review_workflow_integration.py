"""Integration tests for review workflow service."""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.config.review_config import ReviewConfig, ReviewConfigBuilder, NotificationConfig
from src.llm.review_workflow import ReviewWorkflow, ReviewItem
from src.llm.llm_interface import LLMResult
from src.llm.confidence_evaluator import ConfidenceEvaluation


class TestReviewWorkflowIntegration:
    """Integration tests for review workflow service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ReviewConfigBuilder.default()
        self.notification_config = NotificationConfig()
        self.workflow = ReviewWorkflow(self.config, self.notification_config)
    
    def test_complete_review_workflow(self):
        """Test complete review workflow from marking to approval."""
        # Create test data
        artifact = {
            'id': 'test_artifact_1',
            'roaster_id': 'test_roaster',
            'name': 'Test Coffee'
        }
        
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.6,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = ConfidenceEvaluation(
            confidence_score=0.6,
            original_confidence=0.6,
            final_confidence=0.6,
            threshold=0.7,
            action='manual_review',
            status='review',
            evaluation_rules_applied=[],
            evaluation_time=0.01
        )
        
        # Step 1: Mark for review
        review_item = self.workflow.mark_for_review(artifact, llm_result, evaluation)
        
        # Assertions for marking
        assert review_item.review_status == 'pending'
        assert artifact['processing_status'] == 'review'
        assert 'review_reason' in artifact
        
        # Step 2: Approve enrichment
        result = self.workflow.approve_enrichment(review_item, 'reviewer_1', 'Looks good')
        
        # Assertions for approval
        assert review_item.review_status == 'approved'
        assert review_item.reviewer_id == 'reviewer_1'
        assert result['field'] == 'roast_level'
        assert result['value'] == 'medium'
    
    def test_complete_review_workflow_rejection(self):
        """Test complete review workflow from marking to rejection."""
        # Create test data
        artifact = {
            'id': 'test_artifact_2',
            'roaster_id': 'test_roaster',
            'name': 'Test Coffee'
        }
        
        llm_result = LLMResult(
            field="bean_species",
            value="arabica",
            confidence=0.5,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = ConfidenceEvaluation(
            confidence_score=0.5,
            original_confidence=0.5,
            final_confidence=0.5,
            threshold=0.7,
            action='manual_review',
            status='review',
            evaluation_rules_applied=[],
            evaluation_time=0.01
        )
        
        # Step 1: Mark for review
        review_item = self.workflow.mark_for_review(artifact, llm_result, evaluation)
        
        # Step 2: Reject enrichment
        result = self.workflow.reject_enrichment(
            review_item, 
            'reviewer_1', 
            'Incorrect classification',
            'This is clearly robusta'
        )
        
        # Assertions for rejection
        assert review_item.review_status == 'rejected'
        assert review_item.reviewer_id == 'reviewer_1'
        assert result['status'] == 'rejected'
        assert result['reason'] == 'Incorrect classification'
    
    def test_batch_review_workflow(self):
        """Test batch review workflow with multiple items."""
        # Create multiple review items
        review_items = []
        
        for i in range(3):
            artifact = {
                'id': f'test_artifact_{i}',
                'roaster_id': f'test_roaster_{i}',
                'name': f'Test Coffee {i}'
            }
            
            llm_result = LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.6,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            )
            
            evaluation = ConfidenceEvaluation(
                confidence_score=0.6,
                original_confidence=0.6,
                final_confidence=0.6,
                threshold=0.7,
                action='manual_review',
                status='review',
                evaluation_rules_applied=[],
                evaluation_time=0.01
            )
            
            review_item = self.workflow.mark_for_review(artifact, llm_result, evaluation)
            review_items.append(review_item)
        
        # Get review stats
        stats = self.workflow.get_review_stats(review_items)
        
        # Assertions
        assert stats['total_reviews'] == 3
        assert stats['pending_count'] == 3
        assert stats['approval_rate'] == 0.0
        assert stats['rejection_rate'] == 0.0
    
    def test_review_workflow_with_notifications(self):
        """Test review workflow with notifications enabled."""
        config = ReviewConfig(
            send_notifications=True,
            notification_channels=["slack", "email"]
        )
        workflow = ReviewWorkflow(config, self.notification_config)
        
        # Create test data
        artifact = {'id': 'test_artifact'}
        llm_result = Mock()
        evaluation = Mock()
        evaluation.final_confidence = 0.6
        evaluation.threshold = 0.7
        
        # Mark for review (should trigger notifications)
        review_item = workflow.mark_for_review(artifact, llm_result, evaluation)
        
        # Assertions
        assert review_item is not None
        assert review_item.review_status == 'pending'
    
    def test_review_workflow_without_notifications(self):
        """Test review workflow without notifications."""
        config = ReviewConfigBuilder.no_notifications()
        workflow = ReviewWorkflow(config)
        
        # Create test data
        artifact = {'id': 'test_artifact'}
        llm_result = Mock()
        evaluation = Mock()
        evaluation.final_confidence = 0.6
        evaluation.threshold = 0.7
        
        # Mark for review (should not trigger notifications)
        review_item = workflow.mark_for_review(artifact, llm_result, evaluation)
        
        # Assertions
        assert review_item is not None
        assert review_item.review_status == 'pending'
    
    def test_review_workflow_error_handling(self):
        """Test review workflow error handling."""
        # Create invalid data
        artifact = None
        llm_result = Mock()
        evaluation = Mock()
        
        # Should handle error gracefully
        with pytest.raises(Exception):  # ReviewWorkflowError
            self.workflow.mark_for_review(artifact, llm_result, evaluation)
    
    def test_review_workflow_performance(self):
        """Test review workflow performance requirements."""
        # Create test data
        artifact = {'id': 'test_artifact'}
        llm_result = Mock()
        evaluation = Mock()
        evaluation.final_confidence = 0.6
        evaluation.threshold = 0.7
        
        # Measure review workflow time
        start_time = time.time()
        review_item = self.workflow.mark_for_review(artifact, llm_result, evaluation)
        end_time = time.time()
        
        # Assertions
        assert review_item is not None
        assert (end_time - start_time) < 1.0  # < 1 second requirement
    
    def test_review_workflow_configuration_variants(self):
        """Test review workflow with different configurations."""
        # Test fast-track configuration
        fast_config = ReviewConfigBuilder.fast_track()
        fast_workflow = ReviewWorkflow(fast_config)
        
        assert fast_config.review_timeout_hours == 24
        assert fast_config.escalation_hours == 48
        
        # Test thorough configuration
        thorough_config = ReviewConfigBuilder.thorough()
        thorough_workflow = ReviewWorkflow(thorough_config)
        
        assert thorough_config.review_timeout_hours == 168
        assert thorough_config.escalation_hours == 336
        
        # Test no-notifications configuration
        no_notif_config = ReviewConfigBuilder.no_notifications()
        no_notif_workflow = ReviewWorkflow(no_notif_config)
        
        assert no_notif_config.send_notifications == False


if __name__ == "__main__":
    pytest.main([__file__])
