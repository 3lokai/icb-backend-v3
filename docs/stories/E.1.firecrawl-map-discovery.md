# Story E.1: Firecrawl map discovery

## Status
Draft

## Story
**As a** system administrator,
**I want** Firecrawl map discovery to find product URLs for roasters using non-standard platforms (Magento, custom),
**so that** I can scrape roasters that don't have JSON APIs or require browser rendering.

## Business Context
This story implements Firecrawl map discovery as a fallback mechanism for roasters using Magento, custom platforms, or other non-standard e-commerce systems. When Shopify/WooCommerce fetchers fail or return insufficient data, Firecrawl map will discover product URLs that can then be processed through the extract pipeline.

## Dependencies
**✅ COMPLETED: Core infrastructure exists:**
- **A.1-A.5 Pipeline**: Worker scaffolding, fetcher service, artifact validation, RPC integration
- **Configuration System**: Roaster configuration with `use_firecrawl_fallback` and `firecrawl_budget_limit`
- **Queue System**: Redis-based job queue with retry logic and backoff
- **Database Schema**: Roaster configuration fields for Firecrawl integration
- **Monitoring**: G.1-G.4 observability and alerting infrastructure

## Acceptance Criteria
1. Firecrawl client integration with proper authentication and configuration
2. Map discovery returns product URLs for roasters with `use_firecrawl_fallback=true`
3. Product URLs are queued for extract processing with proper job metadata
4. Budget tracking decrements `firecrawl_budget_limit` for each map operation
5. Error handling for Firecrawl API failures with appropriate fallback behavior
6. Integration with existing A.1-A.5 pipeline architecture and patterns
7. Comprehensive test coverage for map discovery functionality
8. Performance optimization for batch URL discovery operations

## Tasks / Subtasks

### Task 1: Firecrawl client implementation (AC: 1, 6)
- [ ] Install Firecrawl Python SDK and add to requirements.txt
- [ ] Create Firecrawl client service with authentication
- [ ] Implement configuration management for Firecrawl API keys
- [ ] Add Firecrawl client to dependency injection system
- [ ] Create error handling and retry logic for Firecrawl API calls

### Task 2: Map discovery service implementation (AC: 2, 3, 6)
- [ ] Create FirecrawlMapService following A.1-A.5 patterns
- [ ] Implement domain mapping to discover product URLs
- [ ] Add URL filtering and validation for coffee-related products
- [ ] Integrate with existing job queue system for URL processing
- [ ] Add comprehensive logging and monitoring for map operations

### Task 3: Budget tracking and management (AC: 4, 5)
- [ ] Implement budget tracking for Firecrawl operations
- [ ] Add budget decrement logic for each map operation
- [ ] Create budget exhaustion handling and alerts
- [ ] Integrate with existing monitoring and alerting system
- [ ] Add budget reporting and analytics

### Task 4: Integration with existing pipeline (AC: 6, 7)
- [ ] Integrate Firecrawl map with A.1-A.5 fetcher service
- [ ] Add Firecrawl fallback logic to existing fetcher patterns
- [ ] Implement proper error handling and fallback behavior
- [ ] Add Firecrawl-specific configuration to roaster schema
- [ ] Create integration tests with existing pipeline components

### Task 5: Performance optimization and testing (AC: 7, 8)
- [ ] Implement batch processing for multiple domain mapping
- [ ] Add performance monitoring and optimization
- [ ] Create comprehensive unit tests for map discovery
- [ ] Add integration tests with real Firecrawl API
- [ ] Implement performance benchmarks and monitoring

## Dev Notes

### Architecture Context
[Source: architecture/2-component-architecture.md#2.2]

**Firecrawl Integration Points:**
- **A.1 Worker Scaffolding**: Firecrawl jobs integrated with existing job queue
- **A.2 Fetcher Service**: Firecrawl map as fallback when JSON endpoints fail
- **A.3 Artifact Validation**: Firecrawl output validated against existing schema
- **A.4 RPC Integration**: Firecrawl artifacts processed through existing RPC pipeline
- **A.5 Coffee Classification**: Firecrawl products classified using existing logic

### Firecrawl API Integration
[Source: Firecrawl documentation and existing patterns]

**Firecrawl Map API:**
- **Endpoint**: `POST /v1/map` for domain mapping
- **Parameters**: URL, max_pages, search, include_links, include_images
- **Response**: Array of discovered URLs with metadata
- **Rate Limits**: Respect Firecrawl API rate limits and quotas

**Configuration Requirements:**
- **API Key**: Firecrawl API key from environment variables
- **Base URL**: Firecrawl API base URL configuration
- **Timeout**: Request timeout configuration
- **Retry Logic**: Exponential backoff for API failures

### Roaster Configuration Integration
[Source: src/config/roaster_schema.py]

**Firecrawl Configuration Fields:**
- `use_firecrawl_fallback`: Boolean flag to enable Firecrawl for roaster
- `firecrawl_budget_limit`: Integer budget limit for Firecrawl operations
- `platform`: Set to 'custom' or 'other' for non-standard platforms
- `website`: Domain URL for Firecrawl mapping

### Job Queue Integration
[Source: existing A.1-A.5 pipeline architecture]

**Job Types:**
- **Map Job**: Discover product URLs for a roaster domain
- **Extract Job**: Process individual product URLs (E.2 story)
- **Fallback Job**: Handle Firecrawl failures and retries

**Job Metadata:**
- Roaster ID and configuration
- Domain URL and mapping parameters
- Budget tracking and limits
- Error handling and retry logic

### Error Handling and Fallback
[Source: existing error handling patterns]

**Error Scenarios:**
- **API Failures**: Firecrawl API unavailable or rate limited
- **Budget Exhaustion**: Firecrawl budget limit reached
- **Invalid Domains**: Domains that don't support mapping
- **Network Issues**: Connectivity problems with Firecrawl API

**Fallback Behavior:**
- **API Failures**: Retry with exponential backoff, then mark roaster for manual review
- **Budget Exhaustion**: Disable Firecrawl for roaster, alert operations team
- **Invalid Domains**: Log error, continue with other roasters
- **Network Issues**: Retry with backoff, then fallback to manual processing

### Performance Considerations
[Source: existing performance patterns]

**Optimization Strategies:**
- **Batch Processing**: Process multiple domains in parallel
- **Caching**: Cache map results to avoid repeated API calls
- **Rate Limiting**: Respect Firecrawl API rate limits
- **Budget Management**: Optimize map operations to stay within budget

**Monitoring and Metrics:**
- **Map Success Rate**: Percentage of successful map operations
- **Budget Usage**: Track budget consumption per roaster
- **API Performance**: Monitor Firecrawl API response times
- **Error Rates**: Track and alert on high error rates

## Testing

### Test Execution
```bash
# Run Firecrawl map tests
python -m pytest tests/firecrawl/test_map_discovery.py -v

# Run integration tests with real Firecrawl API
python -m pytest tests/integration/test_firecrawl_integration.py -v

# Run performance tests
python -m pytest tests/performance/test_firecrawl_performance.py -v
```

### Test Coverage
- **Unit Tests**: Firecrawl client, map service, budget tracking
- **Integration Tests**: End-to-end map discovery with real API
- **Performance Tests**: Batch processing and optimization
- **Error Tests**: API failures, budget exhaustion, network issues

## Definition of Done
- [ ] Firecrawl client integrated with proper authentication
- [ ] Map discovery returns product URLs for configured roasters
- [ ] Product URLs queued for extract processing
- [ ] Budget tracking decrements for each map operation
- [ ] Error handling for Firecrawl API failures
- [ ] Integration with existing A.1-A.5 pipeline architecture
- [ ] Comprehensive test coverage for map discovery
- [ ] Performance optimization for batch operations
- [ ] Monitoring and alerting for Firecrawl operations
- [ ] Documentation updated with Firecrawl integration
