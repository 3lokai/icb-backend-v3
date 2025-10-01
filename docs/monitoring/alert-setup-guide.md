# Alert System Setup Guide

This guide provides comprehensive instructions for setting up the error reporting and alerting system with Sentry integration and Slack notifications.

## Overview

The alert system provides:
- **Sentry Integration**: Comprehensive error tracking for all pipeline components
- **Slack Alerts**: Real-time notifications for threshold breaches and system failures
- **Threshold Monitoring**: Automated detection of review rate spikes, RPC errors, and system issues
- **Alert Throttling**: Prevents notification spam with intelligent cooldown periods

## Prerequisites

- Python 3.8+
- Access to Sentry.io account (free tier available)
- Slack workspace with webhook permissions
- Existing G.1 monitoring infrastructure

## Configuration

### Environment Variables

Add the following environment variables to your `.env` file:

```bash
# Sentry Configuration
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_ALERTS_ENABLED=true

# Alert Thresholds (optional - defaults provided)
ALERT_REVIEW_RATE_THRESHOLD=50.0
ALERT_RPC_ERROR_THRESHOLD=10.0
ALERT_SYSTEM_HEALTH_THRESHOLD=30.0
ALERT_FETCH_LATENCY_THRESHOLD=60.0
ALERT_VALIDATION_ERROR_THRESHOLD=20.0
ALERT_DATABASE_FAILURE_THRESHOLD=5.0
ALERT_MEMORY_USAGE_THRESHOLD=85.0
ALERT_DISK_USAGE_THRESHOLD=90.0

# Alert Cooldowns (minutes)
ALERT_REVIEW_RATE_COOLDOWN=10
ALERT_RPC_ERROR_COOLDOWN=5
ALERT_SYSTEM_HEALTH_COOLDOWN=5
ALERT_FETCH_LATENCY_COOLDOWN=15
ALERT_VALIDATION_ERROR_COOLDOWN=10
ALERT_DATABASE_FAILURE_COOLDOWN=5
ALERT_MEMORY_USAGE_COOLDOWN=30
ALERT_DISK_USAGE_COOLDOWN=15

# Alert Throttling
ALERT_THROTTLE_WINDOW=300
ALERT_MAX_PER_WINDOW=10

# Monitoring Intervals
ALERT_CHECK_INTERVAL=60
METRICS_COLLECTION_INTERVAL=30

# Debug Settings
ALERT_DEBUG_MODE=false
ALERT_LOG_ATTEMPTS=true
```

### Sentry Setup

1. **Create Sentry Account**:
   - Go to [sentry.io](https://sentry.io) and create a free account
   - Create a new project for your coffee scraper
   - Copy the DSN from project settings

2. **Configure Sentry DSN**:
   ```bash
   export SENTRY_DSN="https://your-dsn@sentry.io/project-id"
   ```

3. **Set Environment**:
   ```bash
   export SENTRY_ENVIRONMENT="production"  # or "development", "staging"
   ```

### Slack Setup

1. **Create Slack App**:
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Click "Create New App" → "From scratch"
   - Name your app (e.g., "Coffee Scraper Alerts")
   - Select your workspace

2. **Enable Incoming Webhooks**:
   - Go to "Features" → "Incoming Webhooks"
   - Toggle "Activate Incoming Webhooks" to On
   - Click "Add New Webhook to Workspace"
   - Choose the channel for alerts (e.g., #alerts, #monitoring)
   - Copy the webhook URL

3. **Configure Webhook URL**:
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
   ```

## Usage

### Basic Setup

```python
from src.monitoring.alert_service import ComprehensiveAlertService
from src.monitoring.threshold_monitoring import ThresholdMonitoringService
from src.monitoring.pipeline_metrics import PipelineMetrics
from src.monitoring.database_metrics import DatabaseMetrics

# Initialize services
pipeline_metrics = PipelineMetrics()
database_metrics = DatabaseMetrics()

alert_service = ComprehensiveAlertService(
    slack_webhook_url="your-slack-webhook-url",
    sentry_dsn="your-sentry-dsn",
    metrics=pipeline_metrics
)

monitoring_service = ThresholdMonitoringService(
    pipeline_metrics=pipeline_metrics,
    database_metrics=database_metrics,
    alert_service=alert_service
)
```

### Error Capture

```python
from src.monitoring.sentry_integration import SentryIntegration

sentry = SentryIntegration(
    dsn="your-sentry-dsn",
    environment="production"
)

# Capture pipeline errors
try:
    # Your pipeline code
    pass
except Exception as e:
    sentry.capture_pipeline_error(
        error=e,
        component="normalizer",
        operation="parse_artifact",
        artifact_id="artifact_123",
        pipeline_state={"step": "validation", "status": "failed"},
        user_info={"user_id": "admin"}
    )

# Capture LLM errors
try:
    # LLM enrichment code
    pass
except Exception as e:
    sentry.capture_llm_error(
        error=e,
        artifact_id="artifact_123",
        llm_provider="deepseek",
        model="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=50,
        cost=0.001
    )
```

### Threshold Monitoring

```python
# Check all thresholds
breaches = await monitoring_service.check_all_thresholds()

# Process breaches
if breaches:
    await monitoring_service.process_threshold_breaches(breaches)
```

### Manual Alerts

```python
# Send system failure alert
await alert_service.send_system_failure_alert(
    component="database",
    failure_type="connection_timeout",
    error_message="Database connection failed after 30s timeout",
    system_state={"cpu_usage": 95.0, "memory_usage": 90.0}
)

# Send review rate spike alert
await alert_service.send_review_rate_spike_alert(
    roaster_id="test_roaster",
    platform="shopify",
    current_rate=75.0,
    baseline_rate=50.0,
    increase_percent=50.0
)
```

## Alert Types

### Threshold Breaches

The system monitors the following thresholds:

1. **Review Rate Spike** (>50% increase)
   - Severity: Warning
   - Cooldown: 10 minutes
   - Component: Normalizer

2. **RPC Error Rate** (>10% error rate)
   - Severity: Critical
   - Cooldown: 5 minutes
   - Component: Database

3. **System Health** (<30% health score)
   - Severity: Critical
   - Cooldown: 5 minutes
   - Component: System

4. **Fetch Latency** (>60 seconds)
   - Severity: Warning
   - Cooldown: 15 minutes
   - Component: Fetcher

5. **Validation Error Rate** (>20% error rate)
   - Severity: Warning
   - Cooldown: 10 minutes
   - Component: Validator

6. **Database Failures** (>5 failures)
   - Severity: Critical
   - Cooldown: 5 minutes
   - Component: Database

7. **Memory Usage** (>85% usage)
   - Severity: Warning
   - Cooldown: 30 minutes
   - Component: System

8. **Disk Usage** (>90% usage)
   - Severity: Critical
   - Cooldown: 15 minutes
   - Component: System

### Alert Severity Levels

- **Info**: Informational messages (green)
- **Warning**: Non-critical issues (yellow)
- **Critical**: System failures requiring immediate attention (red)

## Alert Throttling

The system includes intelligent throttling to prevent notification spam:

- **Throttle Window**: 5 minutes (configurable)
- **Max Alerts per Window**: 10 alerts (configurable)
- **Per-Rule Cooldowns**: Individual cooldown periods for each threshold
- **Alert Escalation**: Critical alerts can be escalated after delay

## Monitoring Dashboard

### Slack Channel Setup

1. Create a dedicated channel for alerts (e.g., `#coffee-scraper-alerts`)
2. Add the webhook to this channel
3. Configure channel notifications for critical alerts
4. Set up channel topics and descriptions

### Sentry Dashboard

1. Access your Sentry project dashboard
2. Configure alert rules in Sentry for additional filtering
3. Set up issue tracking and assignment
4. Configure release tracking for deployments

## Troubleshooting

### Common Issues

1. **Slack Webhook Not Working**:
   - Verify webhook URL is correct
   - Check Slack app permissions
   - Ensure webhook is enabled

2. **Sentry Not Capturing Errors**:
   - Verify DSN is correct
   - Check Sentry project settings
   - Ensure environment variables are set

3. **Alerts Not Triggering**:
   - Check threshold values
   - Verify metrics are being collected
   - Check cooldown periods

4. **Too Many Alerts**:
   - Adjust throttle settings
   - Increase cooldown periods
   - Review threshold values

### Debug Mode

Enable debug mode for troubleshooting:

```bash
export ALERT_DEBUG_MODE=true
export ALERT_LOG_ATTEMPTS=true
```

This will log all alert attempts and provide detailed debugging information.

## Performance Considerations

### Resource Usage

- **Memory**: Minimal overhead (~10MB for alert service)
- **CPU**: Low impact with async processing
- **Network**: Efficient batching of alerts
- **Storage**: No persistent storage required

### Scaling

- **Horizontal**: Multiple instances can share the same Slack webhook
- **Vertical**: Increase throttle limits for high-volume systems
- **Geographic**: Use region-specific Sentry projects for global deployments

## Security

### Webhook Security

- Use HTTPS for all webhook URLs
- Rotate webhook URLs periodically
- Monitor webhook usage in Slack

### Sentry Security

- Use environment-specific DSNs
- Configure Sentry data scrubbing
- Set up proper access controls

### Data Privacy

- No sensitive data is sent to Slack
- Sentry data is scrubbed of PII
- All communications use HTTPS

## Maintenance

### Regular Tasks

1. **Monitor Alert Volume**: Check for alert fatigue
2. **Review Thresholds**: Adjust based on system behavior
3. **Update Cooldowns**: Optimize based on alert patterns
4. **Clean Up Sentry**: Archive resolved issues

### Health Checks

```python
# Check alert service status
status = alert_service.get_alert_status()
print(f"Active alerts: {status['alert_throttle']['active_alerts']}")
print(f"Slack configured: {status['clients']['slack_configured']}")
print(f"Sentry configured: {status['clients']['sentry_configured']}")

# Check monitoring service status
monitoring_status = monitoring_service.get_monitoring_status()
print(f"Thresholds configured: {monitoring_status['thresholds_configured']}")
print(f"Active cooldowns: {monitoring_status['active_cooldowns']}")
```

## Support

For issues with the alert system:

1. Check the logs for error messages
2. Verify configuration settings
3. Test webhook connectivity
4. Review Sentry dashboard for errors
5. Contact the development team with specific error messages

## Cost Optimization

### Free Tier Limits

- **Sentry**: 5,000 errors/month (free tier)
- **Slack**: 10,000 message history (free tier)
- **Monitoring**: Self-hosted Prometheus/Grafana

### Optimization Strategies

1. **Error Sampling**: Use Sentry sampling rates
2. **Alert Filtering**: Filter out non-critical alerts
3. **Batch Processing**: Group similar alerts
4. **Smart Throttling**: Reduce alert frequency for known issues

### Upgrade Paths

- **Sentry Pro**: For higher error volumes
- **Slack Pro**: For advanced integrations
- **Cloud Monitoring**: For managed Prometheus/Grafana
