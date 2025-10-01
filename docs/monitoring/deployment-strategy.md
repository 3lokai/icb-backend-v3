# Monitoring Deployment Strategy

## 🏗️ **Local Development vs Production Deployment**

### **Local Development (Your Machine)**

**When to run monitoring scripts:**
- ✅ **During development** - Test monitoring setup
- ✅ **Debugging** - Verify metrics collection
- ✅ **Dashboard testing** - Import and configure dashboards

**Scripts to run locally:**
```bash
# Test your monitoring setup
python scripts/test_monitoring_setup.py

# Import dashboards to Grafana Cloud
python scripts/import_grafana_dashboards.py

# Start metrics server for testing
python scripts/start_monitoring.py
```

### **Production Deployment (Fly.io)**

**What runs automatically:**
- ✅ **Metrics collection** - Built into your application
- ✅ **Prometheus export** - Automatic on port 8000
- ✅ **Grafana Cloud integration** - Automatic remote write
- ✅ **Alerting** - Automatic threshold monitoring

**What you configure once:**
- ✅ **Grafana Cloud credentials** - Set in Fly.io secrets
- ✅ **Dashboard import** - Run once during deployment
- ✅ **Alert rules** - Configure in Grafana Cloud

## 🚀 **Fly.io Deployment Configuration**

### **1. Fly.io Secrets (Environment Variables)**

```bash
# Set your Grafana Cloud credentials in Fly.io
fly secrets set GRAFANA_CLOUD_URL=https://your-instance.grafana.net
fly secrets set GRAFANA_CLOUD_API_KEY=your_api_key
fly secrets set GRAFANA_CLOUD_PROMETHEUS_URL=https://your-instance.grafana.net/api/prom/push
fly secrets set GRAFANA_CLOUD_PROMETHEUS_USERNAME=your_username
fly secrets set GRAFANA_CLOUD_PROMETHEUS_PASSWORD=your_password
```

### **2. Fly.io Configuration (fly.toml)**

```toml
# Add to your fly.toml
[metrics]
  port = 8000
  path = "/metrics"

[env]
  PROMETHEUS_ENABLED = "true"
  PROMETHEUS_PORT = "8000"
  GRAFANA_CLOUD_ENABLED = "true"
```

### **3. Deployment Script**

Create `scripts/deploy_monitoring.py`:

```python
#!/usr/bin/env python3
"""
Deploy Monitoring to Fly.io

This script handles monitoring deployment to Fly.io.
"""

import os
import subprocess
import sys
from dotenv import load_dotenv

def deploy_to_fly():
    """Deploy monitoring configuration to Fly.io."""
    print("🚀 Deploying monitoring to Fly.io...")
    
    # Check if we're in production
    if os.getenv("FLY_APP_NAME"):
        print("✅ Running on Fly.io - deploying monitoring...")
        
        # Import dashboards to Grafana Cloud
        print("📊 Importing dashboards...")
        subprocess.run([sys.executable, "scripts/import_grafana_dashboards.py"])
        
        print("✅ Monitoring deployed to Fly.io!")
        return True
    else:
        print("ℹ️  Not running on Fly.io - skipping deployment")
        return True

if __name__ == "__main__":
    deploy_to_fly()
```

## 📋 **Deployment Timeline**

### **Phase 1: Local Development**
```bash
# 1. Set up Grafana Cloud account
# 2. Configure .env with credentials
# 3. Test monitoring locally
python scripts/test_monitoring_setup.py

# 4. Import dashboards
python scripts/import_grafana_dashboards.py
```

### **Phase 2: Fly.io Deployment**
```bash
# 1. Set Fly.io secrets
fly secrets set GRAFANA_CLOUD_URL=...
fly secrets set GRAFANA_CLOUD_API_KEY=...

# 2. Deploy your application
fly deploy

# 3. Import dashboards (one-time)
fly ssh console
python scripts/import_grafana_dashboards.py
```

### **Phase 3: Production Monitoring**
- ✅ **Automatic metrics collection** from your application
- ✅ **Real-time dashboards** in Grafana Cloud
- ✅ **Automatic alerting** via Slack/Sentry
- ✅ **No additional scripts needed**

## 🔄 **What Runs When**

### **Local Development:**
- 🧪 **Test scripts** - Run manually for testing
- 📊 **Dashboard import** - Run once to set up
- 🔍 **Metrics server** - Run for development testing

### **Production (Fly.io):**
- ✅ **Metrics collection** - Automatic (built into app)
- ✅ **Grafana Cloud** - Automatic (via environment variables)
- ✅ **Alerting** - Automatic (via G.2 implementation)
- ❌ **No scripts needed** - Everything runs automatically

## 🎯 **Recommended Approach**

### **For Development:**
1. **Set up locally** using the quick-start guide
2. **Test everything** works with your application
3. **Import dashboards** to your Grafana Cloud
4. **Verify metrics** are flowing correctly

### **For Production:**
1. **Set Fly.io secrets** with your Grafana Cloud credentials
2. **Deploy your application** (monitoring is built-in)
3. **Import dashboards once** (they persist in Grafana Cloud)
4. **Monitor via Grafana Cloud** (no additional setup needed)

## 💡 **Key Benefits**

- ✅ **No overlap** with Fly.io's basic monitoring
- ✅ **Enhanced observability** beyond system metrics
- ✅ **Automatic in production** - no manual intervention
- ✅ **Business-specific metrics** for coffee scraping pipeline
- ✅ **Professional alerting** via Slack/Sentry integration

Your monitoring setup **enhances** Fly.io's capabilities rather than replacing them!
