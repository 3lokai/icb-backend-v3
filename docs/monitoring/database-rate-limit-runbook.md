# Database Rate-Limit Handling Runbook

This runbook provides comprehensive procedures for detecting, responding to, and managing database rate-limit issues in the coffee scraper system.

## Rate-Limit Detection

### Monitoring Metrics
The system monitors the following database metrics for rate-limit detection:

- **Connection Pool Exhaustion**: When connection pool reaches maximum capacity
- **Query Timeout Rate**: Percentage of queries timing out
- **RPC Rate Limits**: Supabase RPC call rate limits
- **Database Response Time**: Average response time for database queries
- **Connection Errors**: Number of connection failures per minute

### Alert Thresholds
- **Critical**: Connection pool >90% utilized, >10% query timeouts
- **Warning**: Connection pool >75% utilized, >5% query timeouts
- **Info**: Connection pool >50% utilized, response time >1s

## Rate-Limit Response Procedures

### 1. Immediate Detection (0-5 minutes)

#### Check Database Status
```bash
# Check database service status
sudo systemctl status postgresql

# Check database logs for rate-limit errors
sudo journalctl -u postgresql -f | grep -i "rate\|limit\|timeout"

# Check connection pool status
netstat -an | grep :5432 | wc -l

# Check active connections
psql -d coffee_scraper -c "SELECT count(*) FROM pg_stat_activity;"
```

#### Check Application Metrics
```bash
# Check application metrics
curl http://localhost:8000/metrics | grep -E "(db_|connection|timeout)"

# Check application logs for database errors
tail -f /var/log/coffee-scraper/*.log | grep -i "database\|connection\|timeout"
```

### 2. Immediate Response (5-15 minutes)

#### Connection Pool Management
```bash
# Check current connection pool settings
grep -r "pool" src/config/
grep -r "connection" src/config/

# Check for connection leaks
ps aux | grep coffee-scraper
lsof | grep coffee-scraper | grep -E "(postgres|5432)"

# Restart application to reset connection pool
sudo systemctl restart coffee-scraper
```

#### Database Optimization
```bash
# Check database performance
psql -d coffee_scraper -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Check for long-running queries
psql -d coffee_scraper -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"

# Check database locks
psql -d coffee_scraper -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

### 3. Rate-Limit Mitigation (15-30 minutes)

#### Implement Connection Pooling
```python
# Example connection pool configuration
DATABASE_CONFIG = {
    "pool_size": 10,  # Reduce from default if needed
    "max_overflow": 5,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}
```

#### Implement Retry Logic
```python
# Example retry logic for database operations
import time
from functools import wraps

def retry_db_operation(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except DatabaseError as e:
                    if "rate limit" in str(e).lower() or "timeout" in str(e).lower():
                        if attempt < max_retries - 1:
                            time.sleep(delay * (2 ** attempt))  # Exponential backoff
                            continue
                    raise
            return None
        return wrapper
    return decorator
```

#### Implement Circuit Breaker Pattern
```python
# Example circuit breaker for database operations
class DatabaseCircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise
```

### 4. Database Performance Tuning (30-60 minutes)

#### Connection Pool Optimization
```bash
# Check current connection pool configuration
grep -r "pool" src/config/

# Update connection pool settings
# Edit src/config/database_config.py
```

#### Database Configuration Tuning
```sql
-- Check current database configuration
SELECT name, setting, unit, context FROM pg_settings WHERE name LIKE '%connection%';

-- Optimize connection settings
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Reload configuration
SELECT pg_reload_conf();
```

#### Query Optimization
```sql
-- Check for slow queries
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public' 
AND n_distinct > 100 
AND correlation < 0.1;

-- Analyze table statistics
ANALYZE;
```

### 5. Monitoring and Alerting (Ongoing)

#### Set Up Rate-Limit Monitoring
```python
# Example monitoring configuration
RATE_LIMIT_MONITORING = {
    "connection_pool_threshold": 0.8,  # 80% of pool capacity
    "query_timeout_threshold": 0.05,   # 5% timeout rate
    "response_time_threshold": 2.0,    # 2 seconds average response time
    "alert_cooldown": 300              # 5 minutes between alerts
}
```

#### Implement Health Checks
```python
# Example health check for database
async def check_database_health():
    try:
        # Test basic connectivity
        result = await supabase_client.table('scrape_runs').select('id').limit(1).execute()
        
        # Check connection pool status
        pool_status = get_connection_pool_status()
        
        # Check response time
        start_time = time.time()
        await supabase_client.table('scrape_runs').select('count').execute()
        response_time = time.time() - start_time
        
        return {
            "status": "healthy",
            "response_time": response_time,
            "pool_status": pool_status
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## Recovery Procedures

### 1. Connection Pool Exhaustion Recovery
```bash
# Check for connection leaks
ps aux | grep coffee-scraper
lsof | grep coffee-scraper | grep postgres

# Kill leaked connections if necessary
sudo pkill -f "coffee-scraper"

# Restart application
sudo systemctl restart coffee-scraper

# Verify connection pool is healthy
netstat -an | grep :5432 | wc -l
```

### 2. Database Performance Recovery
```bash
# Check for long-running queries
psql -d coffee_scraper -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"

# Kill problematic queries if necessary
psql -d coffee_scraper -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = [PROBLEMATIC_PID];"

# Restart database if necessary
sudo systemctl restart postgresql
```

### 3. RPC Rate-Limit Recovery
```bash
# Check RPC rate limits
curl -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
     "https://your-project.supabase.co/rest/v1/scrape_runs?select=count"

# Implement exponential backoff
# Update src/config/supabase_config.py
```

## Prevention Strategies

### 1. Connection Pool Management
- **Regular Monitoring**: Monitor connection pool usage continuously
- **Pool Sizing**: Size connection pool appropriately for workload
- **Connection Leak Detection**: Implement connection leak detection
- **Pool Health Checks**: Regular health checks for connection pool

### 2. Query Optimization
- **Index Optimization**: Ensure proper indexes on frequently queried columns
- **Query Analysis**: Regular analysis of slow queries
- **Query Caching**: Implement query result caching where appropriate
- **Batch Operations**: Use batch operations instead of individual queries

### 3. Rate-Limit Management
- **Request Throttling**: Implement request throttling for external APIs
- **Exponential Backoff**: Use exponential backoff for retry logic
- **Circuit Breakers**: Implement circuit breakers for external services
- **Load Balancing**: Distribute load across multiple database connections

### 4. Monitoring and Alerting
- **Proactive Monitoring**: Set up proactive monitoring for rate-limit indicators
- **Alert Thresholds**: Configure appropriate alert thresholds
- **Dashboard Monitoring**: Use dashboards to monitor database health
- **Log Analysis**: Regular analysis of database logs for issues

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Connection Pool Exhaustion
**Symptoms**: Database connection errors, application timeouts
**Solution**: 
1. Check for connection leaks
2. Restart application
3. Optimize connection pool settings
4. Implement connection leak detection

#### Issue: Query Timeouts
**Symptoms**: Slow database responses, application timeouts
**Solution**:
1. Optimize slow queries
2. Add appropriate indexes
3. Increase query timeout settings
4. Implement query caching

#### Issue: RPC Rate Limits
**Symptoms**: Supabase RPC errors, API rate limit errors
**Solution**:
1. Implement exponential backoff
2. Reduce request frequency
3. Use batch operations
4. Implement circuit breakers

#### Issue: Database Performance Degradation
**Symptoms**: Slow overall system performance, high response times
**Solution**:
1. Check for long-running queries
2. Optimize database configuration
3. Add database indexes
4. Implement query optimization

## Emergency Contacts

### Database Issues
- **Primary DBA**: [Name] - [Phone] - [Slack]
- **Secondary DBA**: [Name] - [Phone] - [Slack]
- **Database Vendor**: Supabase Support

### Application Issues
- **Primary Developer**: [Name] - [Phone] - [Slack]
- **Secondary Developer**: [Name] - [Phone] - [Slack]

### Infrastructure Issues
- **DevOps Lead**: [Name] - [Phone] - [Slack]
- **Infrastructure Team**: [Name] - [Phone] - [Slack]

## Tools and Resources

### Monitoring Tools
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Database Metrics**: `src/monitoring/database_metrics.py`

### Configuration Files
- **Database Config**: `src/config/database_config.py`
- **Supabase Config**: `src/config/supabase_config.py`
- **Monitoring Config**: `src/monitoring/alert_config.py`

### Useful Commands
```bash
# Check database status
sudo systemctl status postgresql

# Check connection pool
netstat -an | grep :5432

# Check database performance
psql -d coffee_scraper -c "SELECT * FROM pg_stat_activity;"

# Check slow queries
psql -d coffee_scraper -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Restart database
sudo systemctl restart postgresql

# Restart application
sudo systemctl restart coffee-scraper
```
