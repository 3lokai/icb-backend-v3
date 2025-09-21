# 10. Monitoring & Observability

### 10.1 Metrics Collection
- **Fetch Metrics**: Requests/sec, latency, success rate per roaster
- **Processing Metrics**: Artifacts processed, parsing warnings count
- **Business Metrics**: Price changes, new products, review queue depth
- **Infrastructure Metrics**: Queue depth, worker health, DB connection pool

### 10.2 Alerting Strategy
- **Critical Alerts**: >5% artifacts flagged for review, DB RPC errors
- **Warning Alerts**: High error volume, queue backup, LLM budget exhausted
- **Info Alerts**: Successful runs, significant price changes
- **Escalation**: Slack notifications, optional PagerDuty integration

### 10.3 Dashboards
- **Operational Dashboard**: Real-time pipeline health, queue status
- **Business Dashboard**: Product counts, price trends, review queue
- **Technical Dashboard**: Error rates, latency, resource utilization
- **Roaster Dashboard**: Per-roaster performance, failure patterns
