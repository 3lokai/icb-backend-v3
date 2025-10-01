# Story E.3: Firecrawl budget & fallback policy

## Status
Draft

## Story
**As a** system administrator,
**I want** comprehensive budget tracking and fallback policies for Firecrawl operations,
**so that** I can control costs, prevent budget overruns, and ensure reliable fallback behavior when Firecrawl budget is exhausted.

## Business Context
This story implements budget management and fallback policies for Firecrawl operations to ensure cost control and reliable system behavior. When Firecrawl budget is exhausted, the system must gracefully fall back to alternative methods or alert operations for manual intervention, preventing unexpected costs and ensuring continuous operation.

## Dependencies
**✅ COMPLETED: Core infrastructure exists:**
- **E.1 Firecrawl Map Discovery**: Product URL discovery with budget tracking
- **E.2 Firecrawl Extract**: Product extraction with budget decrement
- **G.1-G.4 Monitoring**: Observability and alerting infrastructure
- **A.1-A.5 Pipeline**: Job queue and error handling systems
- **Database Schema**: Roaster configuration with budget fields

## Acceptance Criteria
1. Budget tracking decrements for each Firecrawl map and extract operation
2. Budget exhaustion detection and automatic fallback behavior
3. Roaster flagging when budget exhausted with appropriate alerts
4. Budget reporting and analytics for cost monitoring
5. Integration with existing G.1-G.4 monitoring and alerting system
6. State persistence for budget tracking across system restarts
7. Budget reset and management capabilities for operations team
8. Comprehensive test coverage for budget scenarios and edge cases

## Tasks / Subtasks

### Task 1: Budget tracking implementation (AC: 1, 6)
- [ ] Create FirecrawlBudgetService following A.1-A.5 patterns
- [ ] Implement budget decrement for map and extract operations
- [ ] Add budget state persistence to database
- [ ] Create budget tracking metrics and monitoring
- [ ] Add comprehensive logging for budget operations

### Task 2: Budget exhaustion handling (AC: 2, 3)
- [ ] Implement budget exhaustion detection logic
- [ ] Create automatic fallback behavior when budget exhausted
- [ ] Add roaster flagging for budget exhaustion
- [ ] Implement graceful degradation for Firecrawl operations
- [ ] Add fallback to manual processing when budget exhausted

### Task 3: Alerting and monitoring integration (AC: 4, 5)
- [ ] Integrate budget alerts with G.1-G.4 monitoring system
- [ ] Create budget exhaustion alerts for operations team
- [ ] Add budget usage dashboards and reporting
- [ ] Implement budget trend analysis and forecasting
- [ ] Add budget health checks and monitoring

### Task 4: Budget management and operations (AC: 7, 8)
- [ ] Create budget reset and management capabilities
- [ ] Add budget allocation and distribution logic
- [ ] Implement budget recovery and replenishment
- [ ] Add budget audit trails and compliance tracking
- [ ] Create budget management API for operations team

### Task 5: Testing and validation (AC: 8)
- [ ] Create test scenarios for budget exhaustion
- [ ] Add edge case testing for budget scenarios
- [ ] Implement integration tests with monitoring system
- [ ] Add performance tests for budget operations
- [ ] Create end-to-end tests for budget workflows

## Dev Notes

### Architecture Context
[Source: architecture/2-component-architecture.md#2.2]

**Budget Management Integration:**
- **E.1 Map Discovery**: Budget decrement for map operations
- **E.2 Extract Operations**: Budget decrement for extract operations
- **G.1-G.4 Monitoring**: Budget alerts and reporting
- **A.1-A.5 Pipeline**: Job queue integration with budget checks
- **Database Schema**: Budget tracking and state persistence

### Budget Tracking Implementation
[Source: existing monitoring and database patterns]

**Budget Fields:**
- `firecrawl_budget_limit`: Total budget allocated per roaster
- `firecrawl_budget_used`: Current budget consumption
- `firecrawl_budget_remaining`: Available budget for operations
- `firecrawl_budget_exhausted_at`: Timestamp when budget exhausted

**Budget Operations:**
- **Map Operation**: Decrement budget by map cost (typically lower)
- **Extract Operation**: Decrement budget by extract cost (typically higher)
- **Budget Check**: Verify sufficient budget before operations
- **Budget Reset**: Replenish budget for continued operations

### Fallback Policy Implementation
[Source: existing error handling and fallback patterns]

**Fallback Scenarios:**
- **Budget Exhausted**: Disable Firecrawl, fallback to manual processing
- **API Failures**: Retry with backoff, then fallback to alternative methods
- **Rate Limiting**: Implement backoff, then fallback to manual processing
- **Data Quality Issues**: Flag for manual review, continue with other roasters

**Fallback Behavior:**
- **Immediate**: Stop Firecrawl operations when budget exhausted
- **Graceful**: Complete in-progress operations before stopping
- **Alerting**: Notify operations team of budget exhaustion
- **Recovery**: Enable Firecrawl when budget replenished

### Monitoring and Alerting Integration
[Source: G.1-G.4 monitoring infrastructure]

**Budget Metrics:**
- **Budget Usage**: Track budget consumption per roaster
- **Budget Trends**: Monitor budget usage patterns over time
- **Budget Health**: Alert when budget approaching exhaustion
- **Cost Analysis**: Track cost per operation and efficiency

**Alerting Thresholds:**
- **Warning**: 80% of budget consumed
- **Critical**: 95% of budget consumed
- **Exhausted**: 100% of budget consumed
- **Recovery**: Budget replenished after exhaustion

### Database Schema Integration
[Source: existing database schema and patterns]

**Budget Tracking Tables:**
- **roasters**: Add budget fields and tracking
- **firecrawl_operations**: Track individual operations and costs
- **budget_alerts**: Store budget alerts and notifications
- **budget_audit**: Audit trail for budget operations

**Budget State Persistence:**
- **Current Budget**: Track remaining budget per roaster
- **Operation History**: Store operation costs and timestamps
- **Alert History**: Track budget alerts and responses
- **Recovery Events**: Log budget replenishment and recovery

### Error Handling and Recovery
[Source: existing error handling patterns]

**Error Scenarios:**
- **Budget Calculation Errors**: Handle budget calculation failures
- **State Persistence Failures**: Handle database update failures
- **Alert Delivery Failures**: Handle alert system failures
- **Recovery Failures**: Handle budget replenishment failures

**Recovery Procedures:**
- **Budget Reset**: Manual budget reset by operations team
- **State Recovery**: Recover budget state from database
- **Alert Recovery**: Retry failed alert deliveries
- **System Recovery**: Restart Firecrawl operations after recovery

## Testing

### Test Execution
```bash
# Run budget tracking tests
python -m pytest tests/firecrawl/test_budget_tracking.py -v

# Run fallback policy tests
python -m pytest tests/firecrawl/test_fallback_policy.py -v

# Run integration tests with monitoring
python -m pytest tests/integration/test_firecrawl_budget_integration.py -v
```

### Test Coverage
- **Unit Tests**: Budget tracking, fallback logic, alerting
- **Integration Tests**: End-to-end budget workflows
- **Edge Case Tests**: Budget exhaustion scenarios
- **Performance Tests**: Budget operations under load

## Definition of Done
- [ ] Budget tracking decrements for each Firecrawl operation
- [ ] Budget exhaustion detection and automatic fallback
- [ ] Roaster flagging when budget exhausted with alerts
- [ ] Budget reporting and analytics for cost monitoring
- [ ] Integration with G.1-G.4 monitoring and alerting
- [ ] State persistence for budget tracking across restarts
- [ ] Budget reset and management capabilities
- [ ] Comprehensive test coverage for budget scenarios
- [ ] Performance optimization for budget operations
- [ ] Documentation updated with budget management
