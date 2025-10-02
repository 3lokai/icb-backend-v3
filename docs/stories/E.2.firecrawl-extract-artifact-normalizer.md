# Story E.2: Firecrawl extract → artifact normalizer

## Status
Draft

## Story
**As a** system administrator,
**I want** Firecrawl extract to convert scraped product data into canonical artifact format,
**so that** Firecrawl-discovered products can be processed through the existing normalization and validation pipeline.

## Business Context
This story implements Firecrawl extract functionality to scrape individual product pages and convert the output into the canonical artifact format used by the existing A.1-A.5 pipeline. This enables products discovered through Firecrawl map (E.1) to be processed through the same validation, normalization, and database storage pipeline as Shopify/WooCommerce products.

## Dependencies
**✅ COMPLETED: Core infrastructure exists:**
- **E.1 Firecrawl Map Discovery**: Product URL discovery and queuing
- **A.3 Artifact Validation**: Pydantic models for canonical artifact schema
- **A.4 RPC Integration**: Database storage through existing RPC functions
- **C.1-C.8 Normalizer Pipeline**: Text cleaning, parsing, and normalization
- **F.1-F.3 Image Processing**: Image handling and ImageKit integration

## Acceptance Criteria
1. Firecrawl extract service processes individual product URLs from map discovery
2. Extracted product data converted to canonical artifact format matching existing schema
3. Artifact validation ensures Firecrawl data meets same standards as Shopify/WooCommerce
4. Integration with existing C.1-C.8 normalizer pipeline for text processing
5. Image processing integration with F.1-F.3 image handling pipeline
6. Integration with E.3 budget tracking system for extract operations
7. Error handling for extraction failures with appropriate retry logic
8. Comprehensive test coverage with sample Firecrawl output data

## Tasks / Subtasks

### Task 1: Firecrawl extract service implementation (AC: 1, 2, 6)
- [ ] Create FirecrawlExtractService following A.1-A.5 patterns
- [ ] Implement product page extraction using Firecrawl extract API
- [ ] Add URL processing and validation for product pages
- [ ] Integrate with existing job queue system for extract operations
- [ ] Add comprehensive logging and monitoring for extract operations

### Task 2: Artifact format conversion (AC: 2, 3, 4)
- [ ] Create Firecrawl-to-canonical artifact converter
- [ ] Map Firecrawl output fields to canonical artifact schema
- [ ] Handle missing fields and data validation
- [ ] Add source attribution and metadata preservation
- [ ] Implement data quality checks and validation

### Task 3: Integration with normalizer pipeline (AC: 4, 5)
- [ ] Integrate Firecrawl artifacts with C.1-C.8 normalizer pipeline
- [ ] Add text cleaning and normalization for Firecrawl content
- [ ] Implement image processing for Firecrawl-discovered images
- [ ] Add sensory content parsing for Firecrawl products
- [ ] Ensure consistent data quality across all sources

### Task 4: Error handling and integration (AC: 6, 7)
- [ ] Integrate with E.3 budget tracking system for extract operations
- [ ] Create error handling for extraction failures
- [ ] Implement retry logic with exponential backoff
- [ ] Add fallback behavior for failed extractions
- [ ] Add comprehensive logging for extract operations

### Task 5: Testing and validation (AC: 8)
- [ ] Create test fixtures with sample Firecrawl output data
- [ ] Add unit tests for artifact conversion logic
- [ ] Implement integration tests with real Firecrawl API
- [ ] Add performance tests for batch extraction
- [ ] Create end-to-end tests with existing pipeline

## Dev Notes

### Architecture Context
[Source: architecture/2-component-architecture.md#2.2]

**Firecrawl Extract Integration:**
- **E.1 Map Discovery**: Provides product URLs for extraction
- **A.3 Artifact Validation**: Validates Firecrawl artifacts against schema
- **A.4 RPC Integration**: Stores Firecrawl artifacts in database
- **C.1-C.8 Normalizer**: Processes Firecrawl text and metadata
- **F.1-F.3 Image Processing**: Handles Firecrawl-discovered images

### Firecrawl Extract API Integration
[Source: Firecrawl documentation and existing patterns]

**Firecrawl Extract API:**
- **Endpoint**: `POST /v1/extract` for content extraction
- **Parameters**: URL, extractor, schema, include_links, include_images
- **Response**: Structured product data with metadata
- **Rate Limits**: Respect Firecrawl API rate limits and quotas

**Extraction Configuration:**
- **Extractor**: Use appropriate extractor for e-commerce sites
- **Schema**: Define schema for product data extraction
- **Include Links**: Extract related product links
- **Include Images**: Extract product images and metadata

**Integration with E.1 Map Discovery:**
- **Input**: Product URLs discovered by E.1 FirecrawlMapService
- **Processing**: Extract individual product pages using Firecrawl extract API
- **Output**: Canonical artifacts ready for A.3 validation and A.4 RPC integration

### Canonical Artifact Schema Integration
[Source: A.3 artifact validation and existing schema]

**Required Fields Mapping:**
- **source**: Set to 'firecrawl' for Firecrawl-discovered products
- **roaster_domain**: Extract from product URL domain
- **scraped_at**: Current timestamp for extraction
- **product**: Map Firecrawl product data to canonical format

**Product Field Mapping:**
- **platform_product_id**: Extract from Firecrawl product data
- **title**: Map product title from Firecrawl output
- **description_html/md**: Map product description
- **source_url**: Original product URL from map discovery
- **variants**: Convert Firecrawl variants to canonical format
- **images**: Process Firecrawl images through F.1-F.3 pipeline

### Normalizer Pipeline Integration
[Source: C.1-C.8 normalizer pipeline]

**Text Processing:**
- **C.7 Name Description Cleaner**: Clean Firecrawl product titles and descriptions
- **C.3 Tags Normalization**: Process Firecrawl product tags and categories
- **C.5 Varieties Geographic Parser**: Extract geographic and variety information
- **C.6 Sensory Content Hash Parser**: Process sensory information from Firecrawl

**Image Processing:**
- **F.1 Image Hash & Dedupe**: Process Firecrawl images for deduplication
- **F.2 ImageKit Integration**: Upload Firecrawl images to ImageKit
- **F.3 Price-only Guards**: Ensure images processed correctly in price-only mode

### Error Handling and Fallback
[Source: existing error handling patterns]

**Error Scenarios:**
- **Extraction Failures**: Firecrawl API errors or timeouts
- **Data Quality Issues**: Invalid or incomplete product data
- **Schema Validation**: Firecrawl output doesn't match expected format
- **Budget Exhaustion**: Firecrawl budget limit reached

**Fallback Behavior:**
- **Extraction Failures**: Retry with exponential backoff, then mark for manual review
- **Data Quality Issues**: Log warnings, continue with available data
- **Schema Validation**: Store raw data, flag for manual processing
- **Budget Exhaustion**: Disable Firecrawl for roaster, alert operations team

### Performance Considerations
[Source: existing performance patterns]

**Optimization Strategies:**
- **Batch Processing**: Process multiple product URLs in parallel
- **Caching**: Cache extraction results to avoid repeated API calls
- **Rate Limiting**: Respect Firecrawl API rate limits
- **Budget Management**: Optimize extraction operations to stay within budget

**Monitoring and Metrics:**
- **Extraction Success Rate**: Percentage of successful extractions
- **Data Quality Metrics**: Track completeness and accuracy of extracted data
- **API Performance**: Monitor Firecrawl API response times
- **Budget Usage**: Track budget consumption per roaster

## Testing

### Test Execution
```bash
# Run Firecrawl extract tests
python -m pytest tests/firecrawl/test_extract_service.py -v

# Run artifact conversion tests
python -m pytest tests/firecrawl/test_artifact_converter.py -v

# Run integration tests with real Firecrawl API
python -m pytest tests/integration/test_firecrawl_extract_integration.py -v
```

### Test Coverage
- **Unit Tests**: Firecrawl extract service, artifact conversion, budget tracking
- **Integration Tests**: End-to-end extraction with real API
- **Schema Tests**: Artifact validation and schema compliance
- **Performance Tests**: Batch extraction and optimization

## Definition of Done
- [ ] Firecrawl extract service processes product URLs from map discovery
- [ ] Extracted data converted to canonical artifact format
- [ ] Artifact validation ensures data quality standards
- [ ] Integration with existing C.1-C.8 normalizer pipeline
- [ ] Image processing integration with F.1-F.3 pipeline
- [ ] Integration with E.3 budget tracking system for extract operations
- [ ] Error handling for extraction failures with retry logic
- [ ] Comprehensive test coverage with sample data
- [ ] Performance optimization for batch operations
- [ ] Monitoring and alerting for extract operations
