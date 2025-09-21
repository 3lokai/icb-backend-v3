# 5. Operational Policies

### 5.1 Concurrency & Rate Limiting
- **Per-Roaster Concurrency**: Default 3 workers (configurable)
- **Domain Delays**: 250ms ± 100ms jitter, respect robots.txt crawl-delay
- **Retry Policy**: 5 retries with exponential backoff
- **Permanent Failures**: 4xx errors logged to manual review queue

### 5.2 Data Retention & Cleanup
- **Raw Artifacts**: 90 days retention (configurable)
- **Price Time-Series**: Retained forever or per policy
- **Image Backups**: S3 with lifecycle rules and versioning
- **Database Backups**: Periodic snapshots from Supabase

### 5.3 Error Handling & Monitoring
- **Alert Thresholds**: >5% failures per run OR per-roaster repeat failures
- **Manual Review**: Artifacts with parsing warnings or confidence issues
- **Metrics**: Requests/sec, errors, queue length, per-roaster failure rate
- **Logging**: Structured logs to external provider (Papertrail, Datadog)
