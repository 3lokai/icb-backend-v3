# Quick Start Guide: G.1 Monitoring Setup

## 🚀 **Get Your Monitoring Running in 5 Minutes**

### **Step 1: Update Your .env File**

Add your Grafana Cloud credentials to your `.env` file:

```bash
# Get these from your Grafana Cloud dashboard
GRAFANA_CLOUD_URL=https://your-instance.grafana.net
GRAFANA_CLOUD_API_KEY=your_grafana_api_key
GRAFANA_CLOUD_PROMETHEUS_URL=https://your-instance.grafana.net/api/prom/push
GRAFANA_CLOUD_PROMETHEUS_USERNAME=your_prometheus_username
GRAFANA_CLOUD_PROMETHEUS_PASSWORD=your_prometheus_password
```

### **Step 2: Start Your Monitoring Stack**

```bash
# Start the complete monitoring stack
python scripts/start_monitoring.py
```

This will:
- ✅ Start your metrics server on port 8000
- ✅ Import G.1 dashboards to Grafana Cloud
- ✅ Test the complete setup
- ✅ Show you useful URLs

### **Step 3: Verify Everything is Working**

```bash
# Test your monitoring setup
python scripts/test_monitoring_setup.py
```

### **Step 4: Check Your Dashboards**

1. **Go to your Grafana Cloud URL**
2. **Look for these dashboards:**
   - 📊 **ICB-Backend Pipeline Overview**
   - 🗄️ **ICB-Backend Database Health** 
   - ☕ **ICB-Backend Roaster Monitoring**

### **Step 5: Start Your Application**

```bash
# Start your icb-backend with monitoring enabled
export PROMETHEUS_ENABLED=true
python -m src.main
```

## 🔍 **What You'll See**

### **In Grafana Cloud:**
- **Real-time pipeline health scores**
- **Fetch operation rates and latency**
- **Database query performance**
- **Roaster-specific metrics**
- **Error rates and success rates**

### **In Your Application:**
- **Metrics endpoint**: http://localhost:8000/metrics
- **Health endpoint**: http://localhost:8000/health
- **Automatic metrics collection** from all pipeline operations

## 🛠️ **Troubleshooting**

### **No Data in Grafana?**
```bash
# Check if metrics are being collected
curl http://localhost:8000/metrics | grep icb_

# Check if your app is running
curl http://localhost:8000/health
```

### **Dashboard Import Failed?**
```bash
# Re-import dashboards manually
python scripts/import_grafana_dashboards.py
```

### **Connection Issues?**
```bash
# Test your Grafana Cloud connection
python scripts/test_monitoring_setup.py
```

## 📊 **Available Dashboards**

### **1. Pipeline Overview**
- Pipeline health score
- Fetch operations rate
- Artifact count
- Review rate
- Database queries

### **2. Database Health**
- Database health score
- Query performance
- Connection pool status
- Table sizes
- Query duration

### **3. Roaster Monitoring**
- Roaster performance
- Price updates
- Data quality score
- Error rates by roaster

## 🚨 **Setting Up Alerts**

### **In Grafana Cloud:**
1. **Go to Alerting** → **Alert Rules**
2. **Create new rule**:
   - **Name**: "Pipeline Health Critical"
   - **Query**: `icb_pipeline_health_score < 50`
   - **Condition**: `IS BELOW 50`
   - **Notification**: Send to Slack (if configured)

### **Test Your Alerts:**
```bash
# Generate test metrics to trigger alerts
python scripts/test_monitoring_setup.py
```

## 🎯 **Next Steps**

1. **Monitor your dashboards** for real pipeline data
2. **Set up additional alert rules** for critical thresholds
3. **Customize dashboards** for your specific needs
4. **Configure notification channels** for Slack integration

## 📚 **Additional Resources**

- **Full Setup Guide**: `docs/monitoring/grafana-cloud-setup.md`
- **G.1 Story**: `docs/stories/G.1.metrics-exporter-dashboards.md`
- **Alert Setup**: `docs/monitoring/alert-setup-guide.md`

---

**🎉 Your icb-backend monitoring is now ready for production!**
