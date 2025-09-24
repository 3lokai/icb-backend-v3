# Story C.4: Grind & bean species parser

## Status
Draft

## Story
**As a** data processing engineer,
**I want** to parse grind types and bean species from product titles/descriptions to enhance the existing coffee artifact mapping,
**so that** I can provide consistent grind and species categorization for coffee products following the established C.2 pattern without creating separate database operations.

## Acceptance Criteria
1. Grind types parsed from product titles/descriptions into `default_grind` enum
2. Bean species parsed from product titles/descriptions into `bean_species` enum
3. Ambiguous cases flagged in `parsing_warnings` with confidence scoring
4. Integration with A.1-A.5 pipeline through ValidatorIntegrationService composition
5. Enhancement of `ArtifactMapper._map_artifact_data()` following C.2 pattern
6. Use existing `rpc_upsert_coffee()` with existing `default_grind` and `bean_species` fields
7. Comprehensive test coverage for grind and species detection
8. Performance optimized for batch processing of product data

## Tasks / Subtasks
- [ ] Task 1: Grind parser service implementation (AC: 1, 3, 7, 8)
  - [ ] Create `GrindParserService` with Pydantic result models
  - [ ] Implement grind type detection from titles/descriptions
  - [ ] Add confidence scoring for grind detection accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for grind detection accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 2: Bean species parser service implementation (AC: 2, 3, 7, 8)
  - [ ] Create `BeanSpeciesParserService` with Pydantic result models
  - [ ] Implement species detection from titles/descriptions
  - [ ] Add confidence scoring for species detection accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for species detection accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 3: ValidatorIntegrationService composition (AC: 4, 5)
  - [ ] Integrate grind parser with ValidatorIntegrationService
  - [ ] Integrate species parser with ValidatorIntegrationService
  - [ ] Add parser configuration to ValidatorConfig
  - [ ] Update ArtifactMapper to use new parsers
  - [ ] Add integration tests for parser composition
  - [ ] Test A.1-A.5 pipeline integration

- [ ] Task 4: ArtifactMapper enhancement following C.2 pattern (AC: 5, 6)
  - [ ] Enhance `ArtifactMapper._map_artifact_data()` with grind parsing
  - [ ] Enhance `ArtifactMapper._map_artifact_data()` with species parsing
  - [ ] Use existing `rpc_upsert_coffee()` with existing `default_grind` and `bean_species` fields
  - [ ] Add integration tests for ArtifactMapper enhancement
  - [ ] Test end-to-end data flow from parsing to existing RPC

## Dev Notes
[Source: Epic C requirements and A.1-A.5 implementation patterns]

**⚠️ IMPORTANT: DO NOT CREATE NEW MIGRATIONS**
- The migration `extend_rpc_upsert_coffee_epic_c_parameters.sql` already handles ALL Epic C parameters
- This includes C.3 (tags/notes), C.4 (grind/species), C.5 (varieties/geographic), C.6 (sensory/hash), and C.7 (text cleaning)
- Dev should use the existing enhanced RPC function with `p_default_grind` parameter
- No additional database migrations needed for this story

### Grind Parser Strategy
[Source: Epic C requirements]

**Grind Type Detection:**
```python
class GrindParserService:
    def __init__(self, config: GrindConfig):
        self.config = config
        self.grind_patterns = {
            'whole-bean': [r'whole\s*bean', r'beans?', r'coffee\s*beans?'],
            'coarse': [r'coarse\s*grind', r'french\s*press\s*grind'],
            'medium': [r'medium\s*grind', r'filter\s*grind', r'drip\s*grind'],
            'fine': [r'fine\s*grind', r'espresso\s*grind'],
            'extra-fine': [r'extra\s*fine', r'turkish\s*grind']
        }
    
    def parse_grind(self, title: str, description: str) -> GrindResult:
        """Parse grind type from product title and description"""
        text = f"{title} {description}".lower()
        
        for grind_type, patterns in self.grind_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return GrindResult(
                        grind_type=grind_type,
                        confidence=0.9,
                        source='pattern_match',
                        warnings=[]
                    )
        
        return GrindResult(
            grind_type='unknown',
            confidence=0.0,
            source='no_match',
            warnings=['No grind type detected']
        )
```

### Bean Species Parser Strategy
[Source: Epic C requirements]

**Species Detection:**
```python
class BeanSpeciesParserService:
    def __init__(self, config: SpeciesConfig):
        self.config = config
        self.species_patterns = {
            'arabica': [r'arabica', r'coffea\s*arabica'],
            'robusta': [r'robusta', r'coffea\s*canephora'],
            'liberica': [r'liberica', r'coffea\s*liberica'],
            'excelsa': [r'excelsa', r'coffea\s*excelsa']
        }
    
    def parse_species(self, title: str, description: str) -> SpeciesResult:
        """Parse bean species from product title and description"""
        text = f"{title} {description}".lower()
        
        for species, patterns in self.species_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return SpeciesResult(
                        species=species,
                        confidence=0.9,
                        source='pattern_match',
                        warnings=[]
                    )
        
        return SpeciesResult(
            species='unknown',
            confidence=0.0,
            source='no_match',
            warnings=['No species detected']
        )
```

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
        
        # New parsers
        if config.enable_grind_parsing:
            self.grind_parser = GrindParserService(config.grind_config)
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
        
        # New mapping
        if self.integration_service.grind_parser:
            grind_result = self.integration_service.grind_parser.parse_grind(
                artifact.get('title', ''),
                artifact.get('description', '')
            )
            artifact['default_grind'] = grind_result.grind_type
        
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
- Grind parser service: `src/parser/grind_parser.py` (new)
- Species parser service: `src/parser/species_parser.py` (new)
- Grind configuration: `src/config/grind_config.py` (new)
- Species configuration: `src/config/species_config.py` (new)
- Integration tests: `tests/parser/test_grind_parser_integration.py` (new)
- Integration tests: `tests/parser/test_species_parser_integration.py` (new)

**Extension Files (Modify Existing):**
- Extend existing: `src/validator/artifact_mapper.py` ✅ **EXISTS** (enhance `_map_artifact_data`)
- Extend existing: `src/validator/database_integration.py` ✅ **EXISTS** (add grind/species processing)
- Extend existing: `src/validator/rpc_client.py` ✅ **EXISTS** (enhance `upsert_coffee_artifact`)
- Extend existing: `tests/validator/test_artifact_mapper.py` ✅ **EXISTS** (add grind/species tests)

**Configuration Files:**
- Grind processing config: `src/config/grind_config.py` (new)
- Species processing config: `src/config/species_config.py` (new)
- Test fixtures: `tests/parser/fixtures/grind_samples.json` (new)
- Test fixtures: `tests/parser/fixtures/species_samples.json` (new)
- Documentation: `docs/parser/grind_parser.md` (new)
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
- Grind detection accuracy across different product types
- Species detection accuracy across different product types
- Error handling for corrupted or invalid data
- Performance tests for batch processing

**Integration Tests:**
- A.1-A.5 pipeline integration with grind and species parsing
- Database integration with grind and species storage
- End-to-end artifact processing with parsing
- Performance benchmarks for large product sets

## Definition of Done
- [ ] Grind parser service implemented with pattern matching
- [ ] Species parser service implemented with pattern matching
- [ ] ValidatorIntegrationService composition completed
- [ ] Database integration with normalized grind and species data
- [ ] Comprehensive test coverage for grind and species parsing
- [ ] Performance optimization for batch processing
- [ ] Integration tests with existing pipeline components
- [ ] Documentation updated with grind and species parser implementation

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation with A.1-A.5 integration strategy | Bob (Scrum Master) |
