# Story A.5: Raw artifact persistence (raw_payload & hashes)

## Status
Draft

## Story
**As a** system administrator,
**I want** validated artifacts to have their raw JSON, hashes, and audit fields persisted in the database,
**so that** the coffee scraper can maintain complete audit trails, enable replay capabilities, and track data lineage for debugging and compliance.

## Acceptance Criteria
1. Raw artifact JSON is stored in `coffees.source_raw` field
2. Content hash and raw payload hash are stored in `coffees.source_raw` JSON
3. Audit fields (artifact_id, created_at, collected_by) are stored in `coffees.source_raw` JSON
4. Collector signals are stored in `coffees.source_raw` JSON for debugging
5. `coffees.first_seen_at` is populated with artifact creation timestamp
6. Raw artifact persistence is integrated with A.4 RPC upsert flow
7. Comprehensive testing verifies hash integrity and audit trail completeness

## Tasks / Subtasks
- [ ] Task 1: Create raw artifact persistence service (AC: 1, 2, 3, 4)
  - [ ] Create `RawArtifactPersistence` service for handling raw data storage
  - [ ] Implement content hash and raw payload hash extraction from artifacts
  - [ ] Add audit field extraction (artifact_id, created_at, collected_by)
  - [ ] Add collector signals extraction for debugging information
- [ ] Task 2: Integrate with A.4 RPC upsert flow (AC: 6)
  - [ ] Extend `ValidatorIntegrationService` to include raw artifact persistence
  - [ ] Add raw artifact persistence to RPC upsert workflow
  - [ ] Implement transaction-like behavior for atomic operations
  - [ ] Add error handling for raw artifact persistence failures
- [ ] Task 3: Implement database field updates (AC: 5)
  - [ ] Add `first_seen_at` field population from artifact audit data
  - [ ] Update `coffees.source_raw` with complete raw artifact JSON
  - [ ] Ensure proper JSON serialization and storage
  - [ ] Add validation for required audit fields
- [ ] Task 4: Add comprehensive testing (AC: 7)
  - [ ] Create unit tests for raw artifact persistence service
  - [ ] Test hash integrity and audit trail completeness
  - [ ] Test integration with A.4 RPC upsert flow
  - [ ] Test error handling and rollback scenarios
  - [ ] Test end-to-end flow with real artifact data

## Dev Notes

### Architecture Context
[Source: docs/canonical_artifact.md#Repurposed Fields Strategy]

**Raw Data Storage Strategy:**
- **`coffees.source_raw`** → Store complete raw scraping payload including:
  - `content_hash` and `raw_payload_hash` from normalization
  - `artifact_id` for replay capability from audit section
  - `collector_signals` for debugging from collector_signals section
  - Full raw product data from platform APIs
  - Complete canonical artifact JSON for full audit trail

**Two-Pass Processing:**
1. **First Pass (Scraper)**: Store raw data in `source_raw` and `notes_raw` JSON fields
2. **Second Pass (Normalizer)**: Extract and normalize geographic data to `regions`/`estates` tables

### Canonical Artifact Fields for Persistence
[Source: docs/canonical_artifact.md]

**Raw Data Storage Fields:**
- `normalization.content_hash` → Store in `coffees.source_raw` JSON ✅ **EXISTS**
- `normalization.raw_payload_hash` → Store in `coffees.source_raw` JSON ✅ **EXISTS**
- `audit.artifact_id` → Store in `coffees.source_raw` JSON for replay ✅ **EXISTS**
- `audit.created_at` → Store in `coffees.source_raw` JSON and populate `coffees.first_seen_at` ✅ **EXISTS**
- `audit.collected_by` → Store in `coffees.source_raw` JSON ✅ **EXISTS**
- `collector_signals.*` → Store in `coffees.source_raw` JSON for debugging ✅ **EXISTS**
- Complete canonical artifact JSON → Store in `coffees.source_raw` JSON ✅ **EXISTS**

**Database Schema Requirements:**
- `coffees.source_raw` (Json) - Existing field for raw data storage ✅ **EXISTS**
- `coffees.first_seen_at` (string) - Existing field - populate from `audit.created_at` ✅ **EXISTS**
- `coffees.notes_raw` (Json) - Existing field for LLM/processing data ✅ **EXISTS**
- `coffees.tags` (string[]) - Existing field for normalized tags ✅ **EXISTS**
- `coffees.varieties` (string[]) - Existing field for coffee varieties ✅ **EXISTS**

### A.4 Integration Points
[Source: A.4 completed infrastructure]

**A.4 Foundation Available:**
- ✅ **`ValidatorIntegrationService`**: Ready to extend with raw artifact persistence
- ✅ **`RPCClient`**: Ready for additional RPC calls if needed
- ✅ **`DatabaseIntegration`**: Ready to extend with raw artifact storage methods
- ✅ **RPC Upsert Flow**: Ready to integrate raw artifact persistence

**Integration Approach:**
- Extend `ValidatorIntegrationService.process_roaster_artifacts()` to include raw artifact persistence
- Add raw artifact persistence after successful RPC upserts
- Implement transaction-like behavior for atomic operations
- Add error handling and rollback logic for persistence failures

### Raw Artifact Data Structure
[Source: docs/canonical_artifact.md]

**Complete Raw Artifact JSON Structure:**
```json
{
  "source": "shopify|woocommerce|firecrawl|manual|other",
  "roaster_domain": "hostname",
  "scraped_at": "ISO-8601-timestamp",
  "collector_meta": { "collector": "string", "job_id": "string", ... },
  "product": { "platform_product_id": "string", "title": "string", ... },
  "normalization": { "content_hash": "string", "raw_payload_hash": "string", ... },
  "collector_signals": { "response_status": 200, "download_time_ms": 532, ... },
  "audit": { "artifact_id": "string", "created_at": "ISO-8601-timestamp", "collected_by": "string" }
}
```

**Persistence Requirements:**
- Store complete artifact JSON in `coffees.source_raw`
- Extract and store hashes for deduplication and integrity
- Extract and store audit fields for compliance and replay
- Extract and store collector signals for debugging
- Populate `coffees.first_seen_at` from audit timestamp

### Database Integration
[Source: docs/db/tables.md#coffees, docs/db/rpc.md#rpc_upsert_coffee]

**RPC Functions for Raw Artifact Persistence:**
- Use existing `rpc_upsert_coffee` with `p_source_raw` parameter for raw data ✅ **EXISTS**
- Use existing `rpc_upsert_coffee` with `p_notes_raw` parameter for LLM/processing data ✅ **EXISTS**
- Ensure atomic operations with existing RPC upsert flow
- Implement proper error handling and rollback logic

**Database Schema Integration:**
- `coffees.source_raw` (Json) - Store complete raw artifact ✅ **EXISTS**
- `coffees.first_seen_at` (string) - Populate from audit.created_at ✅ **EXISTS**
- `coffees.notes_raw` (Json) - Store LLM/processing data ✅ **EXISTS**
- `coffees.tags` (string[]) - Store normalized tags ✅ **EXISTS**
- `coffees.varieties` (string[]) - Store coffee varieties ✅ **EXISTS**

### File Locations
Based on the A.4 completed structure, the raw artifact persistence should be structured as:
- Raw artifact persistence service: `src/validator/raw_artifact_persistence.py` (new)
- Integration methods: Extend existing `src/validator/integration_service.py` ✅ **EXISTS**
- Database methods: Extend existing `src/validator/database_integration.py` ✅ **EXISTS**
- RPC client methods: Extend existing `src/validator/rpc_client.py` ✅ **EXISTS**
- Configuration: `src/validator/config.py` (extend existing) ✅ **EXISTS**
- Tests: `tests/validator/test_raw_artifact_persistence.py`, `tests/validator/test_integration_persistence.py`

### A.4 Files Ready for Extension
- ✅ **`src/validator/integration_service.py`**: Ready to extend with raw artifact persistence methods
- ✅ **`src/validator/database_integration.py`**: Ready to extend with raw artifact storage methods
- ✅ **`src/validator/rpc_client.py`**: Ready to extend with raw artifact RPC calls
- ✅ **`src/validator/config.py`**: Ready to extend with raw artifact configuration
- ✅ **`tests/validator/`**: Ready to extend with raw artifact persistence tests

### Technical Constraints
- Use existing Supabase client for RPC calls
- Implement proper error handling for raw artifact persistence failures
- Support transaction-like behavior for atomic operations
- Handle large JSON payloads efficiently
- Ensure hash integrity and audit trail completeness
- Support replay capabilities through artifact_id storage

### Integration Points
- **A.4 RPC Integration**: ✅ **COMPLETED** - Extends existing RPC upsert flow with raw artifact persistence
- **Database**: ✅ **COMPLETED** - Extends existing `DatabaseIntegration` class with raw artifact storage methods
- **A.3 Validation**: ✅ **COMPLETED** - Uses validated artifacts from A.3 validation pipeline
- **A.2 Storage**: ✅ **COMPLETED** - Integrates with A.2 storage system for raw response access
- **Error Handling**: Raw artifact persistence failures are logged and artifacts marked for manual review
- **Next Stage**: Completes Epic A core pipeline - ready for Epic B (Weekly Price Job)

### Testing Requirements
[Source: architecture/8-development-testing.md#8.1]

**Integration Testing:**
- Test with staging Supabase database
- Verify raw artifact persistence with real artifact data
- Test hash integrity and audit trail completeness
- Test error scenarios and rollback behavior
- Test end-to-end flow from artifact to database

**Test Scenarios:**
- Valid artifact persistence with complete audit trail
- Hash integrity verification and deduplication
- Error handling for persistence failures
- Integration testing with A.4 RPC upsert flow
- End-to-end flow from artifact to database with raw data

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

## QA Results
*This section will be populated by QA during review*
