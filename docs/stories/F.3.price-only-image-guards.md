# Story F.3: Price-only must not touch images

## Status
Draft

## Story
**As a** system administrator,
**I want** strict enforcement that price-only runs never trigger image uploads or processing,
**so that** I can maintain fast, lightweight price updates without unnecessary image operations.

## Acceptance Criteria
1. Code path guards prevent image processing during price-only runs
2. Unit tests assert image upload/processing not called during price-only execution
3. Integration tests validate price-only pipeline skips all image operations
4. Performance tests confirm price-only runs maintain speed without image overhead
5. Error handling for edge cases where image processing might be triggered
6. Comprehensive logging for price-only vs full pipeline execution paths
7. CI smoke tests validate price-only image guard enforcement

## Tasks / Subtasks
- [ ] Task 1: Price-only guard implementation (AC: 1, 5, 6)
  - [ ] Add `metadata_only` flag checks in image processing code paths
  - [ ] Implement guard clauses in `ArtifactMapper._map_images_data()`
  - [ ] Add guard clauses in `DatabaseIntegration.upsert_artifact_via_rpc()`
  - [ ] Create guard clauses in `RPCClient.upsert_coffee_image()`
  - [ ] Add comprehensive error handling for guard violations
  - [ ] Create detailed logging for price-only vs full pipeline execution
- [ ] Task 2: Unit test coverage for image guards (AC: 2, 5)
  - [ ] Test `ArtifactMapper` skips image processing when `metadata_only=True`
  - [ ] Test `DatabaseIntegration` skips image upserts when `metadata_only=True`
  - [ ] Test `RPCClient` skips image RPC calls when `metadata_only=True`
  - [ ] Test error handling for guard violations
  - [ ] Test logging output for price-only execution paths
  - [ ] Test edge cases where image processing might be triggered
- [ ] Task 3: Integration test coverage (AC: 3, 6)
  - [ ] End-to-end test for price-only pipeline skipping image operations
  - [ ] Test B.1-B.3 price-only workflow with image guard enforcement
  - [ ] Test A.1-A.5 full pipeline with image processing enabled
  - [ ] Test mixed scenarios with both price-only and full pipeline runs
  - [ ] Test error scenarios and guard violation handling
  - [ ] Test logging and monitoring for different execution paths
- [ ] Task 4: Performance validation and CI tests (AC: 4, 7)
  - [ ] Performance tests comparing price-only vs full pipeline execution
  - [ ] Benchmark tests for price-only runs without image overhead
  - [ ] CI smoke tests for price-only image guard enforcement
  - [ ] Load tests for price-only pipeline under high volume
  - [ ] Monitoring tests for price-only execution metrics
  - [ ] Documentation tests for price-only vs full pipeline differences

## Dev Technical Guidance

### Existing Infrastructure Integration
[Source: Epic F requirements and B.1-B.3 implementation]

**B.1-B.3 Price-Only Pipeline Integration:**
- **Price Fetcher**: Uses `metadata_only=True` flag in B.1 price-only fetcher ✅ **EXISTS**
- **RPC Integration**: B.2 uses `metadata_only=True` for price-only RPC calls ✅ **EXISTS**
- **Pipeline Flow**: B.3 monitoring tracks price-only vs full pipeline execution ✅ **EXISTS**
- **Guard Enforcement**: Extends existing `metadata_only` flag usage throughout pipeline

**A.1-A.5 Full Pipeline Integration:**
- **Image Processing**: A.1-A.5 pipeline processes images when `metadata_only=False` ✅ **EXISTS**
- **Database Integration**: Full pipeline includes image upserts via RPC calls ✅ **EXISTS**
- **Pipeline Flow**: Full pipeline includes all artifact processing including images ✅ **EXISTS**

### Price-Only Guard Implementation Strategy
[Source: Epic F requirements]

**Guard Implementation Pattern:**
```python
class ImageProcessingGuard:
    def __init__(self, metadata_only: bool):
        self.metadata_only = metadata_only
        self.logger = get_logger(__name__)
    
    def check_image_processing_allowed(self, operation: str) -> bool:
        """Check if image processing is allowed for current operation"""
        if self.metadata_only:
            self.logger.warning(
                "Image processing blocked for price-only run",
                operation=operation,
                metadata_only=self.metadata_only
            )
            return False
        return True
    
    def guard_image_processing(self, operation: str, func: Callable, *args, **kwargs):
        """Guard wrapper for image processing operations"""
        if not self.check_image_processing_allowed(operation):
            self.logger.info(
                "Skipping image processing for price-only run",
                operation=operation
            )
            return None
        return func(*args, **kwargs)
```

**Integration Points:**
- **ArtifactMapper**: Guard `_map_images_data()` when `metadata_only=True`
- **DatabaseIntegration**: Guard image upserts when `metadata_only=True`
- **RPCClient**: Guard `upsert_coffee_image()` when `metadata_only=True`

### Integration Points
[Source: B.1-B.3 and A.1-A.5 implementation patterns]

**B.1-B.3 Price-Only Integration:**
- **Price Fetcher**: B.1 sets `metadata_only=True` for price-only runs
- **RPC Integration**: B.2 uses `metadata_only=True` for price-only RPC calls
- **Monitoring**: B.3 tracks price-only execution metrics
- **Guard Enforcement**: Extend existing `metadata_only` flag usage

**A.1-A.5 Full Pipeline Integration:**
- **Image Processing**: A.1-A.5 processes images when `metadata_only=False`
- **Database Integration**: Full pipeline includes image upserts
- **Pipeline Flow**: Full pipeline includes all artifact processing

### File Locations
Based on Epic F requirements and B.1-B.3/A.1-A.5 integration:

**New Files:**
- Image guard service: `src/images/processing_guard.py` (new)
- Guard utilities: `src/images/guard_utils.py` (new)
- Integration tests: `tests/images/test_price_only_guards.py` (new)
- Performance tests: `tests/images/test_price_only_performance.py` (new)

**Extension Files (Modify Existing):**
- Extend existing: `src/validator/artifact_mapper.py` ✅ **EXISTS** (add image guards)
- Extend existing: `src/validator/database_integration.py` ✅ **EXISTS** (add image guards)
- Extend existing: `src/validator/rpc_client.py` ✅ **EXISTS** (add image guards)
- Extend existing: `tests/validator/test_artifact_mapper.py` ✅ **EXISTS** (add guard tests)

**Configuration Files:**
- Guard configuration: `src/images/guard_config.py` (new)
- Test fixtures: `tests/images/fixtures/price_only_scenarios.json` (new)
- Documentation: `docs/images/price_only_guards.md` (new)

### Performance Requirements
[Source: Epic F requirements]

**Price-Only Performance:**
- **Execution Speed**: Price-only runs must be 3x faster than full pipeline
- **Memory Usage**: Price-only runs must use 50% less memory than full pipeline
- **Network Usage**: Price-only runs must avoid all image download/upload operations
- **Database Operations**: Price-only runs must skip all image-related RPC calls

**Guard Performance:**
- **Guard Overhead**: Image guards must add <1ms overhead per operation
- **Logging Performance**: Guard logging must not impact execution speed
- **Error Handling**: Guard violations must be handled efficiently

### Testing Strategy
[Source: Epic F requirements]

**Unit Tests:**
- Image guard functionality across all components
- `metadata_only` flag handling in image processing
- Error handling for guard violations
- Logging output for price-only execution

**Integration Tests:**
- B.1-B.3 price-only pipeline with image guards
- A.1-A.5 full pipeline with image processing
- Mixed scenarios with both execution paths
- End-to-end validation of guard enforcement

**Performance Tests:**
- Price-only vs full pipeline execution speed
- Memory usage comparison for different execution paths
- Network usage validation for price-only runs
- Load testing for price-only pipeline under high volume

**CI Smoke Tests:**
- Price-only image guard enforcement
- Full pipeline image processing
- Mixed execution scenarios
- Error handling and guard violations

## Definition of Done
- [ ] Image processing guards implemented across all components
- [ ] Unit tests assert image operations blocked during price-only runs
- [ ] Integration tests validate price-only pipeline skips image operations
- [ ] Performance tests confirm price-only runs maintain speed
- [ ] Error handling for guard violations implemented
- [ ] Comprehensive logging for different execution paths
- [ ] CI smoke tests validate guard enforcement
- [ ] Documentation updated with price-only vs full pipeline differences

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation with B.1-B.3 and A.1-A.5 integration strategy | Bob (Scrum Master) |
