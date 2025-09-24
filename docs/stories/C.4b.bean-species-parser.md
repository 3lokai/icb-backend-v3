# Story C.4b: Bean Species Parser (from Content)

## Status
Draft

## Story
**As a** data processing engineer,
**I want** to parse bean species from product titles/descriptions to enhance the existing coffee artifact mapping,
**so that** I can provide consistent species categorization for coffee products following the established C.2 pattern without creating separate database operations.

## Acceptance Criteria
1. Bean species parsed from product titles/descriptions into `bean_species` enum
2. Ambiguous cases flagged in `parsing_warnings` with confidence scoring
3. Integration with A.1-A.5 pipeline through ValidatorIntegrationService composition
4. Enhancement of `ArtifactMapper._map_artifact_data()` following C.2 pattern
5. Use existing `rpc_upsert_coffee()` with existing `bean_species` field
6. Comprehensive test coverage for species detection
7. Performance optimized for batch processing of product data

## Tasks / Subtasks
- [ ] Task 1: Bean species parser service implementation (AC: 1, 2, 6, 7)
  - [ ] Create `BeanSpeciesParserService` with Pydantic result models
  - [ ] Implement species detection from titles/descriptions
  - [ ] Add confidence scoring for species detection accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for species detection accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 2: ValidatorIntegrationService composition (AC: 3, 4)
  - [ ] Integrate species parser with ValidatorIntegrationService
  - [ ] Add parser configuration to ValidatorConfig
  - [ ] Update ArtifactMapper to use new parser
  - [ ] Add integration tests for parser composition
  - [ ] Test A.1-A.5 pipeline integration

- [ ] Task 3: ArtifactMapper enhancement following C.2 pattern (AC: 4, 5)
  - [ ] Enhance `ArtifactMapper._map_artifact_data()` with species parsing
  - [ ] Use existing `rpc_upsert_coffee()` with existing `bean_species` field
  - [ ] Add integration tests for ArtifactMapper enhancement
  - [ ] Test end-to-end data flow from parsing to existing RPC

## Dev Notes
[Source: Epic C requirements and A.1-A.5 implementation patterns]

**⚠️ IMPORTANT: DO NOT CREATE NEW MIGRATIONS**
- The migration `extend_rpc_upsert_coffee_epic_c_parameters.sql` already handles ALL Epic C parameters
- This includes C.3 (tags/notes), C.4 (grind/species), C.5 (varieties/geographic), C.6 (sensory/hash), and C.7 (text cleaning)
- Dev should use the existing enhanced RPC function with `p_bean_species` parameter
- No additional database migrations needed for this story

### Bean Species Parser Strategy
[Source: Epic C requirements and sample data analysis]

**Species Detection from Content:**
```python
class BeanSpeciesParserService:
    def __init__(self, config: SpeciesConfig):
        self.config = config
        self.species_patterns = {
            'arabica': [
                r'100%\s*arabica', r'pure\s*arabica', r'arabica\s*only'
            ],
            'robusta': [
                r'100%\s*robusta', r'pure\s*robusta', r'robusta\s*only'
            ],
            'liberica': [
                r'liberica', r'coffea\s*liberica', r'liberica\s*coffee'
            ],
            # Ratio-based blends
            'arabica_80_robusta_20': [
                r'80.*20', r'80%\s*arabica.*20%\s*robusta', r'80-20'
            ],
            'arabica_70_robusta_30': [
                r'70.*30', r'70%\s*arabica.*30%\s*robusta', r'70-30'
            ],
            'arabica_60_robusta_40': [
                r'60.*40', r'60%\s*arabica.*40%\s*robusta', r'60-40'
            ],
            'arabica_50_robusta_50': [
                r'50.*50', r'50%\s*arabica.*50%\s*robusta', r'50-50'
            ],
            'robusta_80_arabica_20': [
                r'80%\s*robusta.*20%\s*arabica', r'robusta.*80.*arabica.*20'
            ],
            # Chicory mixes
            'arabica_chicory': [
                r'arabica.*chicory', r'chicory.*arabica'
            ],
            'robusta_chicory': [
                r'robusta.*chicory', r'chicory.*robusta'
            ],
            'blend_chicory': [
                r'blend.*chicory', r'chicory.*blend', r'coffee.*chicory'
            ],
            'filter_coffee_mix': [
                r'filter\s*coffee', r'south\s*indian\s*filter'
            ],
            # Generic blends (fallback)
            'blend': [
                r'arabica\s*&\s*robusta', r'arabica\s*and\s*robusta',
                r'mixed\s*blend', r'coffee\s*blend', r'blend\s*of',
                r'arabica.*robusta', r'robusta.*arabica'
            ]
        }
        
        # Context patterns for better detection
        self.context_patterns = {
            'species_mention': [
                r'species', r'variety', r'type\s*of\s*bean',
                r'bean\s*type', r'coffee\s*type'
            ],
            'blend_indicators': [
                r'blend', r'mix', r'combination', r'fusion'
            ]
        }
    
    def parse_species(self, title: str, description: str) -> SpeciesResult:
        """Parse bean species from product title and description"""
        text = f"{title} {description}".lower()
        
        detected_species = []
        confidence_scores = []
        warnings = []
        
        # Check for explicit species mentions
        for species, patterns in self.species_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    detected_species.append(species)
                    confidence_scores.append(0.9)
                    
                    # Check for context that increases confidence
                    if any(re.search(ctx_pattern, text) for ctx_pattern in self.context_patterns['species_mention']):
                        confidence_scores[-1] = 0.95
        
        # Handle blend detection
        if any(re.search(pattern, text) for pattern in self.species_patterns['blend']):
            if 'arabica' in detected_species and 'robusta' in detected_species:
                # Both species mentioned - likely a blend
                return SpeciesResult(
                    species='blend',
                    confidence=0.9,
                    source='blend_detection',
                    warnings=[],
                    detected_species=detected_species
                )
        
        # Determine primary species
        if detected_species:
            primary_species = max(set(detected_species), key=detected_species.count)
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            
            return SpeciesResult(
                species=primary_species,
                confidence=avg_confidence,
                source='content_parsing',
                warnings=warnings,
                detected_species=detected_species
            )
        
        return SpeciesResult(
            species='unknown',
            confidence=0.0,
            source='no_match',
            warnings=['No species detected in title/description'],
            detected_species=[]
        )
```

### Database Schema Alignment
[Source: docs/db/enums.md and canonical_artifact.md]

**Species Enum Values (from database):**
- `arabica` - Arabica coffee species
- `robusta` - Robusta coffee species  
- `liberica` - Liberica coffee species
- `blend` - Blend of multiple species

**Canonical Artifact Mapping:**
- `normalization.bean_species` → `coffees.bean_species` (via `rpc_upsert_coffee`)
- Store in `normalization` section of artifact for processing
- Use existing `species_enum` from database schema

### Integration Points
[Source: A.1-A.5 implementation patterns]

**ValidatorIntegrationService Integration:**
```python
class ValidatorIntegrationService:
    def __init__(self, config: ValidatorConfig):
        # Existing parsers
        if config.enable_weight_parsing:
            self.weight_parser = WeightParser()
        if config.enable_roast_parsing:
            self.roast_parser = RoastLevelParser()
        if config.enable_process_parsing:
            self.process_parser = ProcessMethodParser()
        
        # New parser
        if config.enable_species_parsing:
            self.species_parser = BeanSpeciesParserService(config.species_config)
        
        # Pass to ArtifactMapper
        self.artifact_mapper = ArtifactMapper(integration_service=self)
```

**ArtifactMapper Integration:**
```python
class ArtifactMapper:
    def __init__(self, integration_service: ValidatorIntegrationService):
        self.integration_service = integration_service
    
    def _map_artifact_data(self, artifact: Dict) -> Dict:
        # Existing mapping
        if self.integration_service.weight_parser:
            weight_result = self.integration_service.weight_parser.parse_weight(artifact.get('weight', ''))
            artifact['weight_g'] = weight_result.grams
        
        # New mapping for species
        if self.integration_service.species_parser:
            species_result = self.integration_service.species_parser.parse_species(
                artifact.get('title', ''),
                artifact.get('description', '')
            )
            artifact['bean_species'] = species_result.species
        
        return artifact
```

### File Locations
Based on Epic C requirements and A.1-A.5 integration:

**New Files:**
- Species parser service: `src/parser/species_parser.py` (new)
- Species configuration: `src/config/species_config.py` (new)
- Integration tests: `tests/parser/test_species_parser_integration.py` (new)

**Extension Files (Modify Existing):**
- Extend existing: `src/validator/artifact_mapper.py` ✅ **EXISTS** (enhance `_map_artifact_data`)
- Extend existing: `src/validator/database_integration.py` ✅ **EXISTS** (add species processing)
- Extend existing: `src/validator/rpc_client.py` ✅ **EXISTS** (enhance `upsert_coffee_artifact`)
- Extend existing: `tests/validator/test_artifact_mapper.py` ✅ **EXISTS** (add species tests)

**Configuration Files:**
- Species processing config: `src/config/species_config.py` (new)
- Test fixtures: `tests/parser/fixtures/species_samples.json` (new)
- Documentation: `docs/parser/species_parser.md` (new)

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
- Species detection accuracy across different product types
- Error handling for corrupted or invalid data
- Performance tests for batch processing

**Integration Tests:**
- A.1-A.5 pipeline integration with species parsing
- Database integration with species storage
- End-to-end artifact processing with parsing
- Performance benchmarks for large product sets

## Definition of Done
- [ ] Species parser service implemented with content pattern matching
- [ ] ValidatorIntegrationService composition completed
- [ ] Database integration with normalized species data
- [ ] Comprehensive test coverage for species parsing
- [ ] Performance optimization for batch processing
- [ ] Integration tests with existing pipeline components
- [ ] Documentation updated with species parser implementation

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation with content-based species parsing strategy | Bob (Scrum Master) |
