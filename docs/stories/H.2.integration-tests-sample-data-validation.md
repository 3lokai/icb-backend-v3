# Story H.2: Integration tests: sample data validation

## Status
Draft

## Story
**As a** developer,
**I want** comprehensive integration tests that validate the full pipeline using real sample data,
**so that** I can ensure the system works correctly with actual Shopify and WooCommerce data before production deployment.

## Business Context
This story creates end-to-end integration tests using the real sample data from `data/samples/` to validate the complete pipeline from data ingestion through parsing, normalization, and database storage. This ensures the system works correctly with actual e-commerce data structures.

## Dependencies
**✅ COMPLETED: Sample data available:**
- **Shopify samples**: `data/samples/shopify/bluetokaicoffee-shopify.json`, `rosettecoffee-shopify.json`
- **WooCommerce samples**: `data/samples/woocommerce/bababeans-woocommerce.json`
- **Pipeline infrastructure**: A.1-A.5 fetcher and parser modules
- **Database integration**: RPC upsert functions and Supabase integration
- **Image processing**: F.1-F.3 image handling and ImageKit integration

## Acceptance Criteria
1. End-to-end test processes complete Shopify sample data through full pipeline
2. End-to-end test processes complete WooCommerce sample data through full pipeline
3. Database state verification confirms correct data storage in `coffees`, `variants`, `prices` tables
4. Processing status flags are set appropriately for all processed items
5. Image processing works correctly with sample data images
6. Price updates work correctly with sample data pricing
7. All parser modules handle real data correctly (weight, roast, process, species, sensory)
8. All normalizer modules process real data correctly (tags, text, variety)
9. Performance tests validate processing time and memory usage with sample data
10. Error handling works correctly with malformed or incomplete sample data

## Tasks / Subtasks

### Task 1: Create sample data test harness (AC: 1, 2)
- [ ] Create test harness for loading and processing sample data
- [ ] Implement Shopify sample data loader and validator
- [ ] Implement WooCommerce sample data loader and validator
- [ ] Create test fixtures for sample data processing
- [ ] Add sample data validation and integrity checks

### Task 2: Shopify integration test implementation (AC: 1, 3, 7, 8)
- [ ] Process Blue Tokai Coffee sample data through full pipeline
- [ ] Process Rosette Coffee sample data through full pipeline
- [ ] Validate Shopify-specific data extraction (products, variants, images)
- [ ] Verify Shopify data mapping to database schema
- [ ] Test Shopify-specific parser logic (weight, roast, process, species)
- [ ] Test Shopify-specific normalizer logic (tags, text, variety)

### Task 3: WooCommerce integration test implementation (AC: 2, 3, 7, 8)
- [ ] Process Baba Beans sample data through full pipeline
- [ ] Validate WooCommerce-specific data extraction (products, attributes, categories)
- [ ] Verify WooCommerce data mapping to database schema
- [ ] Test WooCommerce-specific parser logic (weight, roast, process, species)
- [ ] Test WooCommerce-specific normalizer logic (tags, text, variety)

### Task 4: Database state verification (AC: 3, 4)
- [ ] Verify `coffees` table populated correctly with sample data
- [ ] Verify `variants` table populated correctly with sample data
- [ ] Verify `prices` table populated correctly with sample data
- [ ] Verify `processing_status` flags set appropriately
- [ ] Verify data integrity and foreign key relationships
- [ ] Verify audit trail and metadata storage

### Task 5: Image processing integration test (AC: 5)
- [ ] Test image processing with sample data images
- [ ] Verify ImageKit integration works with sample images
- [ ] Test image deduplication with sample data
- [ ] Verify image URL storage in database
- [ ] Test price-only image guard enforcement

### Task 6: Price processing integration test (AC: 6)
- [ ] Test price updates with sample data pricing
- [ ] Verify price delta tracking and storage
- [ ] Test price-only processing path
- [ ] Verify price data integrity and currency handling
- [ ] Test price update performance and efficiency

### Task 7: Performance and error handling tests (AC: 9, 10)
- [ ] Test processing time with full sample datasets
- [ ] Test memory usage with large sample data
- [ ] Test error handling with malformed sample data
- [ ] Test recovery from processing failures
- [ ] Test batch processing efficiency

## Dev Notes

### Sample Data Analysis
[Source: data/samples/ directory analysis]

**Shopify Sample Data Structure:**
- **Blue Tokai Coffee**: 8,737 lines, complex product data with variants, images, tags
- **Rosette Coffee**: Similar structure, different product types and attributes
- **Key Fields**: products, variants, images, tags, vendor, product_type
- **Complex Data**: HTML descriptions, image URLs, variant options, pricing

**WooCommerce Sample Data Structure:**
- **Baba Beans**: 16,314 lines, variable products with attributes and categories
- **Key Fields**: products, attributes, categories, images, pricing
- **Complex Data**: Short descriptions, categories, attributes, image sets

### Pipeline Integration Points
[Source: architecture/2-component-architecture.md#2.2]

**A.1-A.5 Pipeline Integration:**
- **A.1**: Worker scaffolding and orchestration
- **A.2**: Shopify/WooCommerce list fetcher
- **A.3**: Artifact validation and Pydantic models
- **A.4**: RPC upsert integration
- **A.5**: Coffee classification parser

**C.1-C.8 Normalizer Integration:**
- **C.1**: Weight unit parser library
- **C.2**: Roast process mapping
- **C.3**: Tags normalization and notes extraction
- **C.4**: Grind bean species parser
- **C.5**: Varieties geographic parser
- **C.6**: Sensory content hash parser
- **C.7**: Name description cleaner
- **C.8**: Complete normalizer pipeline

**F.1-F.3 Image Processing Integration:**
- **F.1**: Image hash and deduplication
- **F.2**: ImageKit upload integration
- **F.3**: Price-only image guards

### Test Data Requirements
- **Sample Data**: Use real Shopify and WooCommerce data from `data/samples/`
- **Test Fixtures**: Create test fixtures for sample data processing
- **Validation Data**: Expected output data for verification
- **Error Data**: Malformed or incomplete data for error testing

### Database Schema Validation
[Source: docs/db/tables.md]

**Tables to Verify:**
- **coffees**: Product information, names, descriptions, metadata
- **variants**: Product variants, weights, prices, attributes
- **prices**: Price history, currency, timestamps
- **images**: Image URLs, ImageKit URLs, metadata
- **processing_status**: Status flags, timestamps, error information

### Performance Requirements
- **Processing Time**: Full sample data processing within 5 minutes
- **Memory Usage**: Peak memory usage under 1GB
- **Database Performance**: Efficient upsert operations
- **Image Processing**: Image upload and processing within reasonable time

## Testing

### Test Execution
```bash
# Run sample data integration tests
python -m pytest tests/integration/test_sample_data_integration.py -v

# Run specific sample data tests
python -m pytest tests/integration/test_shopify_sample_data.py -v
python -m pytest tests/integration/test_woocommerce_sample_data.py -v

# Run performance tests with sample data
python -m pytest tests/performance/test_sample_data_performance.py -v
```

### Test Validation
- All sample data processes successfully through full pipeline
- Database state matches expected output
- Performance requirements met
- Error handling works correctly
- Image processing works correctly
- Price processing works correctly

## Definition of Done
- [ ] Shopify sample data processes through full pipeline
- [ ] WooCommerce sample data processes through full pipeline
- [ ] Database state verification confirms correct data storage
- [ ] Processing status flags set appropriately
- [ ] Image processing works with sample data
- [ ] Price processing works with sample data
- [ ] All parser modules handle real data correctly
- [ ] All normalizer modules process real data correctly
- [ ] Performance tests validate processing time and memory usage
- [ ] Error handling works with malformed sample data
- [ ] Test execution time remains reasonable (< 10 minutes)
- [ ] No test flakiness or intermittent failures
