# Grafana Cloud Setup Guide for G.1 Monitoring

## Overview

This guide helps you set up monitoring for your icb-backend using **Grafana Cloud** services, as configured in your `env.example`.

## Prerequisites

- ✅ Grafana Cloud account (free tier available)
- ✅ Prometheus metrics endpoint running on port 8000
- ✅ Environment variables configured in `.env`

## Step 1: Grafana Cloud Configuration

### 1.1 Get Your Grafana Cloud Credentials

1. **Log into Grafana Cloud**: https://grafana.com/
2. **Go to your stack**: Click on your stack name
3. **Get your credentials**:
   - **Grafana URL**: `https://your-instance.grafana.net`
   - **API Key**: Go to "API Keys" → Create new key
   - **Prometheus URL**: Go to "Prometheus" → Copy the remote write URL
   - **Prometheus Username/Password**: From your stack details

### 1.2 Update Your Environment Variables

Update your `.env` file with your actual Grafana Cloud credentials:

```bash
# Grafana Configuration (G.1) - Cloud Services
GRAFANA_CLOUD_ENABLED=true
GRAFANA_CLOUD_URL=https://your-actual-instance.grafana.net
GRAFANA_CLOUD_API_KEY=your_actual_grafana_api_key
GRAFANA_CLOUD_PROMETHEUS_URL=https://your-actual-instance.grafana.net/api/prom/push
GRAFANA_CLOUD_PROMETHEUS_USERNAME=your_actual_prometheus_username
GRAFANA_CLOUD_PROMETHEUS_PASSWORD=your_actual_prometheus_password
```

## Step 2: Configure Prometheus Remote Write

### 2.1 Create Prometheus Configuration

Create `prometheus.yml` for remote write to Grafana Cloud:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

remote_write:
  - url: ${GRAFANA_CLOUD_PROMETHEUS_URL}
    basic_auth:
      username: ${GRAFANA_CLOUD_PROMETHEUS_USERNAME}
      password: ${GRAFANA_CLOUD_PROMETHEUS_PASSWORD}

scrape_configs:
  - job_name: 'icb-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### 2.2 Test Prometheus Connection

```bash
# Test your metrics endpoint
curl http://localhost:8000/metrics

# Test remote write (if you have promtool)
promtool remote-write test prometheus.yml
```

## Step 3: Configure Grafana Dashboards

### 3.1 Import G.1 Dashboards

The G.1 story includes programmatic dashboard configuration. Let me create the import script:

```python
# dashboard_importer.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def import_dashboards():
    """Import G.1 dashboards to Grafana Cloud."""
    
    grafana_url = os.getenv("GRAFANA_CLOUD_URL")
    api_key = os.getenv("GRAFANA_CLOUD_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Import pipeline overview dashboard
    pipeline_dashboard = {
        "dashboard": {
            "title": "ICB-Backend Pipeline Overview",
            "panels": [
                {
                    "title": "Pipeline Health Score",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "icb_pipeline_health_score",
                            "refId": "A"
                        }
                    ]
                },
                {
                    "title": "Fetch Latency",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(icb_fetch_latency_seconds_sum[5m])",
                            "refId": "A"
                        }
                    ]
                }
            ]
        }
    }
    
    response = requests.post(
        f"{grafana_url}/api/dashboards/db",
        json=pipeline_dashboard,
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ Pipeline dashboard imported successfully!")
    else:
        print(f"❌ Failed to import dashboard: {response.text}")

if __name__ == "__main__":
    import_dashboards()
```

## Step 4: Start Your Monitoring Stack

### 4.1 Start Your Application with Metrics

```bash
# Start your icb-backend with metrics enabled
export PROMETHEUS_ENABLED=true
export PROMETHEUS_PORT=8000
python -m src.main
```

### 4.2 Verify Metrics Collection

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics | grep icb_

# Check specific metrics
curl http://localhost:8000/metrics | grep -E "(pipeline_health|fetch_latency|artifact_count)"
```

## Step 5: Configure Grafana Data Source

### 5.1 Add Prometheus Data Source

1. **Go to Grafana**: Your Grafana Cloud URL
2. **Configuration** → **Data Sources** → **Add data source**
3. **Select Prometheus**
4. **Configure**:
   - **URL**: `https://your-instance.grafana.net/api/prom`
   - **Access**: Server (default)
   - **Auth**: Enable basic auth with your credentials

### 5.2 Test Data Source

1. **Click "Save & Test"**
2. **Verify**: Should show "Data source is working"

## Step 6: Import G.1 Dashboards

### 6.1 Pipeline Overview Dashboard

```json
{
  "dashboard": {
    "title": "ICB-Backend Pipeline Overview",
    "panels": [
      {
        "title": "Pipeline Health Score",
        "type": "stat",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [
          {
            "expr": "icb_pipeline_health_score",
            "refId": "A"
          }
        ]
      },
      {
        "title": "Fetch Operations",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [
          {
            "expr": "rate(icb_fetch_operations_total[5m])",
            "refId": "A"
          }
        ]
      }
    ]
  }
}
```

### 6.2 Database Health Dashboard

```json
{
  "dashboard": {
    "title": "ICB-Backend Database Health",
    "panels": [
      {
        "title": "Database Connection Health",
        "type": "stat",
        "targets": [
          {
            "expr": "icb_database_health_score",
            "refId": "A"
          }
        ]
      },
      {
        "title": "Query Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(icb_database_queries_total[5m])",
            "refId": "A"
          }
        ]
      }
    ]
  }
}
```

## Step 7: Set Up Alerting

### 7.1 Configure Alert Rules

In Grafana Cloud:

1. **Go to Alerting** → **Alert Rules**
2. **Create new rule**:
   - **Name**: "ICB Pipeline Health Critical"
   - **Query**: `icb_pipeline_health_score < 50`
   - **Condition**: `IS BELOW 50`
   - **Notification**: Send to your Slack webhook

### 7.2 Test Alerting

```bash
# Trigger a test alert by setting health score low
curl -X POST http://localhost:8000/metrics \
  -d "icb_pipeline_health_score 25"
```

## Step 8: Verify Complete Setup

### 8.1 Check Metrics Flow

```bash
# 1. Verify metrics are being collected
curl http://localhost:8000/metrics | grep icb_

# 2. Check Grafana Cloud is receiving data
# Go to Grafana → Explore → Query: icb_pipeline_health_score

# 3. Verify dashboards are populated
# Go to your dashboards and check for data
```

### 8.2 Test Complete Pipeline

```bash
# Run a test pipeline operation
python -m src.monitoring.test_metrics_export

# Check metrics updated
curl http://localhost:8000/metrics | grep -E "(pipeline|database|fetch)"
```

## Troubleshooting

### Common Issues

1. **No metrics in Grafana**:
   - Check Prometheus remote write configuration
   - Verify credentials in `.env`
   - Check network connectivity to Grafana Cloud

2. **Dashboards not loading**:
   - Verify data source configuration
   - Check metric names match your application
   - Ensure metrics are being sent to Grafana Cloud

3. **Alerts not firing**:
   - Check alert rule configuration
   - Verify notification channels
   - Test with manual metric updates

### Debug Commands

```bash
# Check if metrics endpoint is working
curl -v http://localhost:8000/metrics

# Check specific metrics
curl http://localhost:8000/metrics | grep -E "(icb_|pipeline|database)"

# Test Grafana Cloud connection
curl -u $GRAFANA_CLOUD_PROMETHEUS_USERNAME:$GRAFANA_CLOUD_PROMETHEUS_PASSWORD \
  $GRAFANA_CLOUD_PROMETHEUS_URL/api/v1/query?query=up
```

## Next Steps

1. **Monitor your dashboards** for real pipeline data
2. **Set up additional alert rules** for critical thresholds
3. **Configure notification channels** for Slack integration
4. **Review and optimize** based on actual usage patterns

Your icb-backend monitoring is now ready for production! 🚀
