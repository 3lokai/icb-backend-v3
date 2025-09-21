# Story A.4: RPC upsert integration (rpc_upsert_coffee + rpc_upsert_variant)

## Status
Ready for Development

## Story
**As a** system administrator,
**I want** validated artifacts transformed into RPC payloads and upserted to the database,
**so that** the coffee scraper can persist product data using the existing database schema and RPC functions.

## Acceptance Criteria
1. Validated artifacts are transformed into RPC payloads for `rpc_upsert_coffee` and `rpc_upsert_variant`
2. RPC calls are made with correct payloads and return coffee/variant IDs
3. Database rows are created/updated in staging Supabase
4. Idempotency is maintained for retry scenarios
5. Error handling covers RPC failures and database constraints
6. Metadata-only flag support is implemented for price-only updates
7. Integration tests verify end-to-end artifact → database flow

## Tasks / Subtasks
- [ ] Task 1: Create RPC client wrapper (AC: 2, 5)
  - [ ] Implement RPC client wrapper for Supabase RPC calls
  - [ ] Add error handling for RPC failures and database constraints
  - [ ] Implement retry logic with exponential backoff
  - [ ] Add logging for RPC call success/failure
- [ ] Task 2: Implement artifact transformation logic (AC: 1, 6)
  - [ ] Create artifact to RPC payload mapper
  - [ ] Map canonical artifact fields to `rpc_upsert_coffee` parameters
  - [ ] Map variant data to `rpc_upsert_variant` parameters
  - [ ] Implement metadata-only flag for price-only updates
- [ ] Task 3: Add price history integration (AC: 1, 2)
  - [ ] Implement `rpc_insert_price` calls for each variant
  - [ ] Handle price comparison logic (sale vs regular price)
  - [ ] Add currency validation and normalization
  - [ ] Implement price history deduplication
- [ ] Task 4: Extend existing integration service (AC: 2, 3, 7)
  - [ ] Add RPC transformation methods to existing `ValidatorIntegrationService`
  - [ ] Add transaction-like behavior for atomic operations
  - [ ] Implement idempotency checks using composite keys
  - [ ] Add comprehensive error handling and rollback logic
- [ ] Task 5: Add comprehensive testing (AC: 3, 7)
  - [ ] Create integration tests with staging database
  - [ ] Test idempotency with duplicate artifacts
  - [ ] Test error scenarios and rollback behavior
  - [ ] Test metadata-only flag functionality
  - [ ] Test end-to-end flow with real artifact data

## Dev Notes

### Architecture Context
[Source: architecture/2-component-architecture.md#2.6]

**Transformer & RPCs:**
- Atomic Operations: All writes through server-side RPCs
- Idempotency: Composite keys for safe retries
- Data Storage Strategy: Raw scraping data → `coffees.source_raw` (JSON), LLM enrichment → `coffees.notes_raw` (JSON)
- RPC Functions: `rpc_upsert_coffee`, `rpc_upsert_variant`, `rpc_insert_price`, `rpc_upsert_coffee_image`

### RPC Function Specifications
[Source: db/rpc.md]

**rpc_upsert_coffee Parameters:**
- `p_bean_species` (species_enum): Coffee species
- `p_decaf` (boolean, optional): Whether coffee is decaffeinated
- `p_description_md` (string): Markdown description
- `p_direct_buy_url` (string): Direct purchase URL
- `p_name` (string): Coffee name
- `p_notes_raw` (Json, optional): Raw notes data
- `p_platform_product_id` (string): Platform product ID
- `p_process` (process_enum): Processing method
- `p_process_raw` (string): Raw process description
- `p_roast_level` (roast_level_enum): Roast level
- `p_roast_level_raw` (string): Raw roast level description
- `p_roast_style_raw` (string): Roast style description
- `p_roaster_id` (string): Roaster ID
- `p_slug` (string): URL-friendly slug
- `p_source_raw` (Json, optional): Raw source data
- `p_status` (coffee_status_enum, optional): Coffee status

**rpc_upsert_variant Parameters:**
- `p_coffee_id` (string): Coffee ID
- `p_platform_variant_id` (string): Platform variant ID
- `p_sku` (string): SKU
- `p_weight_g` (number): Weight in grams
- `p_grind` (grind_enum, optional): Grind type
- `p_pack_count` (number, optional): Number of packs
- `p_currency` (string, optional): Currency code
- `p_in_stock` (boolean, optional): Stock status
- `p_stock_qty` (number, optional): Stock quantity
- `p_subscription_available` (boolean, optional): Subscription availability
- `p_compare_at_price` (number, optional): Compare at price
- `p_source_raw` (Json, optional): Raw source data

**rpc_insert_price Parameters:**
- `p_variant_id` (string): Variant ID
- `p_price` (number): Price value
- `p_currency` (string, optional): Currency code
- `p_is_sale` (boolean, optional): Whether price is a sale
- `p_scraped_at` (string, optional): Scraping timestamp
- `p_source_url` (string, optional): Source URL
- `p_source_raw` (Json, optional): Raw source data

### Canonical Artifact Mapping
[Source: docs/canonical_artifact.md]

**Key Mappings:**
- `product.platform_product_id` → `p_platform_product_id`
- `product.title` / `normalization.name_clean` → `p_name`
- `product.slug` → `p_slug`
- `product.description_md` / `normalization.description_md_clean` → `p_description_md`
- `normalization.roast_level_enum` → `p_roast_level`
- `normalization.roast_level_raw` → `p_roast_level_raw`
- `normalization.process_enum` → `p_process`
- `normalization.process_raw` → `p_process_raw`
- `normalization.bean_species` → `p_bean_species`
- `variants[].platform_variant_id` → `p_platform_variant_id`
- `variants[].sku` → `p_sku`
- `variants[].grams` → `p_weight_g`
- `variants[].currency` → `p_currency`
- `variants[].in_stock` → `p_in_stock`
- `variants[].price_decimal` → `p_price` (for rpc_insert_price)
- `variants[].compare_at_price_decimal` → `p_compare_at_price`

### Data Storage Strategy
[Source: docs/canonical_artifact.md#Repurposed Fields Strategy]

**Raw Data Storage:**
- `coffees.source_raw` → Store complete raw scraping payload including content_hash, raw_payload_hash, artifact_id, collector_signals
- `coffees.notes_raw` → Store LLM enrichment, processing data, geographic data for second-pass normalization

**Two-Pass Processing:**
1. First Pass (Scraper): Store raw data in `source_raw` and `notes_raw` JSON fields
2. Second Pass (Normalizer): Extract and normalize geographic data to `regions`/`estates` tables

### Integration Points
- **A.3 Validator**: ✅ **COMPLETED** - Extends existing `ValidatorIntegrationService` to add RPC transformation
- **Database**: ✅ **COMPLETED** - Extends existing `DatabaseIntegration` class with RPC client methods  
- **Existing Infrastructure**: ✅ **COMPLETED** - Leverages existing Supabase client and validation pipeline
- **A.5 Raw Artifact Storage**: Will integrate with raw artifact persistence
- **Error Handling**: Invalid RPC calls are logged and artifacts marked for manual review
- **Next Stage**: Passes successful upserts to A.5 for raw artifact metadata persistence

### A.3 Foundation Available
**✅ A.3 COMPLETED** - The following infrastructure is ready for A.4 to extend:

- **`ValidatorIntegrationService`**: Main integration service with comprehensive validation pipeline
- **`DatabaseIntegration`**: Database operations with Supabase client integration
- **`ArtifactValidator`**: Pydantic v2 validation with canonical schema support
- **`ValidationPipeline`**: Orchestration of validation process
- **`StorageReader`**: A.2 storage integration for reading raw responses
- **Complete Test Suite**: 56 tests covering all validation scenarios

### Technical Constraints
- Use existing Supabase client for RPC calls
- Implement proper error handling for database constraints
- Support idempotency through composite keys
- Handle currency normalization and validation
- Implement proper transaction-like behavior
- Support metadata-only updates for price-only scenarios

### Course Corrections Based on A.3 Completion
**✅ A.3 COMPLETED** - This story extends the completed A.3 infrastructure:

1. **Extend A.3 Services**: Add RPC methods to existing `ValidatorIntegrationService` and `DatabaseIntegration` classes
2. **Leverage A.3 Infrastructure**: Use existing Supabase client, validation pipeline, and database integration from A.3
3. **Build on A.3 Foundation**: Extend the validation pipeline to include RPC transformation and database persistence
4. **Maintain A.3 Patterns**: Follow the same patterns established in A.1, A.2, and A.3 for consistency
5. **Incremental Development**: Add RPC functionality as an extension to the existing validator module rather than a separate transformer module

### A.3 Integration Points Ready
- **`ValidatorIntegrationService.process_roaster_artifacts()`**: Ready to extend with RPC transformation
- **`DatabaseIntegration.store_batch_validation_results()`**: Ready to extend with RPC upsert calls
- **`ValidationPipeline.process_storage_artifacts()`**: Ready to extend with RPC persistence
- **Existing Supabase Client**: Ready for RPC calls with proper error handling
- **Validation Results**: Ready to transform into RPC payloads

### File Locations
Based on the A.3 completed structure, the RPC integration should be structured as:
- RPC client wrapper: `src/validator/rpc_client.py` (new)
- Artifact mapper: `src/validator/artifact_mapper.py` (new)
- RPC integration methods: Extend existing `src/validator/database_integration.py` ✅ **EXISTS**
- RPC transformation service: Extend existing `src/validator/integration_service.py` ✅ **EXISTS**
- Configuration: `src/validator/config.py` (extend existing) ✅ **EXISTS**
- Tests: `tests/validator/test_rpc_client.py`, `tests/validator/test_artifact_mapper.py`, `tests/validator/test_rpc_integration.py`

### A.3 Files Ready for Extension
- ✅ **`src/validator/integration_service.py`**: Ready to extend with RPC transformation methods
- ✅ **`src/validator/database_integration.py`**: Ready to extend with RPC client methods
- ✅ **`src/validator/config.py`**: Ready to extend with RPC configuration
- ✅ **`tests/validator/`**: Ready to extend with RPC integration tests

### Testing Requirements
[Source: architecture/8-development-testing.md#8.1]

**Integration Testing:**
- Test with staging Supabase database
- Verify RPC calls with real artifact data
- Test idempotency with duplicate artifacts
- Test error scenarios and rollback behavior
- Test metadata-only flag functionality

**Test Scenarios:**
- Valid artifact transformation and RPC calls
- Error handling for invalid data
- Idempotency testing with duplicate artifacts
- Price history insertion and deduplication
- End-to-end flow from artifact to database

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation | Bob (Scrum Master) |

## Dev Agent Record
*This section will be populated by the development agent during implementation*

### Agent Model Used
*To be filled by dev agent*

### Debug Log References
*To be filled by dev agent*

### Completion Notes List
*To be filled by dev agent*

### File List
*To be filled by dev agent*
