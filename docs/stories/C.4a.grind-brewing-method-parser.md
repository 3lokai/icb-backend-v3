# Story C.4a: Grind/Brewing Method Parser (from Variants)

## Status
Draft

## Story
**As a** data processing engineer,
**I want** to parse grind types and brewing methods from product variants to enhance the existing coffee artifact mapping,
**so that** I can provide consistent grind categorization for coffee products following the established C.2 pattern without creating separate database operations.

## Acceptance Criteria
1. Grind types parsed from product variants into `p_grind` parameter (variant-level)
2. Brewing methods parsed from product variants into `p_grind` parameter (variant-level)
3. Ambiguous cases flagged in `parsing_warnings` with confidence scoring
4. Integration with A.1-A.5 pipeline through ValidatorIntegrationService composition
5. Enhancement of `ArtifactMapper._map_variants_data()` following C.1 pattern
6. Use existing `rpc_upsert_variant()` with existing `p_grind` parameter
7. Comprehensive test coverage for grind and brewing method detection
8. Performance optimized for batch processing of variant data

## Tasks / Subtasks
- [ ] Task 1: Grind/Brewing Method parser library implementation (AC: 1, 2, 3, 7, 8)
  - [ ] Create `GrindBrewingParser` standalone library (following C.1 pattern)
  - [ ] Implement grind/brewing method detection from variant titles/options/attributes
  - [ ] Add confidence scoring for grind/brewing detection accuracy
  - [ ] Create batch processing optimization for multiple variants
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for grind/brewing detection accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 2: A.4 RPC Integration - ArtifactMapper grind/brewing parsing (AC: 4, 5)
  - [ ] Extend `ArtifactMapper._map_variants_data()` to include grind/brewing parsing
  - [ ] Integrate grind/brewing parser with variant transformation process
  - [ ] Add `p_grind` parameter to `rpc_upsert_variant` calls
  - [ ] Handle grind/brewing parsing errors and warnings in variant processing
  - [ ] Add comprehensive tests for A.4 RPC integration

- [ ] Task 3: A.1-A.5 Pipeline Integration - ValidatorIntegrationService (AC: 4, 5)
  - [ ] Integrate grind/brewing parsing with `ValidatorIntegrationService`
  - [ ] Add grind/brewing processing to artifact validation pipeline
  - [ ] Extend `DatabaseIntegration.upsert_artifact_via_rpc()` for grind/brewing processing
  - [ ] Add grind/brewing parsing to `ValidationPipeline` processing flow
  - [ ] Create integration tests with A.1-A.5 pipeline

## Dev Notes
[Source: Epic C requirements and A.1-A.5 implementation patterns]

**⚠️ IMPORTANT: DO NOT CREATE NEW MIGRATIONS**
- The migration `extend_rpc_upsert_coffee_epic_c_parameters.sql` already handles ALL Epic C parameters
- This includes C.3 (tags/notes), C.4 (grind/species), C.5 (varieties/geographic), C.6 (sensory/hash), and C.7 (text cleaning)
- Dev should use the existing enhanced RPC function with `p_default_grind` parameter
- No additional database migrations needed for this story

### Grind/Brewing Method Parser Strategy
[Source: Epic C requirements and C.1 weight parser pattern]

**Variant-Based Detection (following C.1 pattern):**
```python
class GrindBrewingParser:
    def __init__(self):
        # Grind/brewing patterns (aligned with C.1 weight parser patterns)
        self.grind_patterns = {
            'whole': [r'whole\s*bean', r'beans?', r'coffee\s*beans?'],
            'espresso': [r'espresso', r'home\s*espresso', r'commercial\s*espresso'],
            'filter': [r'filter', r'drip', r'coffee\s*filter'],
            'pour_over': [r'pour\s*over', r'pourover', r'chemex', r'v60', r'kalita'],
            'french_press': [r'french\s*press', r'french'],
            'moka_pot': [r'moka\s*pot', r'mokapot', r'moka', r'mocha\s*pot'],
            'cold_brew': [r'cold\s*brew', r'coldbrew', r'channi'],
            'aeropress': [r'aero\s*press', r'aeropress', r'inverted\s*aeropress'],
            'south_indian_filter': [r'south\s*indian\s*filter', r'south\s*indian'],
            'syphon': [r'syphon', r'vacuum']
        }
    
    def parse_grind_brewing(self, variant: Dict) -> GrindBrewingResult:
        """Parse grind/brewing method from single variant (following C.1 pattern)"""
        try:
            # Extract grind/brewing from variant title (primary source)
            variant_title = variant.get('title', '')
            grind_type = self._detect_from_text(variant_title)
            
            if grind_type != 'unknown':
                return GrindBrewingResult(
                    grind_type=grind_type,
                    confidence=0.9,
                    source='variant_title',
                    warnings=[],
                    original_text=variant_title
                )
            
            # Fallback to options parsing (Shopify)
            if 'options' in variant and len(variant['options']) > 1:
                option2 = variant['options'][1]  # Second option is typically grind/brewing
                grind_type = self._detect_from_text(option2)
                if grind_type != 'unknown':
                    return GrindBrewingResult(
                        grind_type=grind_type,
                        confidence=0.8,
                        source='variant_option',
                        warnings=[],
                        original_text=option2
                    )
            
            # Fallback to attributes parsing (WooCommerce)
            if 'attributes' in variant:
                for attr in variant['attributes']:
                    if attr.get('name', '').lower() in ['grind size', 'grind']:
                        for term in attr.get('terms', []):
                            grind_type = self._detect_from_text(term.get('name', ''))
                            if grind_type != 'unknown':
                                return GrindBrewingResult(
                                    grind_type=grind_type,
                                    confidence=0.8,
                                    source='variant_attribute',
                                    warnings=[],
                                    original_text=term.get('name', '')
                                )
            
            return GrindBrewingResult(
                grind_type='unknown',
                confidence=0.0,
                source='no_match',
                warnings=['No grind/brewing method detected in variant'],
                original_text=variant_title
            )
            
        except Exception as e:
            return GrindBrewingResult(
                grind_type='unknown',
                confidence=0.0,
                source='error',
                warnings=[f'Error parsing variant: {str(e)}'],
                original_text=str(variant)
            )
    
    def _detect_from_text(self, text: str) -> str:
        """Detect grind type from text using patterns (following C.1 pattern)"""
        text_lower = text.lower()
        
        for grind_type, patterns in self.grind_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return grind_type
        
        return 'unknown'
```

**GrindBrewingResult Object (following C.1 WeightResult pattern):**
```python
@dataclass
class GrindBrewingResult:
    grind_type: str
    confidence: float  # 0.0 to 1.0
    source: str  # 'variant_title', 'variant_option', 'variant_attribute', 'no_match', 'error'
    warnings: List[str]
    original_text: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage (aligned with C.1 WeightResult)."""
        return {
            'grind_type': self.grind_type,
            'confidence': self.confidence,
            'source': self.source,
            'warnings': self.warnings,
            'original_text': self.original_text
        }
```

### Database Schema Alignment
[Source: docs/db/enums.md and canonical_artifact.md]

**Grind Enum Values (from database):**
- `whole`, `filter`, `espresso`, `omni`, `other`, `turkish`, `moka`, `cold_brew`, `aeropress`, `channi`
- `coffee filter`, `cold brew`, `french press`, `home espresso`, `commercial espresso`
- `inverted aeropress`, `south indian filter`, `moka pot`, `pour over`

**Canonical Artifact Mapping:**
- `normalization.default_grind` → `coffees.default_grind` (via `rpc_upsert_coffee`)
- Store in `normalization` section of artifact for processing
- Use existing `grind_enum` from database schema

### A.4 RPC Integration (CRITICAL)
[Source: A.4 completed RPC infrastructure - following C.1 pattern]

**Existing A.4 RPC Infrastructure:**
- ✅ **ArtifactMapper**: `_map_variants_data()` method for variant transformation ✅ **EXISTS**
- ✅ **RPCClient**: `upsert_variant()` method with `p_grind` parameter ✅ **EXISTS**
- ✅ **DatabaseIntegration**: `upsert_artifact_via_rpc()` for variant processing ✅ **EXISTS**
- ✅ **RPC Function**: `rpc_upsert_variant` expects `p_grind` parameter ✅ **EXISTS**

**A.4 Integration Strategy (following C.1 pattern):**
```python
# Extend ArtifactMapper._map_variants_data() with grind/brewing parsing
class ArtifactMapper:
    def _map_variants_data(self, artifact: ArtifactModel) -> List[Dict[str, Any]]:
        """Map artifact variants to RPC payloads with grind/brewing parsing."""
        variants_payloads = []
        
        if artifact.product.variants:
            for variant in artifact.product.variants:
                try:
                    # Parse grind/brewing using C.4a parser (following C.1 pattern)
                    grind_result = self.grind_brewing_parser.parse_grind_brewing(variant)
                    
                    variant_payload = {
                        'p_platform_variant_id': variant.platform_variant_id,
                        'p_sku': variant.sku,
                        'p_weight_g': variant.weight_g,  # From C.1 weight parsing
                        'p_currency': variant.currency,
                        'p_in_stock': variant.in_stock,
                        'p_stock_qty': variant.stock_qty,
                        'p_subscription_available': variant.subscription_available,
                        'p_compare_at_price': variant.compare_at_price,
                        'p_grind': grind_result.grind_type,  # CRITICAL: A.4 RPC parameter
                        'p_pack_count': variant.pack_count,
                        'p_source_raw': {
                            'grind_brewing_parsing': grind_result.to_dict(),
                            'scraped_at': artifact.scraped_at.isoformat()
                        }
                    }
                    
                    variants_payloads.append(variant_payload)
                    
                except Exception as e:
                    logger.warning("Failed to map variant with grind/brewing", error=str(e))
                    continue
        
        return variants_payloads
```

### File Locations
Based on Epic C requirements and A.1-A.5 integration:

**A.4 RPC Integration Files (Extend Existing - following C.1 pattern):**
- Extend existing: `src/validator/artifact_mapper.py` ✅ **EXISTS** (enhance `_map_variants_data` with grind/brewing parsing)
- Extend existing: `src/validator/rpc_client.py` ✅ **EXISTS** (ensure `p_grind` parameter support)
- Extend existing: `src/validator/database_integration.py` ✅ **EXISTS** (add grind/brewing processing to upsert flow)
- Extend existing: `tests/validator/test_artifact_mapper.py` ✅ **EXISTS** (add grind/brewing parsing tests)

**A.1-A.5 Pipeline Integration Files (Extend Existing - following C.1 pattern):**
- Extend existing: `src/validator/integration_service.py` ✅ **EXISTS** (add grind/brewing parsing to validation pipeline)
- Extend existing: `src/validator/validation_pipeline.py` ✅ **EXISTS** (integrate grind/brewing processing)
- Extend existing: `tests/validator/test_integration_service.py` ✅ **EXISTS** (add grind/brewing parsing integration tests)

**New Files (following C.1 pattern):**
- Grind/brewing parser library: `src/parser/grind_brewing_parser.py` (new - standalone library)
- Test fixtures: `tests/parser/fixtures/grind_brewing_formats.json` (new)
- Unit tests: `tests/parser/test_grind_brewing_parser.py` (new)
- Integration tests: `tests/parser/test_grind_brewing_parser_integration.py` (new)

**Configuration Files:**
- Parser config: `src/parser/config.py` (new - extend existing)
- Test data: `tests/parser/data/grind_brewing_samples.json` (new)
- Documentation: `docs/parser/grind_brewing_parser.md` (new)

### Performance Requirements
[Source: Epic C requirements]

**Processing Performance:**
- **Batch Processing**: Handle 100+ products per batch
- **Response Time**: < 2 seconds for 100 products
- **Memory Usage**: < 100MB for batch processing
- **Error Handling**: Graceful fallback for processing failures

### Testing Strategy
[Source: Epic C requirements]

**Unit Tests:**
- Grind/brewing detection accuracy across different variant types
- Error handling for corrupted or invalid variant data
- Performance tests for batch processing

**Integration Tests:**
- A.1-A.5 pipeline integration with grind/brewing parsing
- Database integration with grind/brewing storage
- End-to-end artifact processing with parsing
- Performance benchmarks for large product sets

## Definition of Done
- [ ] Grind/brewing parser service implemented with variant pattern matching
- [ ] ValidatorIntegrationService composition completed
- [ ] Database integration with normalized grind/brewing data
- [ ] Comprehensive test coverage for grind/brewing parsing
- [ ] Performance optimization for batch processing
- [ ] Integration tests with existing pipeline components
- [ ] Documentation updated with grind/brewing parser implementation

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation with variant-based grind/brewing parsing strategy | Bob (Scrum Master) |
