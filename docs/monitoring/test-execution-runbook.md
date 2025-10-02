# Test Execution Runbook

## Overview

This runbook provides operational procedures for sample data testing, including test orchestration, performance validation, error handling, and monitoring. It serves as a comprehensive guide for running and maintaining the test infrastructure.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Test Execution Procedures](#test-execution-procedures)
3. [Performance Validation](#performance-validation)
4. [Error Handling and Recovery](#error-handling-and-recovery)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance Procedures](#maintenance-procedures)

## Prerequisites

### System Requirements

- **Python 3.8+** with required dependencies
- **Memory**: Minimum 2GB RAM, 4GB recommended
- **Storage**: 1GB free space for test data and logs
- **Network**: Access to sample data repositories and external services

### Required Dependencies

```bash
# Install test dependencies
pip install pytest pytest-asyncio psutil tracemalloc

# Install monitoring dependencies
pip install prometheus-client grafana-api

# Install performance testing dependencies
pip install memory-profiler line-profiler
```

### Environment Setup

```bash
# Set environment variables
export TEST_DATA_PATH="data/samples"
export TEST_OUTPUT_PATH="test_results"
export MONITORING_ENABLED="true"
export PERFORMANCE_THRESHOLDS="memory:1024,time:300"
```

## Test Execution Procedures

### 1. Basic Test Execution

#### Run All Integration Tests
```bash
# Run complete test suite with orchestration
python -m pytest tests/integration/test_sample_data_orchestration.py -v

# Run with performance monitoring
python -m pytest tests/integration/ --orchestration --monitoring --performance

# Run specific test categories
python -m pytest tests/integration/test_a1_a5_pipeline_integration.py -v
python -m pytest tests/fetcher/test_integration_real_data.py -v
python -m pytest tests/parser/test_end_to_end_pipeline.py -v
python -m pytest tests/validator/test_real_rpc_with_real_data.py -v
python -m pytest tests/images/test_pipeline_integration.py -v
```

#### Run Performance Tests
```bash
# Run performance validation tests
python -m pytest tests/performance/test_sample_data_performance.py -v

# Run with memory profiling
python -m pytest tests/performance/ --profile-memory

# Run with execution time profiling
python -m pytest tests/performance/ --profile-time
```

#### Run Error Handling Tests
```bash
# Run error handling and resilience tests
python -m pytest tests/integration/test_error_handling_sample_data.py -v

# Run with specific error scenarios
python -m pytest tests/integration/test_error_handling_sample_data.py::TestErrorHandling::test_malformed_data_injection -v
```

### 2. Test Orchestration

#### Start Test Orchestration
```bash
# Start centralized test orchestration
python -c "
from tests.integration.test_sample_data_orchestration import TestOrchestrationManager
import asyncio

async def run_tests():
    manager = TestOrchestrationManager()
    results = await manager.run_orchestrated_tests()
    print(f'Test Results: {results}')

asyncio.run(run_tests())
"
```

#### Monitor Test Execution
```bash
# Monitor test execution status
python -c "
from tests.integration.test_sample_data_orchestration import TestOrchestrationManager
import asyncio

async def monitor_tests():
    manager = TestOrchestrationManager()
    status = manager.get_test_status()
    print(f'Test Status: {status}')

asyncio.run(monitor_tests())
"
```

### 3. Test Data Management

#### Prepare Sample Data
```bash
# Ensure sample data is available
ls -la data/samples/shopify/
ls -la data/samples/woocommerce/

# Validate sample data integrity
python -c "
import json
from pathlib import Path

def validate_sample_data(path):
    for file_path in Path(path).glob('**/*.json'):
        try:
            with open(file_path, 'r') as f:
                json.load(f)
            print(f'✓ {file_path} is valid JSON')
        except Exception as e:
            print(f'✗ {file_path} is invalid: {e}')

validate_sample_data('data/samples')
"
```

#### Clean Test Data
```bash
# Clean up test artifacts
rm -rf test_results/*
rm -rf data/validator/invalid_artifacts/*
rm -rf logs/test_execution_*.log
```

## Performance Validation

### 1. Performance Thresholds

| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Execution Time | 5 minutes | Warning |
| Memory Usage | 1GB | Critical |
| CPU Usage | 80% | Warning |
| Success Rate | 95% | Critical |

### 2. Performance Monitoring

#### Start Performance Monitoring
```bash
# Start performance monitoring for sample data processing
python -c "
from tests.performance.test_sample_data_performance import PerformanceValidator, PerformanceThresholds
import asyncio

async def monitor_performance():
    thresholds = PerformanceThresholds(
        max_execution_time=300.0,
        max_memory_usage=1024.0,
        max_cpu_usage=80.0
    )
    validator = PerformanceValidator(thresholds)
    results = await validator.validate_sample_data_processing('data/samples')
    print(f'Performance Results: {results}')

asyncio.run(monitor_performance())
"
```

#### Check Performance Metrics
```bash
# Get performance summary
python -c "
from tests.performance.test_sample_data_performance import PerformanceValidator
validator = PerformanceValidator()
summary = validator.get_performance_summary()
print(f'Performance Summary: {summary}')
"
```

### 3. Performance Regression Detection

#### Set Baseline Metrics
```bash
# Set baseline performance metrics
python -c "
from tests.performance.test_sample_data_performance import PerformanceMetrics, PerformanceValidator
from datetime import datetime

# Create baseline metrics
baseline = PerformanceMetrics(
    test_name='baseline',
    execution_time=120.0,
    memory_peak=512.0,
    memory_average=400.0,
    cpu_usage=60.0
)

validator = PerformanceValidator()
validator.set_baseline_metrics(baseline)
print('Baseline metrics set')
"
```

#### Detect Performance Regression
```bash
# Check for performance regression
python -c "
from tests.performance.test_sample_data_performance import PerformanceMonitor, PerformanceMetrics
from datetime import datetime

monitor = PerformanceMonitor()
current = PerformanceMetrics('current', 150.0, 600.0, 500.0, 70.0)
baseline = PerformanceMetrics('baseline', 120.0, 512.0, 400.0, 60.0)

regression = monitor.detect_regression(baseline, current)
print(f'Regression Detection: {regression}')
"
```

## Error Handling and Recovery

### 1. Error Scenario Testing

#### Test Malformed Data Handling
```bash
# Test error handling with malformed data
python -c "
from tests.integration.test_error_handling_sample_data import ErrorHandlingTestSuite
import asyncio

async def test_error_handling():
    suite = ErrorHandlingTestSuite()
    results = await suite.run_error_handling_tests('data/samples')
    
    for result in results:
        print(f'Scenario: {result.scenario_name}')
        print(f'  Error Occurred: {result.error_occurred}')
        print(f'  Recovery Successful: {result.recovery_successful}')
        print(f'  Processing Continued: {result.processing_continued}')

asyncio.run(test_error_handling())
"
```

#### Test Graceful Degradation
```bash
# Test graceful degradation strategies
python -c "
from tests.integration.test_error_handling_sample_data import ErrorRecoveryTester
import asyncio

async def test_graceful_degradation():
    tester = ErrorRecoveryTester()
    
    # Test with corrupted data
    corrupted_data = {'products': [{'id': None, 'title': None}]}
    
    strategies = ['skip_invalid_records', 'use_default_values', 'retry_with_delay']
    for strategy in strategies:
        result = await tester.test_graceful_degradation(corrupted_data, strategy)
        print(f'Strategy {strategy}: {result.recovery_successful}')

asyncio.run(test_graceful_degradation())
"
```

### 2. Recovery Procedures

#### Database State Recovery
```bash
# Reset database state after test failures
python -c "
import subprocess
import sys

def reset_database():
    try:
        # Reset test database
        subprocess.run(['python', 'scripts/reset_test_db.py'], check=True)
        print('Database state reset successfully')
    except subprocess.CalledProcessError as e:
        print(f'Database reset failed: {e}')
        sys.exit(1)

reset_database()
"
```

#### Test Environment Recovery
```bash
# Recover test environment
python -c "
import os
import shutil

def recover_test_environment():
    # Clean test artifacts
    if os.path.exists('test_results'):
        shutil.rmtree('test_results')
    os.makedirs('test_results')
    
    # Reset test data
    if os.path.exists('data/validator/invalid_artifacts'):
        shutil.rmtree('data/validator/invalid_artifacts')
    os.makedirs('data/validator/invalid_artifacts')
    
    print('Test environment recovered')

recover_test_environment()
"
```

## Monitoring and Alerting

### 1. Test Execution Monitoring

#### Start Test Monitoring
```bash
# Start test execution monitoring
python -c "
from tests.monitoring.test_execution_monitoring import TestExecutionMonitor
import asyncio

async def start_monitoring():
    monitor = TestExecutionMonitor()
    await monitor.start_monitoring()
    print('Test monitoring started')

asyncio.run(start_monitoring())
"
```

#### Check Test Health Status
```bash
# Get test health status
python -c "
from tests.monitoring.test_execution_monitoring import TestExecutionMonitor

monitor = TestExecutionMonitor()
health_status = monitor.get_test_health_status()
print(f'Health Status: {health_status}')
"
```

### 2. Alerting System

#### Check Active Alerts
```bash
# Check for active alerts
python -c "
from tests.monitoring.test_execution_monitoring import TestExecutionMonitor, AlertLevel

monitor = TestExecutionMonitor()
alerts = monitor.get_alerts()
error_alerts = monitor.get_alerts(AlertLevel.ERROR)

print(f'Total Alerts: {len(alerts)}')
print(f'Error Alerts: {len(error_alerts)}')

for alert in error_alerts:
    print(f'  {alert.level.value}: {alert.message}')
"
```

#### Generate Test Dashboard
```bash
# Generate test dashboard data
python -c "
from tests.monitoring.test_execution_monitoring import TestExecutionMonitor, TestDashboard

monitor = TestExecutionMonitor()
dashboard = TestDashboard(monitor)
data = dashboard.generate_dashboard_data()
print(f'Dashboard Data: {data}')
"
```

### 3. Performance Monitoring

#### Monitor Memory Usage
```bash
# Monitor memory usage during tests
python -c "
import psutil
import time

def monitor_memory():
    process = psutil.Process()
    while True:
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        print(f'Memory Usage: {memory_mb:.2f}MB')
        time.sleep(1)

monitor_memory()
"
```

#### Monitor CPU Usage
```bash
# Monitor CPU usage during tests
python -c "
import psutil
import time

def monitor_cpu():
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f'CPU Usage: {cpu_percent:.2f}%')
        time.sleep(1)

monitor_cpu()
"
```

## Troubleshooting

### 1. Common Issues

#### Test Execution Failures
```bash
# Check test execution logs
tail -f logs/test_execution_*.log

# Check for specific error patterns
grep -i "error\|failed\|exception" logs/test_execution_*.log
```

#### Performance Issues
```bash
# Check performance metrics
python -c "
from tests.performance.test_sample_data_performance import PerformanceValidator
validator = PerformanceValidator()
summary = validator.get_performance_summary()
print(f'Performance Issues: {summary}')
"
```

#### Memory Issues
```bash
# Check memory usage
python -c "
import psutil
process = psutil.Process()
memory_info = process.memory_info()
print(f'Current Memory: {memory_info.rss / 1024 / 1024:.2f}MB')
print(f'Peak Memory: {memory_info.peak_wss / 1024 / 1024:.2f}MB')
"
```

### 2. Debug Procedures

#### Enable Debug Logging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG_MODE=true

# Run tests with debug output
python -m pytest tests/integration/ -v -s --log-cli-level=DEBUG
```

#### Generate Debug Report
```bash
# Generate comprehensive debug report
python -c "
import json
import os
from datetime import datetime

def generate_debug_report():
    report = {
        'timestamp': datetime.now().isoformat(),
        'environment': dict(os.environ),
        'test_results': {},
        'performance_metrics': {},
        'error_logs': []
    }
    
    # Add test results
    if os.path.exists('test_results'):
        for file in os.listdir('test_results'):
            if file.endswith('.json'):
                with open(f'test_results/{file}', 'r') as f:
                    report['test_results'][file] = json.load(f)
    
    # Save debug report
    with open('debug_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print('Debug report generated: debug_report.json')

generate_debug_report()
"
```

## Maintenance Procedures

### 1. Regular Maintenance

#### Clean Test Artifacts
```bash
# Clean test artifacts (run weekly)
find test_results -name "*.json" -mtime +7 -delete
find logs -name "*.log" -mtime +30 -delete
find data/validator/invalid_artifacts -name "*.json" -mtime +7 -delete
```

#### Update Test Data
```bash
# Update sample data (run monthly)
python scripts/update_sample_data.py
```

#### Validate Test Infrastructure
```bash
# Validate test infrastructure (run weekly)
python -m pytest tests/integration/test_sample_data_orchestration.py -v
python -m pytest tests/performance/test_sample_data_performance.py -v
python -m pytest tests/monitoring/test_execution_monitoring.py -v
```

### 2. Performance Optimization

#### Optimize Test Execution
```bash
# Run performance analysis
python -c "
from tests.performance.test_sample_data_performance import PerformanceValidator
import asyncio

async def optimize_performance():
    validator = PerformanceValidator()
    results = await validator.validate_sample_data_processing('data/samples')
    
    # Analyze performance bottlenecks
    if results['validation']['valid']:
        print('Performance is within thresholds')
    else:
        print('Performance issues detected:')
        for violation in results['validation']['violations']:
            print(f'  - {violation}')

asyncio.run(optimize_performance())
"
```

#### Update Performance Baselines
```bash
# Update performance baselines
python -c "
from tests.performance.test_sample_data_performance import PerformanceMetrics, PerformanceValidator
from datetime import datetime

# Set new baseline metrics
baseline = PerformanceMetrics(
    test_name='updated_baseline',
    execution_time=100.0,  # Updated baseline
    memory_peak=512.0,
    memory_average=400.0,
    cpu_usage=60.0
)

validator = PerformanceValidator()
validator.set_baseline_metrics(baseline)
print('Performance baselines updated')
"
```

### 3. Documentation Updates

#### Update Test Documentation
```bash
# Generate updated test documentation
python -c "
import json
from pathlib import Path

def update_test_docs():
    # Generate test coverage report
    coverage_report = {
        'orchestration_tests': len(list(Path('tests/integration').glob('test_sample_data_orchestration.py'))),
        'performance_tests': len(list(Path('tests/performance').glob('test_sample_data_performance.py'))),
        'monitoring_tests': len(list(Path('tests/monitoring').glob('test_execution_monitoring.py'))),
        'error_handling_tests': len(list(Path('tests/integration').glob('test_error_handling_sample_data.py')))
    }
    
    with open('test_coverage_report.json', 'w') as f:
        json.dump(coverage_report, f, indent=2)
    
    print('Test documentation updated')

update_test_docs()
"
```

## Emergency Procedures

### 1. Test System Recovery

#### Complete System Reset
```bash
# Complete test system reset
python -c "
import os
import shutil

def reset_test_system():
    # Stop all test processes
    os.system('pkill -f pytest')
    
    # Clean all test artifacts
    for dir_name in ['test_results', 'logs', 'data/validator/invalid_artifacts']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
        os.makedirs(dir_name)
    
    # Reset test database
    os.system('python scripts/reset_test_db.py')
    
    print('Test system reset completed')

reset_test_system()
"
```

#### Emergency Test Execution
```bash
# Emergency test execution with minimal monitoring
python -m pytest tests/integration/ --orchestration --no-monitoring --no-performance
```

### 2. Data Recovery

#### Recover Test Data
```bash
# Recover test data from backups
python -c "
import shutil
from pathlib import Path

def recover_test_data():
    backup_path = Path('backups/test_data')
    if backup_path.exists():
        shutil.copytree(backup_path, 'data/samples', dirs_exist_ok=True)
        print('Test data recovered from backup')
    else:
        print('No backup found, using default test data')

recover_test_data()
"
```

## Contact Information

- **Test Infrastructure Team**: test-infra@company.com
- **Performance Team**: performance@company.com
- **Monitoring Team**: monitoring@company.com
- **Emergency Contact**: +1-555-TEST-HELP

## Appendix

### A. Test Configuration Files

- `tests/integration/test_sample_data_orchestration.py` - Test orchestration framework
- `tests/performance/test_sample_data_performance.py` - Performance validation
- `tests/integration/test_error_handling_sample_data.py` - Error handling tests
- `tests/monitoring/test_execution_monitoring.py` - Test execution monitoring

### B. Sample Data Locations

- `data/samples/shopify/` - Shopify sample data
- `data/samples/woocommerce/` - WooCommerce sample data
- `data/validator/invalid_artifacts/` - Invalid test artifacts

### C. Log Files

- `logs/test_execution_*.log` - Test execution logs
- `logs/performance_*.log` - Performance monitoring logs
- `logs/error_handling_*.log` - Error handling logs
- `logs/monitoring_*.log` - Monitoring system logs
