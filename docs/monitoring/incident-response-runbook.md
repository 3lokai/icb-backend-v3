# Incident Response Runbook

This runbook provides comprehensive procedures for handling incidents in the coffee scraper system, including classification, escalation, communication, and recovery procedures.

## Incident Classification

### Critical (P0) - Immediate Response Required
- **System Down**: Complete service unavailability
- **Data Loss**: Any data corruption or loss
- **Security Breach**: Unauthorized access or data exposure
- **Database Failure**: Complete database unavailability
- **High RPC Error Rate**: >50% error rate across all services
- **Disk Usage Critical**: >95% disk usage
- **Memory Exhaustion**: System out of memory

**Response Time**: Immediate (0-15 minutes)
**Escalation**: Immediate to Engineering Manager

### High (P1) - Response Within 30 Minutes
- **Service Degradation**: Significant performance impact
- **Database Connection Issues**: Intermittent connection failures
- **High Error Rate**: 10-50% error rate
- **Memory Usage High**: >90% memory usage
- **Disk Usage Warning**: 85-95% disk usage
- **External Service Failures**: Critical external dependencies down

**Response Time**: 30 minutes
**Escalation**: On-call engineer + Senior Engineer

### Medium (P2) - Response Within 2 Hours
- **Performance Issues**: Slow response times
- **Validation Errors**: High validation failure rate
- **Monitoring Issues**: Alerting or metrics collection problems
- **Resource Constraints**: CPU or memory pressure
- **Data Quality Issues**: Inconsistent or poor data quality

**Response Time**: 2 hours
**Escalation**: On-call engineer

### Low (P3) - Response Within 24 Hours
- **Minor Performance Issues**: Slight degradation
- **Informational Alerts**: System status updates
- **Documentation Issues**: Missing or outdated documentation
- **Feature Requests**: Non-critical enhancements

**Response Time**: 24 hours
**Escalation**: Regular business hours

## Incident Response Procedures

### 1. Initial Response (0-15 minutes)

#### Immediate Actions
1. **Acknowledge the incident** in Slack channel `#coffee-scraper-alerts`
2. **Assess severity** using classification criteria above
3. **Create incident ticket** in GitHub Issues with label `incident`
4. **Notify stakeholders** based on severity level
5. **Begin investigation** using monitoring tools

#### Communication Template
```
🚨 INCIDENT: [Severity] - [Brief Description]
- Incident ID: INC-[YYYYMMDD]-[###]
- Severity: [P0/P1/P2/P3]
- Impact: [User/System Impact Description]
- Status: Investigating
- Owner: [@username]
- ETA: [Initial assessment time]
```

### 2. Investigation Phase (15-60 minutes)

#### Critical/High Severity Investigation
1. **Check system status**:
   ```bash
   # Check service status
   systemctl status coffee-scraper
   
   # Check database connectivity
   psql -d coffee_scraper -c "SELECT 1;"
   
   # Check system resources
   htop
   df -h
   free -h
   ```

2. **Review monitoring dashboards**:
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090
   - Sentry: https://sentry.io/projects/[project]

3. **Check logs for errors**:
   ```bash
   # Application logs
   tail -f /var/log/coffee-scraper/*.log
   
   # System logs
   journalctl -u coffee-scraper -f
   
   # Database logs
   sudo journalctl -u postgresql -f
   ```

4. **Verify external dependencies**:
   ```bash
   # Check external API connectivity
   curl -f https://api.external-service.com/health
   
   # Check network connectivity
   ping external-service.com
   ```

#### Medium/Low Severity Investigation
1. **Review metrics and alerts**
2. **Check recent deployments**
3. **Analyze error patterns**
4. **Document findings**

### 3. Resolution Phase (30 minutes - 4 hours)

#### Immediate Resolution Actions
1. **Implement workarounds** if available
2. **Restart services** if appropriate
3. **Scale resources** if needed
4. **Implement circuit breakers** for external services

#### Service Restart Procedures
```bash
# Restart application services
sudo systemctl restart coffee-scraper

# Restart database if needed
sudo systemctl restart postgresql

# Restart monitoring services
sudo systemctl restart prometheus
sudo systemctl restart grafana-server
```

#### Database Recovery Procedures
```bash
# Check database status
sudo systemctl status postgresql

# Check database logs
sudo journalctl -u postgresql -f

# Test database connectivity
psql -h localhost -U postgres -d coffee_scraper -c "SELECT 1;"

# Check connection pool
netstat -an | grep :5432

# Restart database if needed
sudo systemctl restart postgresql
```

#### Resource Management
```bash
# Check disk usage
df -h
du -sh /*

# Find large files
find / -type f -size +100M 2>/dev/null

# Clean up temporary files
rm -rf /tmp/coffee-scraper-*

# Check memory usage
free -h
ps aux --sort=-%mem | head -10
```

### 4. Communication and Updates

#### Status Update Template (Every 15 minutes for P0/P1)
```
📊 Status Update: INC-[YYYYMMDD]-[###]
- Current Status: [Investigating/Working/Resolved]
- Actions Taken: [List of actions taken]
- Next Steps: [Planned actions]
- ETA: [Updated resolution time]
- Owner: [@username]
```

#### Resolution Notification
```
✅ RESOLVED: INC-[YYYYMMDD]-[###]
- Root Cause: [Brief description of cause]
- Resolution: [Solution implemented]
- Prevention: [Preventive measures taken]
- Duration: [Total incident duration]
- Owner: [@username]
```

## Escalation Procedures

### Level 1: On-Call Engineer (0-30 minutes)
- **Responsibilities**: Initial response, basic troubleshooting
- **Tools**: Monitoring dashboards, logs, basic commands
- **Escalation**: If unable to resolve within 30 minutes

### Level 2: Senior Engineer (30-60 minutes)
- **Responsibilities**: Deep investigation, complex troubleshooting
- **Tools**: Advanced debugging, system architecture analysis
- **Escalation**: If incident persists beyond 60 minutes

### Level 3: Engineering Manager (60+ minutes)
- **Responsibilities**: Incident coordination, resource allocation
- **Tools**: Team coordination, external vendor contact
- **Escalation**: If incident impacts business operations

### Level 4: CTO/Leadership (2+ hours)
- **Responsibilities**: Business impact assessment, external communication
- **Tools**: Stakeholder communication, business continuity planning

## Emergency Contacts

### Primary On-Call
- **Name**: System Owner
- **Phone**: +91 7042683727
- **Slack**: @system-owner
- **Email**: gta3lok.ai@gmail.com

### Secondary On-Call
- **Name**: System Owner (Backup)
- **Phone**: +91 7042683727
- **Slack**: @system-owner
- **Email**: gta3lok.ai@gmail.com

### Engineering Manager
- **Name**: System Owner
- **Phone**: +91 7042683727
- **Slack**: @system-owner
- **Email**: gta3lok.ai@gmail.com

### Escalation Contacts
- **CTO**: System Owner - +91 7042683727
- **DevOps Lead**: System Owner - +91 7042683727
- **Database Admin**: System Owner - +91 7042683727

## Post-Incident Procedures

### 1. Immediate Actions (0-1 hour)
- [ ] Verify system is fully operational
- [ ] Check all services are healthy
- [ ] Monitor for recurrence
- [ ] Update status page if applicable
- [ ] Notify stakeholders of resolution

### 2. Documentation (1-24 hours)
- [ ] Document incident details in GitHub issue
- [ ] Record timeline of events
- [ ] Identify root cause
- [ ] Document resolution steps
- [ ] Update runbooks if needed

### 3. Post-Mortem (1-7 days)
- [ ] Schedule post-mortem meeting
- [ ] Review incident timeline
- [ ] Identify improvement opportunities
- [ ] Update procedures and runbooks
- [ ] Implement preventive measures

### 4. Follow-up Actions (1-30 days)
- [ ] Implement preventive measures
- [ ] Update monitoring thresholds
- [ ] Improve alerting rules
- [ ] Train team on new procedures
- [ ] Review and update documentation

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
- [ ] Practice incident response procedures
- [ ] Test escalation procedures
- [ ] Familiarize with tools and systems
- [ ] Participate in incident simulations

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
