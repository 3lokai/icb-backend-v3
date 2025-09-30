"""Unit tests for review workflow service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.config.review_config import ReviewConfig, ReviewConfigBuilder, NotificationConfig
from src.llm.review_workflow import ReviewWorkflow, ReviewItem, ReviewWorkflowError
from src.llm.llm_interface import LLMResult
from src.llm.confidence_evaluator import ConfidenceEvaluation


class TestReviewWorkflow:
    """Test cases for review workflow service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ReviewConfigBuilder.default()
        self.notification_config = NotificationConfig()
        self.workflow = ReviewWorkflow(self.config, self.notification_config)
    
    def test_mark_for_review(self):
        """Test marking artifact for review."""
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
        
        # Mark for review
        review_item = self.workflow.mark_for_review(artifact, llm_result, evaluation)
        
        # Assertions
        assert review_item.artifact_id == 'test_artifact_1'
        assert review_item.field == 'roast_level'
        assert review_item.review_status == 'pending'
        assert review_item.review_reason.startswith('Low confidence:')
        assert artifact['processing_status'] == 'review'
        assert 'review_reason' in artifact
        assert 'review_timestamp' in artifact
    
    def test_approve_enrichment(self):
        """Test approving enrichment after review."""
        # Create review item
        review_item = ReviewItem(
            artifact_id='test_artifact_1',
            field='roast_level',
            llm_result=LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.6,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            ),
            confidence_evaluation=ConfidenceEvaluation(
                confidence_score=0.6,
                original_confidence=0.6,
                final_confidence=0.6,
                threshold=0.7,
                action='manual_review',
                status='review',
                evaluation_rules_applied=[],
                evaluation_time=0.01
            ),
            review_reason="Low confidence: 0.600 < 0.700"
        )
        
        # Approve enrichment
        result = self.workflow.approve_enrichment(review_item, 'reviewer_1', 'Looks good')
        
        # Assertions
        assert review_item.review_status == 'approved'
        assert review_item.reviewer_id == 'reviewer_1'
        assert review_item.review_notes == 'Looks good'
        assert review_item.reviewed_at is not None
        assert result['field'] == 'roast_level'
        assert result['value'] == 'medium'
        assert result['reviewer_id'] == 'reviewer_1'
    
    def test_reject_enrichment(self):
        """Test rejecting enrichment after review."""
        # Create review item
        review_item = ReviewItem(
            artifact_id='test_artifact_1',
            field='roast_level',
            llm_result=LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.6,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            ),
            confidence_evaluation=ConfidenceEvaluation(
                confidence_score=0.6,
                original_confidence=0.6,
                final_confidence=0.6,
                threshold=0.7,
                action='manual_review',
                status='review',
                evaluation_rules_applied=[],
                evaluation_time=0.01
            ),
            review_reason="Low confidence: 0.600 < 0.700"
        )
        
        # Reject enrichment
        result = self.workflow.reject_enrichment(
            review_item, 
            'reviewer_1', 
            'Incorrect classification',
            'This is clearly a dark roast'
        )
        
        # Assertions
        assert review_item.review_status == 'rejected'
        assert review_item.reviewer_id == 'reviewer_1'
        assert review_item.review_notes == 'This is clearly a dark roast'
        assert review_item.reviewed_at is not None
        assert result['status'] == 'rejected'
        assert result['reason'] == 'Incorrect classification'
        assert result['reviewer_id'] == 'reviewer_1'
    
    def test_review_stats(self):
        """Test review statistics calculation."""
        # Create test review items
        review_items = [
            ReviewItem(
                artifact_id='test_1',
                field='roast_level',
                llm_result=Mock(),
                confidence_evaluation=Mock(),
                review_reason="Low confidence",
                review_status='pending'
            ),
            ReviewItem(
                artifact_id='test_2',
                field='bean_species',
                llm_result=Mock(),
                confidence_evaluation=Mock(),
                review_reason="Low confidence",
                review_status='approved'
            ),
            ReviewItem(
                artifact_id='test_3',
                field='process_method',
                llm_result=Mock(),
                confidence_evaluation=Mock(),
                review_reason="Low confidence",
                review_status='rejected'
            )
        ]
        
        # Get stats
        stats = self.workflow.get_review_stats(review_items)
        
        # Assertions
        assert stats['total_reviews'] == 3
        assert stats['pending_count'] == 1
        assert stats['approved_count'] == 1
        assert stats['rejected_count'] == 1
        assert stats['approval_rate'] == 1/3
        assert stats['rejection_rate'] == 1/3
    
    def test_error_handling(self):
        """Test error handling in review workflow."""
        # Create invalid data that should cause error
        artifact = None  # Invalid artifact
        llm_result = Mock()
        evaluation = Mock()
        
        # Should raise ReviewWorkflowError
        with pytest.raises(ReviewWorkflowError):
            self.workflow.mark_for_review(artifact, llm_result, evaluation)
    
    def test_no_notifications_config(self):
        """Test review workflow without notifications."""
        config = ReviewConfigBuilder.no_notifications()
        workflow = ReviewWorkflow(config)
        
        # Create test data
        artifact = {'id': 'test_artifact'}
        llm_result = Mock()
        evaluation = Mock()
        evaluation.final_confidence = 0.6
        evaluation.threshold = 0.7
        
        # Should not send notifications
        review_item = workflow.mark_for_review(artifact, llm_result, evaluation)
        assert review_item is not None
    
    def test_fast_track_config(self):
        """Test fast-track review configuration."""
        config = ReviewConfigBuilder.fast_track()
        workflow = ReviewWorkflow(config)
        
        # Assertions
        assert config.review_timeout_hours == 24
        assert config.escalation_hours == 48
        assert config.batch_review_size == 25
    
    def test_thorough_config(self):
        """Test thorough review configuration."""
        config = ReviewConfigBuilder.thorough()
        workflow = ReviewWorkflow(config)
        
        # Assertions
        assert config.review_timeout_hours == 168  # 1 week
        assert config.escalation_hours == 336  # 2 weeks
        assert config.batch_review_size == 100


class TestReviewConfig:
    """Test cases for review configuration."""
    
    def test_default_configuration(self):
        """Test default configuration creation."""
        config = ReviewConfigBuilder.default()
        
        assert config.send_notifications == True
        assert config.review_timeout_hours == 72
        assert config.escalation_hours == 168
        assert config.auto_assign == True
        assert config.batch_review_size == 50
    
    def test_fast_track_configuration(self):
        """Test fast-track configuration creation."""
        config = ReviewConfigBuilder.fast_track()
        
        assert config.review_timeout_hours == 24
        assert config.escalation_hours == 48
        assert config.batch_review_size == 25
    
    def test_thorough_configuration(self):
        """Test thorough configuration creation."""
        config = ReviewConfigBuilder.thorough()
        
        assert config.review_timeout_hours == 168
        assert config.escalation_hours == 336
        assert config.batch_review_size == 100
    
    def test_no_notifications_configuration(self):
        """Test no-notifications configuration creation."""
        config = ReviewConfigBuilder.no_notifications()
        
        assert config.send_notifications == False
        assert config.notification_channels == []


class TestNotificationConfig:
    """Test cases for notification configuration."""
    
    def test_default_notification_config(self):
        """Test default notification configuration."""
        config = NotificationConfig()
        
        assert config.slack_channel == "#coffee-reviews"
        assert config.slack_username == "Coffee Review Bot"
        assert config.email_from == "noreply@coffee-reviews.com"
        assert config.email_smtp_port == 587
    
    def test_notification_templates(self):
        """Test notification template formatting."""
        config = NotificationConfig()
        
        # Test review required template
        message = config.review_required_template.format(
            artifact_id="test_123",
            reason="Low confidence"
        )
        assert "test_123" in message
        assert "Low confidence" in message
        
        # Test review approved template
        message = config.review_approved_template.format(
            artifact_id="test_123",
            reviewer="reviewer_1"
        )
        assert "test_123" in message
        assert "reviewer_1" in message


if __name__ == "__main__":
    pytest.main([__file__])
