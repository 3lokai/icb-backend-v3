"""Configuration for review workflow service."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime, timezone


class ReviewConfig(BaseModel):
    """Configuration for review workflow service."""
    
    # Review settings
    send_notifications: bool = Field(default=True)
    notification_channels: List[str] = Field(default_factory=lambda: ["slack", "email"])
    
    # Review timeout settings
    review_timeout_hours: int = Field(default=72, gt=0)  # 3 days default
    escalation_hours: int = Field(default=168, gt=0)  # 7 days escalation
    
    # Review assignment
    auto_assign: bool = Field(default=True)
    default_reviewer: Optional[str] = Field(default=None)
    reviewer_rotation: bool = Field(default=True)
    
    # Review categories
    review_categories: List[str] = Field(default_factory=lambda: [
        "low_confidence",
        "ambiguous_result", 
        "validation_error",
        "manual_override"
    ])
    
    # Performance settings
    batch_review_size: int = Field(default=50, gt=0)
    review_processing_timeout: float = Field(default=1.0, gt=0)  # 1 second max
    
    # Logging
    log_review_actions: bool = Field(default=True)
    log_review_decisions: bool = Field(default=True)


class NotificationConfig(BaseModel):
    """Configuration for review notifications."""
    
    # Slack settings
    slack_webhook_url: Optional[str] = Field(default=None)
    slack_channel: str = Field(default="#coffee-reviews")
    slack_username: str = Field(default="Coffee Review Bot")
    
    # Email settings
    email_smtp_host: Optional[str] = Field(default=None)
    email_smtp_port: int = Field(default=587)
    email_username: Optional[str] = Field(default=None)
    email_password: Optional[str] = Field(default=None)
    email_from: str = Field(default="noreply@coffee-reviews.com")
    
    # Notification templates
    review_required_template: str = Field(
        default="Review required for artifact {artifact_id}: {reason}"
    )
    review_approved_template: str = Field(
        default="Review approved for artifact {artifact_id} by {reviewer}"
    )
    review_rejected_template: str = Field(
        default="Review rejected for artifact {artifact_id} by {reviewer}: {reason}"
    )


class ReviewConfigBuilder:
    """Builder for review configuration with common presets."""
    
    @staticmethod
    def default() -> ReviewConfig:
        """Create default review configuration."""
        return ReviewConfig()
    
    @staticmethod
    def fast_track() -> ReviewConfig:
        """Create fast-track review configuration (shorter timeouts)."""
        return ReviewConfig(
            review_timeout_hours=24,
            escalation_hours=48,
            batch_review_size=25
        )
    
    @staticmethod
    def thorough() -> ReviewConfig:
        """Create thorough review configuration (longer timeouts)."""
        return ReviewConfig(
            review_timeout_hours=168,  # 1 week
            escalation_hours=336,  # 2 weeks
            batch_review_size=100
        )
    
    @staticmethod
    def no_notifications() -> ReviewConfig:
        """Create review configuration without notifications."""
        return ReviewConfig(
            send_notifications=False,
            notification_channels=[]
        )
