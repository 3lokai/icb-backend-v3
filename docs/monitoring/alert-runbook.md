# Alert Response Runbook

This runbook provides step-by-step procedures for responding to different types of alerts from the coffee scraper monitoring system.

## Alert Severity Levels

### Critical (Red) - Immediate Response Required
- System failures
- Database connection failures
- High RPC error rates
- Disk usage >90%
- Any service unavailability

### Warning (Yellow) - Response Within 1 Hour
- Review rate spikes
- High fetch latency
- Validation error rates
- Memory usage >85%
- Performance degradation

### Info (Green) - Monitor and Log
- Normal threshold breaches
- Informational messages
- System status updates

## Critical Alert Response Procedures

### 1. Database Connection Failures

**Alert**: `🚨 CRITICAL: Database connection failures (>5)`

**Immediate Actions**:
1. Check database service status
2. Verify network connectivity
3. Check database logs for errors
4. Verify connection pool settings

**Commands**:
```bash
# Check database status
sudo systemctl status postgresql

# Check database logs
sudo journalctl -u postgresql -f

# Test database connectivity
psql -h localhost -U postgres -d coffee_scraper -c "SELECT 1;"

# Check connection pool
netstat -an | grep :5432
```

**Resolution Steps**:
1. Restart database service if needed
2. Check for disk space issues
3. Verify database configuration
4. Check for connection leaks
5. Update connection pool settings

**Verification**:
- Database queries succeed
- Connection pool is healthy
- No more connection failures

### 2. High RPC Error Rate

**Alert**: `🚨 CRITICAL: RPC error rate exceeded (>10%)`

**Immediate Actions**:
1. Check RPC service status
2. Verify network connectivity
3. Check service logs
4. Monitor error patterns

**Commands**:
```bash
# Check RPC service status
curl -f http://localhost:8000/health

# Check service logs
tail -f /var/log/coffee-scraper/rpc.log

# Check network connectivity
ping rpc-service-host

# Monitor error rates
curl http://localhost:8000/metrics | grep rpc_errors
```

**Resolution Steps**:
1. Restart RPC service if needed
2. Check for network issues
3. Verify service configuration
4. Check for resource constraints
5. Update service dependencies

**Verification**:
- RPC calls succeed
- Error rate drops below threshold
- Service health checks pass

### 3. System Health Degradation

**Alert**: `🚨 CRITICAL: System health degraded (<30%)`

**Immediate Actions**:
1. Check system resources
2. Monitor service status
3. Check for resource leaks
4. Verify system configuration

**Commands**:
```bash
# Check system resources
htop
df -h
free -h

# Check service status
systemctl status coffee-scraper

# Check for resource leaks
ps aux | grep coffee-scraper
lsof | grep coffee-scraper

# Check system logs
journalctl -u coffee-scraper -f
```

**Resolution Steps**:
1. Restart services if needed
2. Free up disk space
3. Increase memory limits
4. Check for memory leaks
5. Optimize resource usage

**Verification**:
- System health score >30%
- All services running
- Resource usage normal

### 4. Disk Usage Critical

**Alert**: `🚨 CRITICAL: High disk usage (>90%)`

**Immediate Actions**:
1. Check disk usage by directory
2. Find large files
3. Clean up temporary files
4. Check log file sizes

**Commands**:
```bash
# Check disk usage
df -h
du -sh /*

# Find large files
find / -type f -size +100M 2>/dev/null

# Check log files
du -sh /var/log/*
ls -la /var/log/coffee-scraper/

# Clean up temporary files
rm -rf /tmp/coffee-scraper-*
```

**Resolution Steps**:
1. Clean up old log files
2. Remove temporary files
3. Archive old data
4. Increase disk space
5. Set up log rotation

**Verification**:
- Disk usage <90%
- System has free space
- Log rotation configured

## Warning Alert Response Procedures

### 1. Review Rate Spike

**Alert**: `📈 WARNING: Review rate spike detected (>50% increase)`

**Investigation Steps**:
1. Check recent pipeline runs
2. Verify data quality
3. Check for parsing issues
4. Monitor artifact processing

**Commands**:
```bash
# Check recent pipeline runs
psql -d coffee_scraper -c "SELECT * FROM scrape_runs ORDER BY created_at DESC LIMIT 10;"

# Check artifact processing
psql -d coffee_scraper -c "SELECT status, COUNT(*) FROM scrape_artifacts GROUP BY status;"

# Check parsing errors
grep "parsing error" /var/log/coffee-scraper/normalizer.log
```

**Resolution Steps**:
1. Investigate parsing issues
2. Check data quality
3. Update parsing rules
4. Monitor for patterns
5. Adjust thresholds if needed

### 2. High Fetch Latency

**Alert**: `📊 WARNING: Fetch latency exceeded (>60s)`

**Investigation Steps**:
1. Check network connectivity
2. Monitor external services
3. Check for rate limiting
4. Verify service performance

**Commands**:
```bash
# Check network connectivity
ping external-service.com
curl -w "@curl-format.txt" -o /dev/null -s "https://external-service.com/api"

# Check for rate limiting
grep "rate limit" /var/log/coffee-scraper/fetcher.log

# Monitor service performance
curl http://localhost:8000/metrics | grep fetch_latency
```

**Resolution Steps**:
1. Check external service status
2. Implement retry logic
3. Add circuit breakers
4. Optimize requests
5. Update timeout settings

### 3. Validation Error Rate

**Alert**: `📊 WARNING: Validation error rate high (>20%)`

**Investigation Steps**:
1. Check validation rules
2. Review data quality
3. Check for schema changes
4. Monitor validation patterns

**Commands**:
```bash
# Check validation errors
grep "validation error" /var/log/coffee-scraper/validator.log

# Check data quality
psql -d coffee_scraper -c "SELECT validation_status, COUNT(*) FROM scrape_artifacts GROUP BY validation_status;"

# Check schema changes
git log --oneline -10
```

**Resolution Steps**:
1. Update validation rules
2. Fix data quality issues
3. Update schema if needed
4. Monitor validation patterns
5. Adjust validation thresholds

## Alert Escalation Procedures

### Level 1: Automated Response (0-15 minutes)
- System automatically retries failed operations
- Alerts are sent to monitoring channel
- Basic health checks are performed

### Level 2: On-Call Engineer (15-30 minutes)
- On-call engineer is notified
- Manual investigation begins
- Basic troubleshooting is performed

### Level 3: Senior Engineer (30-60 minutes)
- Senior engineer is escalated
- Deep investigation begins
- System architecture review

### Level 4: Engineering Manager (60+ minutes)
- Engineering manager is notified
- Incident response team is activated
- Post-mortem planning begins

## Communication Procedures

### Slack Notifications

**Channel**: `#coffee-scraper-alerts`

**Message Format**:
```
🚨 CRITICAL: [Component] - [Issue Description]
- Status: [Current Status]
- Impact: [User Impact]
- ETA: [Resolution Time]
- Owner: [@username]
```

### Status Updates

**Every 15 minutes** during critical incidents:
```
📊 Status Update: [Incident ID]
- Current Status: [Status]
- Actions Taken: [List of actions]
- Next Steps: [Planned actions]
- ETA: [Updated resolution time]
```

### Resolution Notification

**When incident is resolved**:
```
✅ RESOLVED: [Incident ID]
- Root Cause: [Cause]
- Resolution: [Solution]
- Prevention: [Preventive measures]
- Duration: [Total time]
```

## Post-Incident Procedures

### 1. Immediate Actions (0-1 hour)
- [ ] Verify system is fully operational
- [ ] Check all services are healthy
- [ ] Monitor for recurrence
- [ ] Update status page if applicable

### 2. Documentation (1-24 hours)
- [ ] Document incident details
- [ ] Record timeline of events
- [ ] Identify root cause
- [ ] Document resolution steps

### 3. Post-Mortem (1-7 days)
- [ ] Schedule post-mortem meeting
- [ ] Review incident timeline
- [ ] Identify improvement opportunities
- [ ] Update runbooks and procedures

### 4. Follow-up Actions (1-30 days)
- [ ] Implement preventive measures
- [ ] Update monitoring thresholds
- [ ] Improve alerting rules
- [ ] Train team on new procedures

## Preventive Measures

### Daily Checks
- [ ] Review alert volume and patterns
- [ ] Check system health scores
- [ ] Verify monitoring is working
- [ ] Review error rates

### Weekly Checks
- [ ] Review threshold settings
- [ ] Check alert cooldown periods
- [ ] Verify escalation procedures
- [ ] Update runbooks

### Monthly Checks
- [ ] Review incident trends
- [ ] Update alert rules
- [ ] Test escalation procedures
- [ ] Review team training

## Emergency Contacts

### Primary On-Call
- **Name**: [Name]
- **Phone**: [Phone]
- **Slack**: @[username]
- **Email**: [email]

### Secondary On-Call
- **Name**: [Name]
- **Phone**: [Phone]
- **Slack**: @[username]
- **Email**: [email]

### Engineering Manager
- **Name**: [Name]
- **Phone**: [Phone]
- **Slack**: @[username]
- **Email**: [email]

### Escalation Contacts
- **CTO**: [Name] - [Phone]
- **DevOps Lead**: [Name] - [Phone]
- **Database Admin**: [Name] - [Phone]

## Tools and Resources

### Monitoring Dashboards
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Sentry**: https://sentry.io/projects/[project]

### Log Locations
- **Application Logs**: `/var/log/coffee-scraper/`
- **System Logs**: `/var/log/syslog`
- **Database Logs**: `/var/log/postgresql/`

### Configuration Files
- **Alert Config**: `src/monitoring/alert_config.py`
- **Environment**: `.env`
- **Docker Compose**: `docker-compose.yml`

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
```

## Training and Preparation

### New Team Members
- [ ] Review this runbook
- [ ] Practice alert response procedures
- [ ] Test escalation procedures
- [ ] Familiarize with tools and systems

### Regular Training
- [ ] Monthly runbook review
- [ ] Quarterly incident simulation
- [ ] Annual emergency procedures test
- [ ] Continuous improvement of procedures

### Knowledge Sharing
- [ ] Document lessons learned
- [ ] Share incident experiences
- [ ] Update procedures based on experience
- [ ] Train new team members
