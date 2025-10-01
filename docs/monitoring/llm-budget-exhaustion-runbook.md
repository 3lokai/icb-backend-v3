# LLM Budget Exhaustion Runbook

This runbook provides comprehensive procedures for detecting, responding to, and managing LLM budget exhaustion in the coffee scraper system.

## LLM Budget Monitoring

### Current LLM Configuration
The system uses DeepSeek API with the following cost structure:
- **Input tokens**: $0.00027 per 1K tokens
- **Output tokens**: $0.00110 per 1K tokens
- **Rate limits**: 60 requests/minute, 1000 requests/hour, 10000 requests/day

### Budget Monitoring Metrics
- **Daily spend tracking**: Monitor daily LLM costs
- **Token usage**: Track input and output token consumption
- **Request frequency**: Monitor API call frequency
- **Cost per roaster**: Track costs by roaster
- **Budget utilization**: Percentage of budget used

## Budget Exhaustion Detection

### Alert Thresholds
- **Critical**: >90% of daily budget used
- **Warning**: >75% of daily budget used
- **Info**: >50% of daily budget used

### Monitoring Setup
```python
# LLM budget monitoring configuration
LLM_BUDGET_MONITORING = {
    "daily_budget_limit": 100.0,  # $100 daily budget
    "warning_threshold": 0.75,    # 75% of budget
    "critical_threshold": 0.90,   # 90% of budget
    "cost_tracking": True,
    "alert_on_threshold": True
}
```

## Budget Exhaustion Response Procedures

### 1. Immediate Detection (0-5 minutes)

#### Check LLM Usage
```bash
# Check LLM usage logs
tail -f /var/log/coffee-scraper/llm.log | grep -E "(cost|budget|token)"

# Check current spend
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     "https://api.deepseek.com/v1/usage" | jq '.data'

# Check application metrics
curl http://localhost:8000/metrics | grep -E "(llm_|token_|cost_)"
```

#### Check Budget Status
```python
# Budget status check script
cat > check_llm_budget.py << 'EOF'
import asyncio
from datetime import datetime, timedelta
from src.config.llm_config import LLMConfig
from src.monitoring.llm_metrics import LLMMetricsService

async def check_budget_status():
    """Check current LLM budget status"""
    llm_config = LLMConfig()
    metrics_service = LLMMetricsService()
    
    # Get current usage
    current_usage = await metrics_service.get_current_usage()
    daily_limit = llm_config.daily_budget_limit
    
    # Calculate budget utilization
    utilization = (current_usage / daily_limit) * 100
    
    # Check thresholds
    if utilization > 90:
        status = "CRITICAL"
    elif utilization > 75:
        status = "WARNING"
    else:
        status = "OK"
    
    return {
        "status": status,
        "utilization": utilization,
        "current_usage": current_usage,
        "daily_limit": daily_limit,
        "remaining_budget": daily_limit - current_usage
    }

if __name__ == "__main__":
    result = asyncio.run(check_budget_status())
    print(f"Budget Status: {result['status']}")
    print(f"Utilization: {result['utilization']:.1f}%")
    print(f"Remaining Budget: ${result['remaining_budget']:.2f}")
EOF
```

### 2. Immediate Response (5-15 minutes)

#### Implement Rate Limiting
```python
# Emergency rate limiting script
cat > emergency_rate_limit.py << 'EOF'
import asyncio
from src.config.llm_config import LLMConfig

async def implement_emergency_rate_limit():
    """Implement emergency rate limiting"""
    llm_config = LLMConfig()
    
    # Reduce rate limits by 50%
    llm_config.rate_limit_per_minute = llm_config.rate_limit_per_minute // 2
    
    # Disable LLM for non-critical fields
    non_critical_fields = ['notes', 'tags', 'sensory']
    for field in non_critical_fields:
        llm_config.field_configs[field]['enabled'] = False
    
    # Increase confidence thresholds
    for field in llm_config.field_configs:
        current_threshold = llm_config.field_configs[field]['confidence_threshold']
        llm_config.field_configs[field]['confidence_threshold'] = min(0.9, current_threshold + 0.1)
    
    # Save updated configuration
    await llm_config.save_config()
    
    return "Emergency rate limiting implemented"

if __name__ == "__main__":
    asyncio.run(implement_emergency_rate_limit())
EOF
```

#### Disable Non-Critical LLM Processing
```bash
# Disable LLM for non-critical fields
python -c "
from src.config.llm_config import LLMConfig
config = LLMConfig()
config.field_configs['notes']['enabled'] = False
config.field_configs['tags']['enabled'] = False
config.field_configs['sensory']['enabled'] = False
config.save_config()
print('Non-critical LLM processing disabled')
"
```

### 3. Budget Management (15-30 minutes)

#### Implement Cost Controls
```python
# Cost control implementation
cat > implement_cost_controls.py << 'EOF'
import asyncio
from src.config.llm_config import LLMConfig
from src.monitoring.llm_metrics import LLMMetricsService

async def implement_cost_controls():
    """Implement cost control measures"""
    llm_config = LLMConfig()
    metrics_service = LLMMetricsService()
    
    # 1. Reduce batch size to minimize token usage
    llm_config.batch_size = max(1, llm_config.batch_size // 2)
    
    # 2. Increase confidence thresholds to reduce LLM calls
    for field in llm_config.field_configs:
        current_threshold = llm_config.field_configs[field]['confidence_threshold']
        llm_config.field_configs[field]['confidence_threshold'] = min(0.95, current_threshold + 0.05)
    
    # 3. Enable aggressive caching
    llm_config.enable_caching = True
    llm_config.cache_ttl_seconds = 7200  # 2 hours
    
    # 4. Implement request queuing
    llm_config.enable_request_queuing = True
    llm_config.max_queue_size = 100
    
    # 5. Set daily budget limit
    llm_config.daily_budget_limit = 50.0  # Reduce to $50
    
    # Save configuration
    await llm_config.save_config()
    
    return "Cost controls implemented"

if __name__ == "__main__":
    asyncio.run(implement_cost_controls())
EOF
```

#### Implement Budget Alerts
```python
# Budget alert implementation
cat > budget_alerts.py << 'EOF'
import asyncio
from src.monitoring.alert_service import AlertService
from src.monitoring.llm_metrics import LLMMetricsService

async def setup_budget_alerts():
    """Setup budget monitoring alerts"""
    alert_service = AlertService()
    metrics_service = LLMMetricsService()
    
    # Setup budget alerts
    await alert_service.add_alert({
        "name": "llm_budget_warning",
        "condition": "llm_daily_cost > 75.0",
        "severity": "warning",
        "message": "LLM budget at 75% of daily limit"
    })
    
    await alert_service.add_alert({
        "name": "llm_budget_critical",
        "condition": "llm_daily_cost > 90.0",
        "severity": "critical",
        "message": "LLM budget at 90% of daily limit"
    })
    
    await alert_service.add_alert({
        "name": "llm_budget_exhausted",
        "condition": "llm_daily_cost >= 100.0",
        "severity": "critical",
        "message": "LLM budget exhausted - service may be degraded"
    })
    
    return "Budget alerts configured"

if __name__ == "__main__":
    asyncio.run(setup_budget_alerts())
EOF
```

### 4. Service Restoration (30-60 minutes)

#### Implement Fallback Processing
```python
# Fallback processing implementation
cat > implement_fallback.py << 'EOF'
import asyncio
from src.config.llm_config import LLMConfig
from src.parser.deterministic_parser import DeterministicParser

async def implement_fallback_processing():
    """Implement fallback to deterministic processing"""
    llm_config = LLMConfig()
    
    # Enable graceful degradation
    llm_config.enable_graceful_degradation = True
    llm_config.fallback_to_deterministic = True
    
    # Configure fallback thresholds
    llm_config.fallback_threshold = 0.5  # Fallback if confidence < 50%
    
    # Save configuration
    await llm_config.save_config()
    
    # Test fallback processing
    parser = DeterministicParser()
    test_result = await parser.parse_sample_data()
    
    return "Fallback processing implemented and tested"

if __name__ == "__main__":
    asyncio.run(implement_fallback_processing())
EOF
```

#### Implement Budget Reset
```python
# Budget reset implementation
cat > reset_budget.py << 'EOF'
import asyncio
from datetime import datetime, timedelta
from src.monitoring.llm_metrics import LLMMetricsService

async def reset_daily_budget():
    """Reset daily budget at midnight"""
    metrics_service = LLMMetricsService()
    
    # Reset daily counters
    await metrics_service.reset_daily_counters()
    
    # Reset cost tracking
    await metrics_service.reset_cost_tracking()
    
    # Log budget reset
    print(f"Daily budget reset at {datetime.now()}")
    
    return "Daily budget reset completed"

if __name__ == "__main__":
    asyncio.run(reset_daily_budget())
EOF
```

### 5. Long-term Budget Management (1-24 hours)

#### Implement Budget Planning
```python
# Budget planning implementation
cat > budget_planning.py << 'EOF'
import asyncio
from datetime import datetime, timedelta
from src.monitoring.llm_metrics import LLMMetricsService

async def plan_budget_allocation():
    """Plan budget allocation for the day"""
    metrics_service = LLMMetricsService()
    
    # Get historical usage
    historical_usage = await metrics_service.get_historical_usage(days=7)
    
    # Calculate average daily usage
    avg_daily_usage = sum(historical_usage) / len(historical_usage)
    
    # Plan budget allocation
    total_budget = 100.0  # $100 daily budget
    emergency_reserve = 20.0  # $20 emergency reserve
    available_budget = total_budget - emergency_reserve
    
    # Allocate budget by roaster
    roaster_allocation = await metrics_service.get_roaster_usage()
    total_roaster_usage = sum(roaster_allocation.values())
    
    budget_allocation = {}
    for roaster, usage in roaster_allocation.items():
        allocation = (usage / total_roaster_usage) * available_budget
        budget_allocation[roaster] = allocation
    
    return budget_allocation

if __name__ == "__main__":
    allocation = asyncio.run(plan_budget_allocation())
    print("Budget allocation plan:")
    for roaster, budget in allocation.items():
        print(f"  {roaster}: ${budget:.2f}")
EOF
```

#### Implement Cost Optimization
```python
# Cost optimization implementation
cat > optimize_costs.py << 'EOF'
import asyncio
from src.config.llm_config import LLMConfig
from src.monitoring.llm_metrics import LLMMetricsService

async def optimize_llm_costs():
    """Optimize LLM costs through various strategies"""
    llm_config = LLMConfig()
    metrics_service = LLMMetricsService()
    
    # 1. Analyze token usage patterns
    token_usage = await metrics_service.get_token_usage_analysis()
    
    # 2. Optimize prompt engineering
    if token_usage['avg_input_tokens'] > 500:
        # Reduce prompt length
        llm_config.prompt_optimization = True
        llm_config.max_prompt_length = 500
    
    # 3. Implement smart caching
    if token_usage['cache_hit_rate'] < 0.7:
        llm_config.cache_ttl_seconds = 14400  # 4 hours
        llm_config.enable_smart_caching = True
    
    # 4. Batch processing optimization
    if token_usage['batch_efficiency'] < 0.8:
        llm_config.batch_size = min(20, llm_config.batch_size * 2)
        llm_config.enable_batch_optimization = True
    
    # 5. Field-specific optimization
    field_usage = await metrics_service.get_field_usage_analysis()
    for field, usage in field_usage.items():
        if usage['cost_per_request'] > 0.10:  # $0.10 per request
            # Increase confidence threshold for expensive fields
            current_threshold = llm_config.field_configs[field]['confidence_threshold']
            llm_config.field_configs[field]['confidence_threshold'] = min(0.95, current_threshold + 0.05)
    
    # Save optimized configuration
    await llm_config.save_config()
    
    return "Cost optimization completed"

if __name__ == "__main__":
    asyncio.run(optimize_llm_costs())
EOF
```

## Recovery Procedures

### 1. Budget Exhaustion Recovery
```bash
# Check current budget status
python check_llm_budget.py

# Implement emergency measures
python emergency_rate_limit.py

# Check service status
curl -f http://localhost:8000/health

# Monitor LLM usage
tail -f /var/log/coffee-scraper/llm.log
```

### 2. Service Degradation Recovery
```bash
# Check fallback processing
python implement_fallback.py

# Verify deterministic processing
python -c "
from src.parser.deterministic_parser import DeterministicParser
parser = DeterministicParser()
result = parser.parse_sample_data()
print(f'Deterministic processing: {result}')
"

# Check service health
curl http://localhost:8000/metrics | grep -E "(llm_|fallback_)"
```

### 3. Budget Reset Recovery
```bash
# Reset daily budget
python reset_budget.py

# Verify budget reset
python check_llm_budget.py

# Restart LLM services
sudo systemctl restart coffee-scraper
```

## Prevention Strategies

### 1. Proactive Budget Monitoring
```python
# Proactive monitoring setup
cat > setup_proactive_monitoring.py << 'EOF'
import asyncio
from src.monitoring.llm_metrics import LLMMetricsService
from src.monitoring.alert_service import AlertService

async def setup_proactive_monitoring():
    """Setup proactive budget monitoring"""
    metrics_service = LLMMetricsService()
    alert_service = AlertService()
    
    # Setup hourly budget checks
    await metrics_service.schedule_hourly_budget_checks()
    
    # Setup predictive alerts
    await alert_service.add_predictive_alert({
        "name": "llm_budget_prediction",
        "condition": "predicted_daily_cost > 90.0",
        "severity": "warning",
        "message": "Predicted LLM budget exhaustion"
    })
    
    # Setup cost trend analysis
    await metrics_service.enable_cost_trend_analysis()
    
    return "Proactive monitoring setup completed"

if __name__ == "__main__":
    asyncio.run(setup_proactive_monitoring())
EOF
```

### 2. Budget Optimization
```python
# Budget optimization strategies
cat > budget_optimization.py << 'EOF'
import asyncio
from src.config.llm_config import LLMConfig
from src.monitoring.llm_metrics import LLMMetricsService

async def implement_budget_optimization():
    """Implement budget optimization strategies"""
    llm_config = LLMConfig()
    metrics_service = LLMMetricsService()
    
    # 1. Implement dynamic rate limiting
    llm_config.enable_dynamic_rate_limiting = True
    llm_config.rate_limit_adjustment_factor = 0.1
    
    # 2. Implement cost-aware processing
    llm_config.enable_cost_aware_processing = True
    llm_config.cost_threshold_per_request = 0.05  # $0.05 per request
    
    # 3. Implement smart batching
    llm_config.enable_smart_batching = True
    llm_config.batch_optimization_threshold = 0.8
    
    # 4. Implement field prioritization
    llm_config.enable_field_prioritization = True
    llm_config.field_priority_order = ['weight', 'roast', 'process', 'species', 'variety', 'geographic', 'tags', 'notes', 'sensory']
    
    # Save optimized configuration
    await llm_config.save_config()
    
    return "Budget optimization implemented"

if __name__ == "__main__":
    asyncio.run(implement_budget_optimization())
EOF
```

### 3. Cost Tracking and Analysis
```python
# Cost tracking implementation
cat > cost_tracking.py << 'EOF'
import asyncio
from datetime import datetime, timedelta
from src.monitoring.llm_metrics import LLMMetricsService

async def setup_cost_tracking():
    """Setup comprehensive cost tracking"""
    metrics_service = LLMMetricsService()
    
    # Setup daily cost tracking
    await metrics_service.setup_daily_cost_tracking()
    
    # Setup roaster-level cost tracking
    await metrics_service.setup_roaster_cost_tracking()
    
    # Setup field-level cost tracking
    await metrics_service.setup_field_cost_tracking()
    
    # Setup cost trend analysis
    await metrics_service.setup_cost_trend_analysis()
    
    # Setup cost alerts
    await metrics_service.setup_cost_alerts()
    
    return "Cost tracking setup completed"

if __name__ == "__main__":
    asyncio.run(setup_cost_tracking())
EOF
```

## Emergency Contacts

### LLM Budget Issues
- **Primary Developer**: [Name] - [Phone] - [Slack]
- **Secondary Developer**: [Name] - [Phone] - [Slack]
- **Budget Manager**: [Name] - [Phone] - [Slack]

### DeepSeek API Issues
- **API Support**: DeepSeek Support
- **Technical Lead**: [Name] - [Phone] - [Slack]

## Tools and Resources

### Budget Monitoring Tools
- **LLM Metrics**: `src/monitoring/llm_metrics.py`
- **Cost Tracking**: `src/monitoring/cost_tracking.py`
- **Budget Alerts**: `src/monitoring/alert_service.py`

### Configuration Files
- **LLM Config**: `src/config/llm_config.py`
- **DeepSeek Config**: `src/config/deepseek_config.py`
- **Budget Config**: `src/config/budget_config.py`

### Useful Commands
```bash
# Check LLM budget status
python check_llm_budget.py

# Implement emergency rate limiting
python emergency_rate_limit.py

# Check LLM usage
curl http://localhost:8000/metrics | grep -E "(llm_|token_|cost_)"

# Monitor LLM logs
tail -f /var/log/coffee-scraper/llm.log

# Reset daily budget
python reset_budget.py
```
