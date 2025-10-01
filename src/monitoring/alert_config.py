"""
Alert configuration service.

This module provides configuration management for alert thresholds,
Slack webhooks, Sentry DSN, and other alerting settings.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .alert_service import AlertSeverity


@dataclass
class AlertConfig:
    """Alert configuration settings."""
    # Required parameters first
    slack_webhook_url: str
    sentry_dsn: str
    
    # Optional parameters with defaults
    slack_enabled: bool = True
    sentry_environment: str = "production"
    sentry_enabled: bool = True
    
    # Alert thresholds
    review_rate_spike_threshold: float = 50.0
    rpc_error_rate_threshold: float = 10.0
    system_health_threshold: float = 30.0
    fetch_latency_threshold: float = 60.0
    validation_error_rate_threshold: float = 20.0
    database_failure_threshold: float = 5.0
    memory_usage_threshold: float = 85.0
    disk_usage_threshold: float = 90.0
    
    # Alert cooldowns (minutes)
    review_rate_cooldown: int = 10
    rpc_error_cooldown: int = 5
    system_health_cooldown: int = 5
    fetch_latency_cooldown: int = 15
    validation_error_cooldown: int = 10
    database_failure_cooldown: int = 5
    memory_usage_cooldown: int = 30
    disk_usage_cooldown: int = 15
    
    # Alert throttling
    throttle_window_seconds: int = 300  # 5 minutes
    max_alerts_per_window: int = 10
    
    # Monitoring intervals
    threshold_check_interval_seconds: int = 60  # 1 minute
    metrics_collection_interval_seconds: int = 30  # 30 seconds
    
    # Alert escalation
    enable_alert_escalation: bool = True
    escalation_delay_minutes: int = 15
    
    # Notification preferences
    enable_slack_notifications: bool = True
    enable_sentry_notifications: bool = True
    enable_email_notifications: bool = False
    
    # Debug settings
    debug_mode: bool = False
    log_alert_attempts: bool = True


class AlertConfigManager:
    """Manages alert configuration from environment variables and defaults."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.config = self._load_config()
    
    def _load_config(self) -> AlertConfig:
        """Load configuration from environment variables."""
        return AlertConfig(
            # Slack configuration
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
            slack_enabled=os.getenv("SLACK_ALERTS_ENABLED", "true").lower() == "true",
            
            # Sentry configuration
            sentry_dsn=os.getenv("SENTRY_DSN", ""),
            sentry_environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
            sentry_enabled=bool(os.getenv("SENTRY_DSN", "")),
            
            # Alert thresholds
            review_rate_spike_threshold=float(os.getenv("ALERT_REVIEW_RATE_THRESHOLD", "50.0")),
            rpc_error_rate_threshold=float(os.getenv("ALERT_RPC_ERROR_THRESHOLD", "10.0")),
            system_health_threshold=float(os.getenv("ALERT_SYSTEM_HEALTH_THRESHOLD", "30.0")),
            fetch_latency_threshold=float(os.getenv("ALERT_FETCH_LATENCY_THRESHOLD", "60.0")),
            validation_error_rate_threshold=float(os.getenv("ALERT_VALIDATION_ERROR_THRESHOLD", "20.0")),
            database_failure_threshold=float(os.getenv("ALERT_DATABASE_FAILURE_THRESHOLD", "5.0")),
            memory_usage_threshold=float(os.getenv("ALERT_MEMORY_USAGE_THRESHOLD", "85.0")),
            disk_usage_threshold=float(os.getenv("ALERT_DISK_USAGE_THRESHOLD", "90.0")),
            
            # Alert cooldowns
            review_rate_cooldown=int(os.getenv("ALERT_REVIEW_RATE_COOLDOWN", "10")),
            rpc_error_cooldown=int(os.getenv("ALERT_RPC_ERROR_COOLDOWN", "5")),
            system_health_cooldown=int(os.getenv("ALERT_SYSTEM_HEALTH_COOLDOWN", "5")),
            fetch_latency_cooldown=int(os.getenv("ALERT_FETCH_LATENCY_COOLDOWN", "15")),
            validation_error_cooldown=int(os.getenv("ALERT_VALIDATION_ERROR_COOLDOWN", "10")),
            database_failure_cooldown=int(os.getenv("ALERT_DATABASE_FAILURE_COOLDOWN", "5")),
            memory_usage_cooldown=int(os.getenv("ALERT_MEMORY_USAGE_COOLDOWN", "30")),
            disk_usage_cooldown=int(os.getenv("ALERT_DISK_USAGE_COOLDOWN", "15")),
            
            # Alert throttling
            throttle_window_seconds=int(os.getenv("ALERT_THROTTLE_WINDOW", "300")),
            max_alerts_per_window=int(os.getenv("ALERT_MAX_PER_WINDOW", "10")),
            
            # Monitoring intervals
            threshold_check_interval_seconds=int(os.getenv("ALERT_CHECK_INTERVAL", "60")),
            metrics_collection_interval_seconds=int(os.getenv("METRICS_COLLECTION_INTERVAL", "30")),
            
            # Alert escalation
            enable_alert_escalation=os.getenv("ALERT_ESCALATION_ENABLED", "true").lower() == "true",
            escalation_delay_minutes=int(os.getenv("ALERT_ESCALATION_DELAY", "15")),
            
            # Notification preferences
            enable_slack_notifications=os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower() == "true",
            enable_sentry_notifications=os.getenv("SENTRY_NOTIFICATIONS_ENABLED", "true").lower() == "true",
            enable_email_notifications=os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "false").lower() == "true",
            
            # Debug settings
            debug_mode=os.getenv("ALERT_DEBUG_MODE", "false").lower() == "true",
            log_alert_attempts=os.getenv("ALERT_LOG_ATTEMPTS", "true").lower() == "true"
        )
    
    def get_config(self) -> AlertConfig:
        """Get current alert configuration."""
        return self.config
    
    def update_config(self, **kwargs) -> AlertConfig:
        """Update configuration with new values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        return self.config
    
    def get_threshold_config(self) -> Dict[str, Any]:
        """Get threshold configuration as dictionary."""
        return {
            "review_rate_spike": {
                "threshold": self.config.review_rate_spike_threshold,
                "cooldown_minutes": self.config.review_rate_cooldown,
                "severity": AlertSeverity.WARNING.value
            },
            "rpc_error_rate": {
                "threshold": self.config.rpc_error_rate_threshold,
                "cooldown_minutes": self.config.rpc_error_cooldown,
                "severity": AlertSeverity.CRITICAL.value
            },
            "system_health": {
                "threshold": self.config.system_health_threshold,
                "cooldown_minutes": self.config.system_health_cooldown,
                "severity": AlertSeverity.CRITICAL.value
            },
            "fetch_latency": {
                "threshold": self.config.fetch_latency_threshold,
                "cooldown_minutes": self.config.fetch_latency_cooldown,
                "severity": AlertSeverity.WARNING.value
            },
            "validation_error_rate": {
                "threshold": self.config.validation_error_rate_threshold,
                "cooldown_minutes": self.config.validation_error_cooldown,
                "severity": AlertSeverity.WARNING.value
            },
            "database_failures": {
                "threshold": self.config.database_failure_threshold,
                "cooldown_minutes": self.config.database_failure_cooldown,
                "severity": AlertSeverity.CRITICAL.value
            },
            "memory_usage": {
                "threshold": self.config.memory_usage_threshold,
                "cooldown_minutes": self.config.memory_usage_cooldown,
                "severity": AlertSeverity.WARNING.value
            },
            "disk_usage": {
                "threshold": self.config.disk_usage_threshold,
                "cooldown_minutes": self.config.disk_usage_cooldown,
                "severity": AlertSeverity.CRITICAL.value
            }
        }
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration."""
        return {
            "slack": {
                "enabled": self.config.slack_enabled and self.config.enable_slack_notifications,
                "webhook_url": self.config.slack_webhook_url,
                "configured": bool(self.config.slack_webhook_url)
            },
            "sentry": {
                "enabled": self.config.sentry_enabled and self.config.enable_sentry_notifications,
                "dsn": self.config.sentry_dsn,
                "environment": self.config.sentry_environment,
                "configured": bool(self.config.sentry_dsn)
            },
            "email": {
                "enabled": self.config.enable_email_notifications,
                "configured": False  # Not implemented yet
            }
        }
    
    def get_throttling_config(self) -> Dict[str, Any]:
        """Get throttling configuration."""
        return {
            "throttle_window_seconds": self.config.throttle_window_seconds,
            "max_alerts_per_window": self.config.max_alerts_per_window,
            "check_interval_seconds": self.config.threshold_check_interval_seconds,
            "metrics_collection_interval_seconds": self.config.metrics_collection_interval_seconds
        }
    
    def get_debug_config(self) -> Dict[str, Any]:
        """Get debug configuration."""
        return {
            "debug_mode": self.config.debug_mode,
            "log_alert_attempts": self.config.log_alert_attempts,
            "environment": self.config.sentry_environment
        }
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any issues."""
        issues = []
        
        # Check required configurations
        if self.config.slack_enabled and not self.config.slack_webhook_url:
            issues.append("Slack webhook URL is required when Slack alerts are enabled")
        
        if self.config.sentry_enabled and not self.config.sentry_dsn:
            issues.append("Sentry DSN is required when Sentry is enabled")
        
        # Check threshold values
        if self.config.review_rate_spike_threshold <= 0:
            issues.append("Review rate spike threshold must be positive")
        
        if self.config.rpc_error_rate_threshold <= 0 or self.config.rpc_error_rate_threshold > 100:
            issues.append("RPC error rate threshold must be between 0 and 100")
        
        if self.config.system_health_threshold <= 0 or self.config.system_health_threshold > 100:
            issues.append("System health threshold must be between 0 and 100")
        
        if self.config.fetch_latency_threshold <= 0:
            issues.append("Fetch latency threshold must be positive")
        
        if self.config.validation_error_rate_threshold <= 0 or self.config.validation_error_rate_threshold > 100:
            issues.append("Validation error rate threshold must be between 0 and 100")
        
        if self.config.database_failure_threshold <= 0:
            issues.append("Database failure threshold must be positive")
        
        if self.config.memory_usage_threshold <= 0 or self.config.memory_usage_threshold > 100:
            issues.append("Memory usage threshold must be between 0 and 100")
        
        if self.config.disk_usage_threshold <= 0 or self.config.disk_usage_threshold > 100:
            issues.append("Disk usage threshold must be between 0 and 100")
        
        # Check cooldown values
        cooldowns = [
            self.config.review_rate_cooldown,
            self.config.rpc_error_cooldown,
            self.config.system_health_cooldown,
            self.config.fetch_latency_cooldown,
            self.config.validation_error_cooldown,
            self.config.database_failure_cooldown,
            self.config.memory_usage_cooldown,
            self.config.disk_usage_cooldown
        ]
        
        for cooldown in cooldowns:
            if cooldown <= 0:
                issues.append("All cooldown values must be positive")
                break
        
        # Check throttling values
        if self.config.throttle_window_seconds <= 0:
            issues.append("Throttle window must be positive")
        
        if self.config.max_alerts_per_window <= 0:
            issues.append("Max alerts per window must be positive")
        
        if self.config.threshold_check_interval_seconds <= 0:
            issues.append("Threshold check interval must be positive")
        
        if self.config.metrics_collection_interval_seconds <= 0:
            issues.append("Metrics collection interval must be positive")
        
        return issues
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for monitoring."""
        return {
            "thresholds": self.get_threshold_config(),
            "notifications": self.get_notification_config(),
            "throttling": self.get_throttling_config(),
            "debug": self.get_debug_config(),
            "validation_issues": self.validate_config()
        }


# Global configuration manager instance
config_manager = AlertConfigManager()


def get_alert_config() -> AlertConfig:
    """Get the global alert configuration."""
    return config_manager.get_config()


def get_threshold_config() -> Dict[str, Any]:
    """Get threshold configuration."""
    return config_manager.get_threshold_config()


def get_notification_config() -> Dict[str, Any]:
    """Get notification configuration."""
    return config_manager.get_notification_config()


def validate_alert_config() -> List[str]:
    """Validate alert configuration."""
    return config_manager.validate_config()


def get_config_summary() -> Dict[str, Any]:
    """Get configuration summary."""
    return config_manager.get_config_summary()
