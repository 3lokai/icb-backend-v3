# Troubleshooting Guide

This comprehensive troubleshooting guide covers common issues, resolution procedures, and optimization techniques for the coffee scraper system.

## Common Pipeline Failures

### 1. Fetcher Service Issues

#### Issue: External API Failures
**Symptoms**: 
- High fetch latency (>60s)
- HTTP 4xx/5xx errors
- Network timeout errors
- Rate limiting errors

**Diagnosis**:
```bash
# Check fetcher logs
tail -f /var/log/coffee-scraper/fetcher.log

# Check network connectivity
ping external-service.com
curl -w "@curl-format.txt" -o /dev/null -s "https://external-service.com/api"

# Check for rate limiting
grep "rate limit" /var/log/coffee-scraper/fetcher.log
```

**Resolution**:
```bash
# 1. Check external service status
curl -f https://external-service.com/health

# 2. Implement retry logic
python -c "
from src.fetcher.fetcher_service import FetcherService
fetcher = FetcherService()
fetcher.enable_retry_logic = True
fetcher.max_retries = 3
fetcher.retry_delay = 5
"

# 3. Implement circuit breaker
python -c "
from src.fetcher.fetcher_service import FetcherService
fetcher = FetcherService()
fetcher.enable_circuit_breaker = True
fetcher.failure_threshold = 5
fetcher.timeout = 30
"

# 4. Check rate limiting
grep "rate limit" /var/log/coffee-scraper/fetcher.log
```

#### Issue: Data Quality Problems
**Symptoms**:
- Invalid artifacts
- Parsing errors
- Data validation failures
- Inconsistent data formats

**Diagnosis**:
```bash
# Check artifact validation
psql -d coffee_scraper -c "SELECT validation_status, COUNT(*) FROM scrape_artifacts GROUP BY validation_status;"

# Check parsing errors
grep "parsing error" /var/log/coffee-scraper/parser.log

# Check data quality
psql -d coffee_scraper -c "SELECT platform, COUNT(*) FROM scrape_artifacts GROUP BY platform;"
```

**Resolution**:
```bash
# 1. Update parsing rules
python -c "
from src.parser.normalizer_pipeline import NormalizerPipeline
pipeline = NormalizerPipeline()
pipeline.update_parsing_rules()
"

# 2. Re-validate artifacts
python -c "
from src.validator.integration_service import IntegrationService
validator = IntegrationService()
validator.revalidate_artifacts()
"

# 3. Check data quality
psql -d coffee_scraper -c "SELECT * FROM scrape_artifacts WHERE validation_status = 'invalid' LIMIT 10;"
```

### 2. Database Connectivity Issues

#### Issue: Connection Pool Exhaustion
**Symptoms**:
- Database connection errors
- Application timeouts
- High connection count
- Connection pool full errors

**Diagnosis**:
```bash
# Check connection pool status
netstat -an | grep :5432 | wc -l

# Check active connections
psql -d coffee_scraper -c "SELECT count(*) FROM pg_stat_activity;"

# Check connection errors
grep "connection" /var/log/coffee-scraper/*.log
```

**Resolution**:
```bash
# 1. Check for connection leaks
ps aux | grep coffee-scraper
lsof | grep coffee-scraper | grep postgres

# 2. Restart application
sudo systemctl restart coffee-scraper

# 3. Check connection pool settings
grep -r "pool" src/config/

# 4. Optimize connection pool
python -c "
from src.config.database_config import DatabaseConfig
config = DatabaseConfig()
config.pool_size = 10
config.max_overflow = 5
config.pool_timeout = 30
config.save_config()
"
```

#### Issue: Database Performance Issues
**Symptoms**:
- Slow database queries
- High response times
- Database locks
- Query timeouts

**Diagnosis**:
```bash
# Check slow queries
psql -d coffee_scraper -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check active queries
psql -d coffee_scraper -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Check database locks
psql -d coffee_scraper -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

**Resolution**:
```bash
# 1. Kill problematic queries
psql -d coffee_scraper -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = [PROBLEMATIC_PID];"

# 2. Add database indexes
psql -d coffee_scraper -c "CREATE INDEX CONCURRENTLY idx_scrape_runs_created_at ON scrape_runs(created_at);"

# 3. Optimize database configuration
psql -d coffee_scraper -c "ALTER SYSTEM SET shared_buffers = '256MB';"
psql -d coffee_scraper -c "ALTER SYSTEM SET effective_cache_size = '1GB';"
psql -d coffee_scraper -c "SELECT pg_reload_conf();"

# 4. Analyze table statistics
psql -d coffee_scraper -c "ANALYZE;"
```

### 3. External API Failures and Timeouts

#### Issue: API Rate Limiting
**Symptoms**:
- HTTP 429 errors
- Rate limit exceeded messages
- API quota exceeded
- Service unavailable errors

**Diagnosis**:
```bash
# Check API rate limits
grep "rate limit" /var/log/coffee-scraper/*.log

# Check API quotas
curl -H "Authorization: Bearer $API_KEY" "https://api.service.com/usage"

# Check request frequency
curl http://localhost:8000/metrics | grep -E "(api_|rate_)"
```

**Resolution**:
```bash
# 1. Implement exponential backoff
python -c "
from src.fetcher.fetcher_service import FetcherService
fetcher = FetcherService()
fetcher.enable_exponential_backoff = True
fetcher.max_retries = 5
fetcher.base_delay = 1
fetcher.max_delay = 60
"

# 2. Implement request throttling
python -c "
from src.fetcher.fetcher_service import FetcherService
fetcher = FetcherService()
fetcher.enable_request_throttling = True
fetcher.requests_per_minute = 30
fetcher.requests_per_hour = 1000
"

# 3. Implement circuit breaker
python -c "
from src.fetcher.fetcher_service import FetcherService
fetcher = FetcherService()
fetcher.enable_circuit_breaker = True
fetcher.failure_threshold = 5
fetcher.recovery_timeout = 300
"
```

#### Issue: API Timeouts
**Symptoms**:
- Request timeout errors
- Connection timeout errors
- Slow API responses
- Service unavailable errors

**Diagnosis**:
```bash
# Check timeout errors
grep "timeout" /var/log/coffee-scraper/*.log

# Check network connectivity
ping api.service.com
curl -w "@curl-format.txt" -o /dev/null -s "https://api.service.com/health"

# Check DNS resolution
nslookup api.service.com
```

**Resolution**:
```bash
# 1. Increase timeout settings
python -c "
from src.config.fetcher_config import FetcherConfig
config = FetcherConfig()
config.timeout = 60
config.connection_timeout = 30
config.read_timeout = 30
config.save_config()
"

# 2. Implement retry logic
python -c "
from src.fetcher.fetcher_service import FetcherService
fetcher = FetcherService()
fetcher.enable_retry_logic = True
fetcher.max_retries = 3
fetcher.retry_delay = 5
"

# 3. Check network configuration
ip route show
cat /etc/resolv.conf
```

### 4. Performance Troubleshooting and Optimization

#### Issue: High Memory Usage
**Symptoms**:
- Memory usage >90%
- Out of memory errors
- System slowdown
- Memory leaks

**Diagnosis**:
```bash
# Check memory usage
free -h
htop
ps aux --sort=-%mem | head -10

# Check for memory leaks
lsof | grep coffee-scraper
ps aux | grep coffee-scraper
```

**Resolution**:
```bash
# 1. Check for memory leaks
ps aux | grep coffee-scraper
lsof | grep coffee-scraper

# 2. Restart application
sudo systemctl restart coffee-scraper

# 3. Optimize memory usage
python -c "
from src.config.pipeline_config import PipelineConfig
config = PipelineConfig()
config.batch_size = 10
config.max_memory_usage = 0.8
config.enable_memory_monitoring = True
config.save_config()
"

# 4. Check system resources
df -h
free -h
```

#### Issue: High CPU Usage
**Symptoms**:
- CPU usage >90%
- Slow system response
- High load average
- Process CPU spikes

**Diagnosis**:
```bash
# Check CPU usage
htop
top -p $(pgrep coffee-scraper)

# Check load average
uptime
cat /proc/loadavg

# Check process CPU usage
ps aux --sort=-%cpu | head -10
```

**Resolution**:
```bash
# 1. Check for CPU-intensive processes
ps aux --sort=-%cpu | head -10

# 2. Optimize processing
python -c "
from src.config.pipeline_config import PipelineConfig
config = PipelineConfig()
config.enable_parallel_processing = True
config.max_workers = 4
config.enable_cpu_monitoring = True
config.save_config()
"

# 3. Check system load
uptime
cat /proc/loadavg
```

### 5. Data Quality and Validation Issues

#### Issue: Validation Failures
**Symptoms**:
- High validation error rate
- Invalid data in database
- Data quality issues
- Schema validation errors

**Diagnosis**:
```bash
# Check validation errors
psql -d coffee_scraper -c "SELECT validation_status, COUNT(*) FROM scrape_artifacts GROUP BY validation_status;"

# Check validation logs
grep "validation error" /var/log/coffee-scraper/validator.log

# Check data quality
psql -d coffee_scraper -c "SELECT * FROM scrape_artifacts WHERE validation_status = 'invalid' LIMIT 10;"
```

**Resolution**:
```bash
# 1. Update validation rules
python -c "
from src.validator.integration_service import IntegrationService
validator = IntegrationService()
validator.update_validation_rules()
"

# 2. Re-validate data
python -c "
from src.validator.integration_service import IntegrationService
validator = IntegrationService()
validator.revalidate_all_artifacts()
"

# 3. Check schema changes
git log --oneline -10
```

#### Issue: Data Inconsistencies
**Symptoms**:
- Duplicate data
- Missing data
- Inconsistent data formats
- Data integrity issues

**Diagnosis**:
```bash
# Check for duplicates
psql -d coffee_scraper -c "SELECT variant_id, scraped_at, COUNT(*) FROM prices GROUP BY variant_id, scraped_at HAVING COUNT(*) > 1;"

# Check for missing data
psql -d coffee_scraper -c "SELECT COUNT(*) FROM prices WHERE variant_id NOT IN (SELECT id FROM variants);"

# Check data integrity
psql -d coffee_scraper -c "SELECT COUNT(*) FROM variants WHERE roaster_id NOT IN (SELECT id FROM roasters);"
```

**Resolution**:
```bash
# 1. Remove duplicates
psql -d coffee_scraper -c "DELETE FROM prices WHERE id IN (SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY variant_id, scraped_at ORDER BY id) as rn FROM prices) t WHERE rn > 1);"

# 2. Fix referential integrity
psql -d coffee_scraper -c "DELETE FROM prices WHERE variant_id NOT IN (SELECT id FROM variants);"

# 3. Check data consistency
python -c "
from src.validator.integration_service import IntegrationService
validator = IntegrationService()
validator.check_data_consistency()
"
```

### 6. Monitoring and Alerting Issues

#### Issue: Missing Alerts
**Symptoms**:
- No alerts for critical issues
- Alerts not firing
- Alert configuration issues
- Monitoring gaps

**Diagnosis**:
```bash
# Check alert configuration
cat src/monitoring/alert_config.py

# Check alert service status
systemctl status alert-service

# Check alert logs
tail -f /var/log/coffee-scraper/alert.log
```

**Resolution**:
```bash
# 1. Check alert configuration
python -c "
from src.monitoring.alert_service import AlertService
alert_service = AlertService()
alert_service.check_alert_configuration()
"

# 2. Test alert system
python -c "
from src.monitoring.alert_service import AlertService
alert_service = AlertService()
alert_service.test_alert_system()
"

# 3. Restart alert service
sudo systemctl restart alert-service
```

#### Issue: False Alerts
**Symptoms**:
- Too many alerts
- False positive alerts
- Alert noise
- Threshold issues

**Diagnosis**:
```bash
# Check alert frequency
grep "alert" /var/log/coffee-scraper/alert.log | wc -l

# Check alert thresholds
curl http://localhost:8000/metrics | grep -E "(alert_|threshold_)"

# Check alert patterns
grep "alert" /var/log/coffee-scraper/alert.log | tail -20
```

**Resolution**:
```bash
# 1. Adjust alert thresholds
python -c "
from src.monitoring.alert_config import AlertConfig
config = AlertConfig()
config.adjust_alert_thresholds()
config.save_config()
"

# 2. Implement alert cooldown
python -c "
from src.monitoring.alert_service import AlertService
alert_service = AlertService()
alert_service.enable_alert_cooldown = True
alert_service.cooldown_period = 300
"

# 3. Filter false positives
python -c "
from src.monitoring.alert_service import AlertService
alert_service = AlertService()
alert_service.enable_alert_filtering = True
alert_service.filter_false_positives = True
"
```

## Performance Optimization

### 1. Database Optimization
```bash
# Optimize database configuration
psql -d coffee_scraper -c "ALTER SYSTEM SET shared_buffers = '256MB';"
psql -d coffee_scraper -c "ALTER SYSTEM SET effective_cache_size = '1GB';"
psql -d coffee_scraper -c "ALTER SYSTEM SET work_mem = '4MB';"
psql -d coffee_scraper -c "ALTER SYSTEM SET maintenance_work_mem = '64MB';"
psql -d coffee_scraper -c "SELECT pg_reload_conf();"

# Add database indexes
psql -d coffee_scraper -c "CREATE INDEX CONCURRENTLY idx_scrape_runs_created_at ON scrape_runs(created_at);"
psql -d coffee_scraper -c "CREATE INDEX CONCURRENTLY idx_scrape_artifacts_validation_status ON scrape_artifacts(validation_status);"
psql -d coffee_scraper -c "CREATE INDEX CONCURRENTLY idx_prices_variant_id ON prices(variant_id);"

# Analyze table statistics
psql -d coffee_scraper -c "ANALYZE;"
```

### 2. Application Optimization
```bash
# Optimize application configuration
python -c "
from src.config.pipeline_config import PipelineConfig
config = PipelineConfig()
config.enable_parallel_processing = True
config.max_workers = 4
config.batch_size = 20
config.enable_caching = True
config.cache_ttl = 3600
config.save_config()
"

# Optimize memory usage
python -c "
from src.config.pipeline_config import PipelineConfig
config = PipelineConfig()
config.max_memory_usage = 0.8
config.enable_memory_monitoring = True
config.garbage_collection_threshold = 0.7
config.save_config()
"
```

### 3. Network Optimization
```bash
# Optimize network settings
python -c "
from src.config.fetcher_config import FetcherConfig
config = FetcherConfig()
config.connection_pool_size = 10
config.max_connections = 100
config.keep_alive = True
config.timeout = 30
config.save_config()
"

# Implement connection pooling
python -c "
from src.config.database_config import DatabaseConfig
config = DatabaseConfig()
config.pool_size = 10
config.max_overflow = 5
config.pool_timeout = 30
config.pool_recycle = 3600
config.save_config()
"
```

## Emergency Procedures

### 1. System Recovery
```bash
# Check system status
systemctl status coffee-scraper
systemctl status postgresql

# Check system resources
df -h
free -h
htop

# Restart services
sudo systemctl restart coffee-scraper
sudo systemctl restart postgresql
```

### 2. Data Recovery
```bash
# Check data integrity
psql -d coffee_scraper -c "SELECT COUNT(*) FROM scrape_runs;"
psql -d coffee_scraper -c "SELECT COUNT(*) FROM scrape_artifacts;"
psql -d coffee_scraper -c "SELECT COUNT(*) FROM prices;"

# Restore from backup if necessary
psql -d coffee_scraper < backup_$(date +%Y%m%d_%H%M%S).sql

# Verify data recovery
python -c "
from src.validator.integration_service import IntegrationService
validator = IntegrationService()
validator.check_data_integrity()
"
```

### 3. Service Restoration
```bash
# Check service health
curl -f http://localhost:8000/health

# Check database connectivity
psql -d coffee_scraper -c "SELECT 1;"

# Check external API connectivity
curl -f https://api.external-service.com/health

# Restart services if necessary
sudo systemctl restart coffee-scraper
```

## Emergency Contacts

### Technical Issues
- **Primary Developer**: [Name] - [Phone] - [Slack]
- **Secondary Developer**: [Name] - [Phone] - [Slack]
- **Database Admin**: [Name] - [Phone] - [Slack]

### Infrastructure Issues
- **DevOps Lead**: [Name] - [Phone] - [Slack]
- **Infrastructure Team**: [Name] - [Phone] - [Slack]

### External Service Issues
- **API Support**: [Service] Support
- **Vendor Support**: [Vendor] Support

## Tools and Resources

### Monitoring Tools
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Sentry**: https://sentry.io/projects/[project]

### Log Locations
- **Application Logs**: `/var/log/coffee-scraper/`
- **System Logs**: `/var/log/syslog`
- **Database Logs**: `/var/log/postgresql/`

### Configuration Files
- **Alert Config**: `src/monitoring/alert_config.py`
- **Database Config**: `src/config/database_config.py`
- **Fetcher Config**: `src/config/fetcher_config.py`
- **Pipeline Config**: `src/config/pipeline_config.py`

### Useful Commands
```bash
# Check system status
systemctl status coffee-scraper

# View logs
journalctl -u coffee-scraper -f

# Check database
psql -d coffee_scraper -c "SELECT 1;"

# Check metrics
curl http://localhost:8000/metrics

# Restart services
sudo systemctl restart coffee-scraper

# Check system resources
htop
df -h
free -h

# Check network connectivity
ping external-service.com
curl -f https://external-service.com/health
```
