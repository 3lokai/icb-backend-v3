"""Review workflow service for low-confidence LLM results."""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

from src.config.review_config import ReviewConfig, NotificationConfig
from src.llm.llm_interface import LLMResult
from src.llm.confidence_evaluator import ConfidenceEvaluation

logger = logging.getLogger(__name__)


@dataclass
class ReviewItem:
    """Individual review item."""
    
    artifact_id: str
    field: str
    llm_result: LLMResult
    confidence_evaluation: ConfidenceEvaluation
    review_reason: str
    review_status: str = "pending"  # pending, approved, rejected, escalated
    reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime = None
    reviewed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class ReviewWorkflow:
    """Service for managing review workflow for low-confidence LLM results."""
    
    def __init__(self, config: ReviewConfig, notification_config: NotificationConfig = None):
        """Initialize review workflow with configuration."""
        self.config = config
        self.notification_config = notification_config or NotificationConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize notification attributes
        self.slack_webhook_url = getattr(self.notification_config, 'slack_webhook_url', None)
        self.email_config = getattr(self.notification_config, 'email_config', None)
    
    def mark_for_review(self, artifact: Dict, llm_result: LLMResult, evaluation: ConfidenceEvaluation) -> ReviewItem:
        """Mark artifact for manual review due to low confidence."""
        try:
            # Create review item
            review_item = ReviewItem(
                artifact_id=artifact.get('id', 'unknown'),
                field=llm_result.field,
                llm_result=llm_result,
                confidence_evaluation=evaluation,
                review_reason=f"Low confidence: {evaluation.final_confidence:.3f} < {evaluation.threshold:.3f}"
            )
            
            # Update artifact processing status
            artifact['processing_status'] = 'review'
            artifact['review_reason'] = review_item.review_reason
            artifact['review_timestamp'] = datetime.now(timezone.utc)
            artifact['review_item_id'] = f"{review_item.artifact_id}_{review_item.field}_{int(time.time())}"
            
            # Send notification if configured
            if self.config.send_notifications:
                self._send_review_notification(review_item, artifact)
            
            # Log review action
            if self.config.log_review_actions:
                self.logger.info(
                    f"Artifact marked for review: {review_item.artifact_id}, "
                    f"field={review_item.field}, "
                    f"confidence={evaluation.final_confidence:.3f}"
                )
            
            return review_item
            
        except Exception as e:
            self.logger.error(f"Review workflow failed: {str(e)}")
            raise ReviewWorkflowError(f"Review workflow failed: {str(e)}")
    
    def approve_enrichment(self, review_item: ReviewItem, reviewer_id: str, notes: str = None) -> Dict[str, Any]:
        """Approve low-confidence enrichment after manual review."""
        try:
            # Update review item
            review_item.review_status = 'approved'
            review_item.reviewer_id = reviewer_id
            review_item.review_notes = notes
            review_item.reviewed_at = datetime.now(timezone.utc)
            
            # Apply enrichment to artifact
            enrichment_result = self._apply_enrichment(review_item)
            
            # Send approval notification
            if self.config.send_notifications:
                self._send_approval_notification(review_item)
            
            # Log approval
            if self.config.log_review_decisions:
                self.logger.info(
                    f"Review approved: {review_item.artifact_id}, "
                    f"field={review_item.field}, "
                    f"reviewer={reviewer_id}"
                )
            
            return enrichment_result
            
        except Exception as e:
            self.logger.error(f"Enrichment approval failed: {str(e)}")
            raise EnrichmentApprovalError(f"Enrichment approval failed: {str(e)}")
    
    def reject_enrichment(self, review_item: ReviewItem, reviewer_id: str, reason: str, notes: str = None) -> Dict[str, Any]:
        """Reject low-confidence enrichment after manual review."""
        try:
            # Update review item
            review_item.review_status = 'rejected'
            review_item.reviewer_id = reviewer_id
            review_item.review_notes = notes
            review_item.reviewed_at = datetime.now(timezone.utc)
            
            # Send rejection notification
            if self.config.send_notifications:
                self._send_rejection_notification(review_item, reason)
            
            # Log rejection
            if self.config.log_review_decisions:
                self.logger.info(
                    f"Review rejected: {review_item.artifact_id}, "
                    f"field={review_item.field}, "
                    f"reviewer={reviewer_id}, "
                    f"reason={reason}"
                )
            
            return {
                'status': 'rejected',
                'reason': reason,
                'reviewer_id': reviewer_id,
                'reviewed_at': review_item.reviewed_at
            }
            
        except Exception as e:
            self.logger.error(f"Enrichment rejection failed: {str(e)}")
            raise EnrichmentRejectionError(f"Enrichment rejection failed: {str(e)}")
    
    def _apply_enrichment(self, review_item: ReviewItem) -> Dict[str, Any]:
        """Apply approved enrichment to artifact."""
        field = review_item.llm_result.field
        value = review_item.llm_result.value
        
        # This would typically update the artifact in the database
        # For now, return the enrichment data
        return {
            'field': field,
            'value': value,
            'confidence': review_item.confidence_evaluation.final_confidence,
            'applied_at': datetime.now(timezone.utc),
            'reviewer_id': review_item.reviewer_id
        }
    
    def _send_review_notification(self, review_item: ReviewItem, artifact: Dict):
        """Send notification for review required."""
        if not self.config.send_notifications:
            return
        
        message = self.notification_config.review_required_template.format(
            artifact_id=review_item.artifact_id,
            reason=review_item.review_reason
        )
        
        # Send to configured channels
        for channel in self.config.notification_channels:
            if channel == "slack":
                self._send_slack_notification(message)
            elif channel == "email":
                self._send_email_notification(message, artifact)
    
    def _send_approval_notification(self, review_item: ReviewItem):
        """Send notification for review approval."""
        message = self.notification_config.review_approved_template.format(
            artifact_id=review_item.artifact_id,
            reviewer=review_item.reviewer_id
        )
        
        for channel in self.config.notification_channels:
            if channel == "slack":
                self._send_slack_notification(message)
            elif channel == "email":
                self._send_email_notification(message, {})
    
    def _send_rejection_notification(self, review_item: ReviewItem, reason: str):
        """Send notification for review rejection."""
        message = self.notification_config.review_rejected_template.format(
            artifact_id=review_item.artifact_id,
            reviewer=review_item.reviewer_id,
            reason=reason
        )
        
        for channel in self.config.notification_channels:
            if channel == "slack":
                self._send_slack_notification(message)
            elif channel == "email":
                self._send_email_notification(message, {})
    
    def _send_slack_notification(self, message: str):
        """Send Slack notification for monitoring (not manual review)."""
        try:
            if not self.slack_webhook_url:
                self.logger.warning("Slack webhook URL not configured, skipping notification")
                return
            
            import requests
            
            payload = {
                "text": f"🤖 Coffee Data Processing: {message}",
                "username": "Coffee Data Bot",
                "icon_emoji": ":coffee:"
            }
            
            response = requests.post(
                self.slack_webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.debug("Slack notification sent successfully")
            else:
                self.logger.warning(f"Slack notification failed: status_code={response.status_code}, response={response.text}")
                
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {str(e)}")
            # Fallback to logging
            self.logger.info(f"Slack notification (fallback): {message}")
    
    def _send_email_notification(self, message: str, artifact: Dict):
        """Send email notification (placeholder implementation)."""
        # This would integrate with email service
        self.logger.info(f"Email notification: {message}")
    
    def get_pending_reviews(self, limit: int = 50, rpc_client=None) -> List[ReviewItem]:
        """Get low-confidence enrichments for monitoring (no manual review needed)."""
        try:
            if not rpc_client:
                return []
            
            # Get low-confidence enrichments for monitoring
            result = rpc_client.supabase_client.table("enrichments").select(
                "enrichment_id, artifact_id, field, confidence_score, created_at"
            ).eq("applied", False).order("created_at", desc=True).limit(limit).execute()
            
            review_items = []
            for record in result.data:
                review_items.append(ReviewItem(
                    enrichment_id=record["enrichment_id"],
                    artifact_id=record["artifact_id"],
                    field=record["field"],
                    confidence_score=record["confidence_score"],
                    review_status="monitoring",  # Just for monitoring, not manual review
                    created_at=record["created_at"]
                ))
            
            return review_items
            
        except Exception as e:
            self.logger.error(f"Failed to get pending reviews: {str(e)}")
            return []
    
    def get_review_stats(self, review_items: List[ReviewItem]) -> Dict[str, Any]:
        """Get statistics from review items."""
        if not review_items:
            return {}
        
        pending_count = sum(1 for item in review_items if item.review_status == 'pending')
        approved_count = sum(1 for item in review_items if item.review_status == 'approved')
        rejected_count = sum(1 for item in review_items if item.review_status == 'rejected')
        escalated_count = sum(1 for item in review_items if item.review_status == 'escalated')
        
        return {
            'total_reviews': len(review_items),
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'escalated_count': escalated_count,
            'approval_rate': approved_count / len(review_items) if review_items else 0.0,
            'rejection_rate': rejected_count / len(review_items) if review_items else 0.0
        }


class ReviewWorkflowError(Exception):
    """Exception raised for review workflow errors."""
    pass


class EnrichmentApprovalError(Exception):
    """Exception raised for enrichment approval errors."""
    pass


class EnrichmentRejectionError(Exception):
    """Exception raised for enrichment rejection errors."""
    pass
