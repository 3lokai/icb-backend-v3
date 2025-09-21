# Story A.3: Artifact validation (Pydantic models)

## Status
Done

## Story
**As a** system administrator,
**I want** Pydantic v2 models generated from the canonical JSON schema to validate fetched product artifacts,
**so that** the coffee scraper can ensure data quality and catch invalid artifacts before processing.

## Acceptance Criteria
1. Pydantic v2 models are generated from the canonical JSON schema
2. Example fixture validates successfully against the model
3. Invalid artifacts produce detailed validation errors
4. Invalid artifacts are persisted for manual review
5. Validation errors are logged with artifact context
6. Model supports all required and optional fields from schema
7. Validation handles edge cases (null values, type coercion, enum validation)

## Tasks / Subtasks
- [x] Task 1: Generate Pydantic models from JSON schema (AC: 1, 6)
  - [x] Create script to convert JSON schema to Pydantic v2 models
  - [x] Generate base artifact model with all required fields
  - [x] Generate nested models for product, variants, images, normalization
  - [x] Add proper type hints and field validation
- [x] Task 2: Implement validation pipeline (AC: 2, 3, 5)
  - [x] Create artifact validator service
  - [x] Add validation error handling and reporting
  - [x] Implement detailed error logging with artifact context
  - [x] Add validation result persistence
- [x] Task 3: Create test fixtures and validation tests (AC: 2, 7)
  - [x] Create valid artifact fixture from canonical example
  - [x] Create invalid artifact fixtures for error testing
  - [x] Test edge cases (null values, type coercion, enum validation)
  - [x] Test validation error messages and context
- [x] Task 4: Integration with fetcher pipeline (AC: 4)
  - [x] Integrate validator with A.2's ResponseStorage for reading stored raw responses
  - [x] Add invalid artifact persistence to database
  - [x] Implement manual review workflow for invalid artifacts
  - [x] Add validation metrics and monitoring

## Dev Notes

### Architecture Context
[Source: architecture/2-component-architecture.md#2.4]

**Validator Specifications:**
- Technology: Pydantic v2 models from canonical JSON schema
- Validation: Strict schema compliance with detailed error reporting
- Persistence: Raw artifacts to S3/Supabase Storage for replay
- Error Handling: Invalid artifacts marked for manual review
- Artifact Storage: Store in `scrape_artifacts` table with run tracking

### Canonical Artifact Schema
[Source: docs/canonical_artifact.md]

**Required Fields:**
- `source`: Origin (shopify, woocommerce, firecrawl, manual, other)
- `roaster_domain`: Store domain (hostname format)
- `scraped_at`: ISO 8601 timestamp
- `product`: Product object with platform identifiers and variants

**Key Product Fields:**
- `platform_product_id`: Unique identifier from source platform
- `title`, `handle`, `description_html/md`: Product information
- `source_url`: Original product URL
- `variants`: Array of product variants with pricing and inventory
- `images`: Array with url, alt_text, order, source_id

**Normalization Fields:**
- `is_coffee`: Boolean coffee classification
- `content_hash`: Hash of normalized content for change detection
- `name_clean`, `description_md_clean`: Cleaned text fields
- `roast_level_enum`, `process_enum`: Standardized enums
- `varieties`, `region`, `country`, `altitude_m`: Geographic data
- `llm_enrichment`: LLM-generated data with confidence score
- `sensory_params`: Sensory analysis data

### Database Schema Context
[Source: db/tables.md#scrape_artifacts]

**Scrape Artifacts Table (Already Implemented):**
The `scrape_artifacts` table contains all necessary fields for storing validation results:
- `id` (string) - Primary key
- `scrape_run_id` (string) - Foreign key to scrape_runs table
- `artifact_data` (jsonb) - Raw artifact JSON data
- `validation_status` (text) - Status (valid, invalid, pending_review)
- `validation_errors` (jsonb) - Detailed validation error information
- `created_at` (timestamptz) - Creation timestamp
- `processed_at` (timestamptz) - Processing completion timestamp

### Core Data Flow
[Source: architecture/1-core-data-flow.md#1.1]

**Full Pipeline (Monthly):**
1. **Fetch** → Store JSON endpoints (Shopify/Woo) as primary source (A.2 with ResponseStorage)
2. **Validate** → Pydantic v2 validation against canonical artifact schema (A.3)
3. **Persist** → Raw artifact pointer/hashes to S3/Supabase Storage

**A.2 → A.3 Integration:**
- A.2 stores raw responses in `data/fetcher/{platform}/` with metadata
- A.3 reads stored responses from A.2's storage system
- A.3 validates against canonical schema and stores results in database

### Validation Requirements
[Source: architecture/2-component-architecture.md#2.4]

**Validation Features:**
- Strict schema compliance with detailed error reporting
- Support for all required and optional fields from canonical schema
- Proper handling of nested objects (product, variants, images, normalization)
- Enum validation for source, platform, roast_level_enum, process_enum
- Type coercion for numeric fields (price_decimal, altitude_m, etc.)
- Null value handling for optional fields
- Date/time validation for scraped_at, created_at fields

### Error Handling and Persistence
[Source: architecture/2-component-architecture.md#2.4]

**Invalid Artifact Handling:**
- Mark invalid artifacts for manual review
- Store detailed validation errors in `scrape_artifacts.validation_errors`
- Persist raw artifact data for replay and debugging
- Log validation errors with artifact context for monitoring
- Implement retry logic for transient validation failures

### Testing Requirements
[Source: architecture/8-development-testing.md#8.1]

**Local Development:**
- Docker Compose: Worker + local Supabase emulator + mock endpoints
- Environment Variables: Same as Fly to minimize surprises
- Testing: Unit tests for parsers, integration tests with staging DB

**Test Scenarios:**
- Valid artifact validation against canonical example
- Invalid artifact error handling and reporting
- Edge case testing (null values, type coercion, enum validation)
- Integration testing with fetcher pipeline
- Manual review workflow testing

### File Locations
Based on the architecture, the validator should be structured as:
- Main validator service: `src/validator/artifact_validator.py`
- Pydantic models: `src/validator/models.py`
- Validation pipeline: `src/validator/validation_pipeline.py`
- A.2 Storage integration: `src/validator/storage_reader.py` (reads from A.2's ResponseStorage)
- Configuration: `src/config/validator_config.py`
- Tests: `tests/validator/test_artifact_validator.py`, `tests/validator/test_models.py`, `tests/validator/test_storage_reader.py`

### Integration Points
- **Fetcher Pipeline**: Receives raw artifacts from fetcher service with storage integration
- **A.2 Storage Integration**: Uses A.2's ResponseStorage for reading stored raw responses from `data/fetcher/` directory
- **Database**: Stores validation results in scrape_artifacts table
- **Storage**: Persists raw artifacts for replay and debugging using A.2's storage system
- **Logging**: Emits validation metrics for monitoring
- **Next Stage**: Passes valid artifacts to normalizer for processing

### Technical Constraints
- Use Pydantic v2 with modern field validation
- Support for complex nested object validation
- Proper error message formatting for debugging
- Integration with existing database schema
- Performance optimization for large artifact volumes
- Support for schema evolution and backward compatibility

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation | Bob (Scrum Master) |

## Dev Agent Record
*This section will be populated by the development agent during implementation*

### Agent Model Used
Claude Sonnet 4

### Debug Log References
- Initial implementation of Pydantic models
- Validation pipeline implementation
- Test fixture creation
- Integration with A.2 storage system
- Pydantic v2 migration and compatibility fixes
- Test suite execution and validation

### Completion Notes List
- [x] Generated Pydantic v2 models from canonical JSON schema
- [x] Implemented comprehensive validation pipeline
- [x] Created test fixtures and validation tests
- [x] Integrated with A.2's ResponseStorage system
- [x] Added database integration for invalid artifacts
- [x] Implemented manual review workflow
- [x] Added validation metrics and monitoring
- [x] Migrated all Pydantic code to v2 compatibility
- [x] Fixed all test failures and warnings
- [x] Ensured full test coverage (56 tests passing)

### File List
- `src/validator/models.py` - Pydantic v2 models
- `src/validator/artifact_validator.py` - Validation service
- `src/validator/storage_reader.py` - A.2 integration
- `src/validator/validation_pipeline.py` - Pipeline orchestration
- `src/validator/database_integration.py` - Database operations
- `src/validator/integration_service.py` - Main integration service
- `src/validator/config.py` - Configuration
- `tests/validator/fixtures.py` - Test fixtures
- `tests/validator/test_*.py` - Comprehensive test suite

## QA Results

### Review Date: 2025-01-12

### Reviewed By: Quinn (Test Architect)

### Code Quality Assessment

**EXCELLENT** - This is a high-quality implementation that demonstrates thorough understanding of requirements and best practices. The code shows:

- **Perfect Schema Alignment**: Pydantic models exactly match the canonical artifact schema with all required fields, enums, and validation rules
- **Comprehensive Pydantic v2 Models**: Well-structured models with proper type hints, field validation, and enum support
- **Robust Error Handling**: Detailed validation error reporting with context and artifact information
- **Clean Architecture**: Well-separated concerns with dedicated services for validation, storage, database integration, and pipeline orchestration
- **Excellent Test Coverage**: 56 tests covering all scenarios including edge cases, error conditions, and integration points
- **Proper Integration**: Seamless integration with A.2's ResponseStorage system and database schema
- **Canonical Validation**: Successfully validates the complete canonical example from docs/canonical_artifact.md

### Refactoring Performed

No refactoring was needed - the code is already well-structured and follows best practices.

### Compliance Check

- **Coding Standards**: ✓ Follows Python best practices with proper type hints, docstrings, and error handling
- **Project Structure**: ✓ Properly organized in `src/validator/` with clear separation of concerns
- **Testing Strategy**: ✓ Comprehensive test suite with 56 tests covering all acceptance criteria
- **All ACs Met**: ✓ All 7 acceptance criteria fully implemented and tested

### Improvements Checklist

- [x] Pydantic v2 models generated from canonical JSON schema (AC 1, 6)
- [x] Example fixture validates successfully against the model (AC 2)
- [x] Invalid artifacts produce detailed validation errors (AC 3)
- [x] Invalid artifacts are persisted for manual review (AC 4)
- [x] Validation errors are logged with artifact context (AC 5)
- [x] Model supports all required and optional fields from schema (AC 6)
- [x] Validation handles edge cases (null values, type coercion, enum validation) (AC 7)

### Security Review

**PASS** - No security concerns identified. The validator properly handles:
- Input validation through Pydantic models
- Safe error handling without information leakage
- Proper data sanitization in validation pipeline

### Performance Considerations

**PASS** - Performance is well-optimized:
- Efficient batch processing in validation pipeline
- Proper error handling without performance impact
- Memory-efficient artifact processing
- Good separation of concerns for scalability

### Files Modified During Review

No files were modified during review - the implementation is already production-ready.

### Gate Status

Gate: **PASS** → docs/qa/gates/A.3-artifact-validation-pydantic-models.yml
Risk profile: docs/qa/assessments/A.3-risk-20250112.md
NFR assessment: docs/qa/assessments/A.3-nfr-20250112.md

### Recommended Status

**✓ Ready for Done** - All acceptance criteria met, comprehensive test coverage, and production-ready implementation.
