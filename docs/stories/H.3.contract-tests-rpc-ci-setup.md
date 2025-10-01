# Story H.3: Contract tests for RPCs & CI setup

## Status
Draft

## Story
**As a** developer,
**I want** comprehensive contract tests for RPC functions and a robust CI pipeline,
**so that** I can ensure database contracts are stable and deployments are automated and reliable.

## Business Context
This story implements contract testing for RPC functions (`rpc_upsert_coffee`, `rpc_insert_price`, `rpc_upsert_image`) and sets up a comprehensive CI pipeline that validates the entire system. This ensures database contracts remain stable and deployments are automated and reliable.

## Dependencies
**✅ COMPLETED: RPC infrastructure exists:**
- **RPC Functions**: `rpc_upsert_coffee`, `rpc_insert_price`, `rpc_upsert_image` implemented
- **Database Schema**: Supabase tables and relationships defined
- **Test Infrastructure**: 1,384 tests with comprehensive coverage
- **Sample Data**: Real Shopify and WooCommerce data available
- **Monitoring**: G.1-G.4 observability and alerting infrastructure

## Acceptance Criteria
1. Contract tests validate RPC schema and database constraints
2. Contract tests validate RPC parameter types and required fields
3. Contract tests validate RPC error handling and edge cases
4. Contract tests validate RPC performance and timeout handling
5. CI pipeline runs all tests automatically on code changes
6. CI pipeline validates database migrations and schema changes
7. CI pipeline validates sample data processing end-to-end
8. CI pipeline provides test coverage reports and quality metrics
9. CI pipeline handles test failures gracefully with clear error reporting
10. CI pipeline supports both unit tests and integration tests

## Tasks / Subtasks

### Task 1: RPC contract test implementation (AC: 1, 2, 3, 4)
- [ ] Create contract tests for `rpc_upsert_coffee` function
- [ ] Create contract tests for `rpc_insert_price` function
- [ ] Create contract tests for `rpc_upsert_image` function
- [ ] Validate RPC parameter types and required fields
- [ ] Test RPC error handling and edge cases
- [ ] Test RPC performance and timeout handling
- [ ] Test RPC database constraints and validation

### Task 2: Database schema contract validation (AC: 1, 2)
- [ ] Validate database table schemas match RPC expectations
- [ ] Test foreign key constraints and relationships
- [ ] Test database triggers and functions
- [ ] Test database indexes and performance
- [ ] Test database migration compatibility

### Task 3: CI pipeline setup (AC: 5, 6, 7, 8, 9, 10)
- [ ] Set up GitHub Actions or similar CI platform
- [ ] Configure automated test execution on code changes
- [ ] Configure database setup and teardown for tests
- [ ] Configure sample data processing validation
- [ ] Configure test coverage reporting
- [ ] Configure quality metrics and reporting
- [ ] Configure error reporting and notifications

### Task 4: CI pipeline test categories (AC: 5, 10)
- [ ] Configure unit test execution (parser, normalizer modules)
- [ ] Configure integration test execution (end-to-end pipeline)
- [ ] Configure contract test execution (RPC functions)
- [ ] Configure performance test execution (memory, speed)
- [ ] Configure sample data test execution (real data validation)

### Task 5: CI pipeline quality gates (AC: 8, 9)
- [ ] Set up test coverage thresholds (90%+ for critical modules)
- [ ] Set up performance benchmarks (memory, speed limits)
- [ ] Set up quality metrics (code complexity, maintainability)
- [ ] Set up error reporting and failure notifications
- [ ] Set up deployment gates and approval processes

### Task 6: CI pipeline database integration (AC: 6)
- [ ] Configure database setup for CI environment
- [ ] Configure database migration testing
- [ ] Configure database schema validation
- [ ] Configure database performance testing
- [ ] Configure database backup and recovery testing

## Dev Notes

### RPC Contract Analysis
[Source: docs/db/rpc.md and existing RPC implementation]

**RPC Functions to Test:**
- **rpc_upsert_coffee**: Coffee product upsert with all parameters
- **rpc_insert_price**: Price insertion with currency and timestamp
- **rpc_upsert_image**: Image upsert with ImageKit URL and metadata

**RPC Parameters to Validate:**
- **Coffee Parameters**: Name, description, roaster, origin, processing
- **Price Parameters**: Amount, currency, timestamp, variant_id
- **Image Parameters**: URL, ImageKit URL, metadata, product_id

### Database Schema Contracts
[Source: docs/db/tables.md]

**Tables to Validate:**
- **coffees**: Product information, metadata, timestamps
- **variants**: Product variants, weights, prices, attributes
- **prices**: Price history, currency, timestamps
- **images**: Image URLs, ImageKit URLs, metadata
- **processing_status**: Status flags, timestamps, error information

### CI Pipeline Architecture
[Source: architecture/4-deployment-architecture-flyio.md]

**CI Pipeline Stages:**
1. **Code Quality**: Linting, formatting, complexity checks
2. **Unit Tests**: Parser, normalizer, validator modules
3. **Integration Tests**: End-to-end pipeline validation
4. **Contract Tests**: RPC function validation
5. **Performance Tests**: Memory, speed, efficiency
6. **Sample Data Tests**: Real data processing validation
7. **Database Tests**: Schema, migrations, constraints
8. **Deployment Tests**: Production readiness validation

### Test Coverage Requirements
- **Parser Modules**: 90%+ coverage for weight, roast, process, species, sensory
- **Normalizer Modules**: 90%+ coverage for tag normalization, text normalization
- **RPC Functions**: 95%+ coverage for all RPC contract tests
- **Integration Tests**: 85%+ coverage for end-to-end pipeline
- **Sample Data Tests**: 100% coverage for critical data processing paths

### Performance Benchmarks
- **Unit Tests**: Complete execution within 2 minutes
- **Integration Tests**: Complete execution within 5 minutes
- **Contract Tests**: Complete execution within 3 minutes
- **Sample Data Tests**: Complete execution within 10 minutes
- **Total CI Pipeline**: Complete execution within 15 minutes

### Error Handling and Reporting
- **Test Failures**: Clear error messages and stack traces
- **Coverage Reports**: HTML and text coverage reports
- **Quality Metrics**: Code complexity, maintainability scores
- **Performance Reports**: Memory usage, execution time metrics
- **Database Reports**: Schema validation, migration status

## Testing

### Test Execution
```bash
# Run contract tests
python -m pytest tests/contract/ -v

# Run CI pipeline locally
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# Run specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
python -m pytest tests/contract/ -v
python -m pytest tests/performance/ -v
```

### CI Pipeline Validation
- All tests pass in CI environment
- Database setup and teardown works correctly
- Sample data processing works correctly
- Coverage reports generated correctly
- Quality metrics calculated correctly
- Error reporting works correctly

## Definition of Done
- [ ] Contract tests validate RPC schema and constraints
- [ ] Contract tests validate RPC parameter types and fields
- [ ] Contract tests validate RPC error handling and edge cases
- [ ] Contract tests validate RPC performance and timeouts
- [ ] CI pipeline runs all tests automatically on code changes
- [ ] CI pipeline validates database migrations and schema
- [ ] CI pipeline validates sample data processing end-to-end
- [ ] CI pipeline provides test coverage reports and quality metrics
- [ ] CI pipeline handles test failures gracefully with clear reporting
- [ ] CI pipeline supports both unit tests and integration tests
- [ ] CI pipeline execution time remains reasonable (< 15 minutes)
- [ ] CI pipeline provides reliable and consistent results
