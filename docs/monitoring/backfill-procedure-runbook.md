# Backfill Procedure Runbook

This runbook provides comprehensive procedures for data recovery, pipeline restart, and backfill operations in the coffee scraper system.

## Backfill Scenarios

### 1. Data Loss Recovery
- **Partial Data Loss**: Missing data for specific time periods
- **Complete Data Loss**: Loss of all data for a roaster or time period
- **Corrupted Data**: Data integrity issues requiring re-processing
- **Schema Changes**: Data structure changes requiring re-processing

### 2. Pipeline Restart Scenarios
- **System Failure**: Complete system failure requiring restart
- **Service Restart**: Individual service restart with data recovery
- **Deployment Issues**: Failed deployments requiring rollback and recovery
- **Configuration Changes**: Configuration changes requiring data re-processing

### 3. Data Quality Issues
- **Validation Failures**: Data failing validation requiring re-processing
- **Parsing Errors**: Data parsing errors requiring re-processing
- **External API Issues**: External API failures requiring re-fetching
- **Rate Limit Issues**: Rate limit issues requiring delayed re-processing

## Backfill Procedures

### 1. Pre-Backfill Assessment (0-30 minutes)

#### Data Assessment
```bash
# Check current data status
psql -d coffee_scraper -c "SELECT COUNT(*) FROM scrape_runs;"
psql -d coffee_scraper -c "SELECT COUNT(*) FROM scrape_artifacts;"
psql -d coffee_scraper -c "SELECT COUNT(*) FROM prices;"
psql -d coffee_scraper -c "SELECT COUNT(*) FROM variants;"

# Check data quality
psql -d coffee_scraper -c "SELECT status, COUNT(*) FROM scrape_runs GROUP BY status;"
psql -d coffee_scraper -c "SELECT validation_status, COUNT(*) FROM scrape_artifacts GROUP BY validation_status;"

# Check recent data
psql -d coffee_scraper -c "SELECT * FROM scrape_runs ORDER BY created_at DESC LIMIT 10;"
```

#### System Assessment
```bash
# Check system resources
df -h
free -h
htop

# Check service status
systemctl status coffee-scraper
systemctl status postgresql

# Check disk space for backfill
du -sh /var/log/coffee-scraper/
du -sh /tmp/
```

#### Identify Backfill Scope
```bash
# Identify missing data periods
psql -d coffee_scraper -c "SELECT roaster_id, MIN(created_at), MAX(created_at) FROM scrape_runs GROUP BY roaster_id;"

# Check for data gaps
psql -d coffee_scraper -c "SELECT roaster_id, DATE(created_at) as date, COUNT(*) FROM scrape_runs GROUP BY roaster_id, DATE(created_at) ORDER BY roaster_id, date;"
```

### 2. Backfill Planning (30-60 minutes)

#### Determine Backfill Strategy
- **Incremental Backfill**: Process only missing or failed data
- **Full Backfill**: Re-process all data for a specific period
- **Selective Backfill**: Re-process specific roasters or data types
- **Validation Backfill**: Re-validate existing data

#### Estimate Backfill Time
```python
# Example backfill time estimation
def estimate_backfill_time(roaster_count, days_to_backfill, avg_processing_time):
    """
    Estimate backfill time based on:
    - Number of roasters
    - Days to backfill
    - Average processing time per roaster per day
    """
    total_roasters = roaster_count
    total_days = days_to_backfill
    avg_time_per_roaster_per_day = avg_processing_time  # in minutes
    
    estimated_time = total_roasters * total_days * avg_time_per_roaster_per_day
    return estimated_time
```

#### Resource Planning
- **Disk Space**: Ensure sufficient disk space for backfill data
- **Memory**: Ensure sufficient memory for processing
- **Network**: Ensure stable network connection for external APIs
- **Database**: Ensure database can handle increased load

### 3. Incremental Backfill Procedure (1-4 hours)

#### Step 1: Identify Missing Data
```bash
# Create backfill script
cat > backfill_script.py << 'EOF'
import asyncio
from datetime import datetime, timedelta
from src.fetcher.fetcher_service import FetcherService
from src.parser.normalizer_pipeline import NormalizerPipeline
from src.validator.integration_service import IntegrationService

async def identify_missing_data(roaster_id, start_date, end_date):
    """Identify missing data for backfill"""
    # Check scrape_runs for missing periods
    # Check scrape_artifacts for failed processing
    # Check prices for missing data
    pass

async def incremental_backfill(roaster_id, start_date, end_date):
    """Perform incremental backfill for specific roaster and date range"""
    # 1. Identify missing data
    missing_data = await identify_missing_data(roaster_id, start_date, end_date)
    
    # 2. Fetch missing data
    fetcher = FetcherService()
    artifacts = await fetcher.fetch_missing_data(roaster_id, missing_data)
    
    # 3. Process artifacts
    normalizer = NormalizerPipeline()
    processed_data = await normalizer.process_artifacts(artifacts)
    
    # 4. Validate and store data
    validator = IntegrationService()
    await validator.validate_and_store(processed_data)
    
    return processed_data

if __name__ == "__main__":
    # Example usage
    asyncio.run(incremental_backfill("roaster1", "2024-01-01", "2024-01-31"))
EOF
```

#### Step 2: Execute Incremental Backfill
```bash
# Run incremental backfill
python backfill_script.py

# Monitor progress
tail -f /var/log/coffee-scraper/backfill.log

# Check database for new data
psql -d coffee_scraper -c "SELECT COUNT(*) FROM scrape_runs WHERE created_at > NOW() - INTERVAL '1 hour';"
```

#### Step 3: Validate Backfill Results
```bash
# Check data quality
psql -d coffee_scraper -c "SELECT validation_status, COUNT(*) FROM scrape_artifacts WHERE created_at > NOW() - INTERVAL '1 hour' GROUP BY validation_status;"

# Check processing status
psql -d coffee_scraper -c "SELECT status, COUNT(*) FROM scrape_runs WHERE created_at > NOW() - INTERVAL '1 hour' GROUP BY status;"

# Check for errors
grep -i "error\|exception" /var/log/coffee-scraper/backfill.log
```

### 4. Full Backfill Procedure (4-24 hours)

#### Step 1: Prepare for Full Backfill
```bash
# Create backup of current data
pg_dump coffee_scraper > backup_$(date +%Y%m%d_%H%M%S).sql

# Check disk space
df -h

# Stop normal processing
sudo systemctl stop coffee-scraper
```

#### Step 2: Execute Full Backfill
```python
# Full backfill script
cat > full_backfill_script.py << 'EOF'
import asyncio
from datetime import datetime, timedelta
from src.fetcher.fetcher_service import FetcherService
from src.parser.normalizer_pipeline import NormalizerPipeline
from src.validator.integration_service import IntegrationService

async def full_backfill(roaster_id, start_date, end_date):
    """Perform full backfill for specific roaster and date range"""
    # 1. Clear existing data for the period
    await clear_existing_data(roaster_id, start_date, end_date)
    
    # 2. Fetch all data for the period
    fetcher = FetcherService()
    artifacts = await fetcher.fetch_all_data(roaster_id, start_date, end_date)
    
    # 3. Process all artifacts
    normalizer = NormalizerPipeline()
    processed_data = await normalizer.process_artifacts(artifacts)
    
    # 4. Validate and store all data
    validator = IntegrationService()
    await validator.validate_and_store(processed_data)
    
    return processed_data

async def clear_existing_data(roaster_id, start_date, end_date):
    """Clear existing data for the period"""
    # Clear scrape_runs
    # Clear scrape_artifacts
    # Clear prices
    # Clear variants
    pass

if __name__ == "__main__":
    # Example usage
    asyncio.run(full_backfill("roaster1", "2024-01-01", "2024-01-31"))
EOF
```

#### Step 3: Monitor Full Backfill
```bash
# Monitor progress
tail -f /var/log/coffee-scraper/backfill.log

# Check system resources
htop
df -h

# Check database performance
psql -d coffee_scraper -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

#### Step 4: Validate Full Backfill
```bash
# Check data completeness
psql -d coffee_scraper -c "SELECT roaster_id, COUNT(*) FROM scrape_runs GROUP BY roaster_id;"
psql -d coffee_scraper -c "SELECT roaster_id, COUNT(*) FROM scrape_artifacts GROUP BY roaster_id;"
psql -d coffee_scraper -c "SELECT roaster_id, COUNT(*) FROM prices GROUP BY roaster_id;"

# Check data quality
psql -d coffee_scraper -c "SELECT validation_status, COUNT(*) FROM scrape_artifacts GROUP BY validation_status;"

# Check for errors
grep -i "error\|exception" /var/log/coffee-scraper/backfill.log
```

### 5. Pipeline Restart Procedures (30 minutes - 2 hours)

#### Step 1: Stop Current Processing
```bash
# Stop all services
sudo systemctl stop coffee-scraper

# Check for running processes
ps aux | grep coffee-scraper

# Kill any remaining processes
sudo pkill -f coffee-scraper
```

#### Step 2: Clear Failed Data
```bash
# Clear failed scrape runs
psql -d coffee_scraper -c "DELETE FROM scrape_runs WHERE status = 'fail';"

# Clear failed artifacts
psql -d coffee_scraper -c "DELETE FROM scrape_artifacts WHERE validation_status = 'invalid';"

# Clear orphaned data
psql -d coffee_scraper -c "DELETE FROM prices WHERE variant_id NOT IN (SELECT id FROM variants);"
```

#### Step 3: Restart Services
```bash
# Start database
sudo systemctl start postgresql

# Start application
sudo systemctl start coffee-scraper

# Check service status
systemctl status coffee-scraper
systemctl status postgresql
```

#### Step 4: Verify Restart
```bash
# Check service health
curl -f http://localhost:8000/health

# Check database connectivity
psql -d coffee_scraper -c "SELECT 1;"

# Check processing status
psql -d coffee_scraper -c "SELECT status, COUNT(*) FROM scrape_runs GROUP BY status;"
```

### 6. Data Validation and Integrity Checking

#### Data Validation Procedures
```python
# Data validation script
cat > data_validation_script.py << 'EOF'
import asyncio
from src.validator.integration_service import IntegrationService

async def validate_data_integrity():
    """Validate data integrity after backfill"""
    validator = IntegrationService()
    
    # 1. Validate scrape_runs
    runs_validation = await validator.validate_scrape_runs()
    
    # 2. Validate scrape_artifacts
    artifacts_validation = await validator.validate_scrape_artifacts()
    
    # 3. Validate prices
    prices_validation = await validator.validate_prices()
    
    # 4. Validate variants
    variants_validation = await validator.validate_variants()
    
    # 5. Check referential integrity
    referential_integrity = await validator.check_referential_integrity()
    
    return {
        "runs": runs_validation,
        "artifacts": artifacts_validation,
        "prices": prices_validation,
        "variants": variants_validation,
        "referential_integrity": referential_integrity
    }

if __name__ == "__main__":
    asyncio.run(validate_data_integrity())
EOF
```

#### Integrity Checking
```bash
# Run data validation
python data_validation_script.py

# Check for data inconsistencies
psql -d coffee_scraper -c "SELECT COUNT(*) FROM prices WHERE variant_id NOT IN (SELECT id FROM variants);"
psql -d coffee_scraper -c "SELECT COUNT(*) FROM variants WHERE roaster_id NOT IN (SELECT id FROM roasters);"

# Check for duplicate data
psql -d coffee_scraper -c "SELECT variant_id, scraped_at, COUNT(*) FROM prices GROUP BY variant_id, scraped_at HAVING COUNT(*) > 1;"
```

## Monitoring and Progress Tracking

### 1. Backfill Progress Monitoring
```python
# Progress monitoring script
cat > backfill_monitoring.py << 'EOF'
import asyncio
import time
from datetime import datetime

class BackfillMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.total_items = 0
        self.processed_items = 0
        self.failed_items = 0
    
    def update_progress(self, processed, failed):
        self.processed_items = processed
        self.failed_items = failed
        
        # Calculate progress percentage
        progress = (processed / self.total_items * 100) if self.total_items > 0 else 0
        
        # Calculate estimated time remaining
        elapsed_time = time.time() - self.start_time
        if processed > 0:
            estimated_total_time = elapsed_time * (self.total_items / processed)
            remaining_time = estimated_total_time - elapsed_time
        else:
            remaining_time = 0
        
        # Log progress
        print(f"Progress: {progress:.1f}% ({processed}/{self.total_items})")
        print(f"Failed: {failed}")
        print(f"Elapsed: {elapsed_time:.1f}s")
        print(f"Remaining: {remaining_time:.1f}s")
        
        return {
            "progress": progress,
            "processed": processed,
            "failed": failed,
            "elapsed_time": elapsed_time,
            "remaining_time": remaining_time
        }

# Usage
monitor = BackfillMonitor()
monitor.total_items = 1000
monitor.update_progress(100, 5)
EOF
```

### 2. Real-time Monitoring
```bash
# Monitor backfill progress
tail -f /var/log/coffee-scraper/backfill.log | grep -E "(progress|error|completed)"

# Monitor database activity
psql -d coffee_scraper -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Monitor system resources
htop
df -h
```

## Recovery Procedures

### 1. Backfill Failure Recovery
```bash
# Check for backfill failures
grep -i "error\|exception\|failed" /var/log/coffee-scraper/backfill.log

# Check database for partial data
psql -d coffee_scraper -c "SELECT COUNT(*) FROM scrape_runs WHERE created_at > NOW() - INTERVAL '1 hour';"

# Clean up partial data if necessary
psql -d coffee_scraper -c "DELETE FROM scrape_runs WHERE created_at > NOW() - INTERVAL '1 hour' AND status = 'fail';"

# Restart backfill from last successful point
python backfill_script.py --resume
```

### 2. System Recovery
```bash
# Check system status
systemctl status coffee-scraper
systemctl status postgresql

# Check system resources
df -h
free -h

# Restart services if necessary
sudo systemctl restart coffee-scraper
sudo systemctl restart postgresql
```

### 3. Data Recovery
```bash
# Restore from backup if necessary
psql -d coffee_scraper < backup_$(date +%Y%m%d_%H%M%S).sql

# Verify data integrity
python data_validation_script.py
```

## Prevention Strategies

### 1. Regular Backups
```bash
# Daily backup script
cat > daily_backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump coffee_scraper > $BACKUP_DIR/backup_$DATE.sql
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
EOF

chmod +x daily_backup.sh
```

### 2. Monitoring and Alerting
```python
# Backfill monitoring configuration
BACKFILL_MONITORING = {
    "progress_check_interval": 300,  # 5 minutes
    "failure_threshold": 0.1,        # 10% failure rate
    "timeout_threshold": 3600,       # 1 hour timeout
    "alert_on_failure": True
}
```

### 3. Data Validation
```python
# Regular data validation
async def regular_data_validation():
    """Perform regular data validation"""
    validator = IntegrationService()
    
    # Check data quality
    quality_check = await validator.check_data_quality()
    
    # Check referential integrity
    integrity_check = await validator.check_referential_integrity()
    
    # Check for missing data
    missing_data_check = await validator.check_missing_data()
    
    return {
        "quality": quality_check,
        "integrity": integrity_check,
        "missing_data": missing_data_check
    }
```

## Emergency Contacts

### Backfill Issues
- **Primary Developer**: [Name] - [Phone] - [Slack]
- **Secondary Developer**: [Name] - [Phone] - [Slack]
- **Database Admin**: [Name] - [Phone] - [Slack]

### Data Recovery
- **Data Engineer**: [Name] - [Phone] - [Slack]
- **Database Admin**: [Name] - [Phone] - [Slack]
- **Backup Admin**: [Name] - [Phone] - [Slack]

## Tools and Resources

### Backfill Tools
- **Backfill Scripts**: `scripts/backfill/`
- **Data Validation**: `src/validator/integration_service.py`
- **Monitoring**: `src/monitoring/database_metrics.py`

### Configuration Files
- **Database Config**: `src/config/database_config.py`
- **Fetcher Config**: `src/config/fetcher_config.py`
- **Parser Config**: `src/config/parser_config.py`

### Useful Commands
```bash
# Check data status
psql -d coffee_scraper -c "SELECT COUNT(*) FROM scrape_runs;"

# Check data quality
psql -d coffee_scraper -c "SELECT validation_status, COUNT(*) FROM scrape_artifacts GROUP BY validation_status;"

# Monitor backfill progress
tail -f /var/log/coffee-scraper/backfill.log

# Check system resources
htop
df -h

# Restart services
sudo systemctl restart coffee-scraper
```
