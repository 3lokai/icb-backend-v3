# Story C.5: Varieties & geographic parser

## Status
Draft

## Story
**As a** data processing engineer,
**I want** to extract coffee varieties, region, country, and altitude from product descriptions to enhance the existing coffee artifact mapping,
**so that** I can provide comprehensive geographic and varietal information for coffee products following the established C.2 pattern without creating separate database operations.

## Acceptance Criteria
1. Coffee varieties extracted from product descriptions into varieties array
2. Geographic data extracted (region, country, altitude) from product descriptions
3. Ambiguous cases flagged in `parsing_warnings` with confidence scoring
4. Integration with A.1-A.5 pipeline through ValidatorIntegrationService composition
5. Enhancement of `ArtifactMapper._map_artifact_data()` following C.2 pattern
6. Use existing `rpc_upsert_coffee()` with existing `varieties` and geographic fields
7. Comprehensive test coverage for variety and geographic extraction
8. Performance optimized for batch processing of product data

## Tasks / Subtasks
- [ ] Task 1: Variety extraction service implementation (AC: 1, 3, 7, 8)
  - [ ] Create `VarietyExtractionService` with Pydantic result models
  - [ ] Implement variety detection from product descriptions
  - [ ] Add confidence scoring for variety extraction accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for variety extraction accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 2: Geographic parser service implementation (AC: 2, 3, 7, 8)
  - [ ] Create `GeographicParserService` with Pydantic result models
  - [ ] Implement region/country detection from descriptions
  - [ ] Implement altitude extraction from descriptions
  - [ ] Add confidence scoring for geographic extraction accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for geographic extraction accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 3: ValidatorIntegrationService composition (AC: 4, 5)
  - [ ] Integrate variety parser with ValidatorIntegrationService
  - [ ] Integrate geographic parser with ValidatorIntegrationService
  - [ ] Add parser configuration to ValidatorConfig
  - [ ] Update ArtifactMapper to use new parsers
  - [ ] Add integration tests for parser composition
  - [ ] Test A.1-A.5 pipeline integration

- [ ] Task 4: ArtifactMapper enhancement following C.2 pattern (AC: 5, 6)
  - [ ] Enhance `ArtifactMapper._map_artifact_data()` with variety extraction
  - [ ] Enhance `ArtifactMapper._map_artifact_data()` with geographic parsing
  - [ ] Use existing `rpc_upsert_coffee()` with existing `varieties` and geographic fields
  - [ ] Add integration tests for ArtifactMapper enhancement
  - [ ] Test end-to-end data flow from parsing to existing RPC

## Dev Notes
[Source: Epic C requirements and A.1-A.5 implementation patterns]

**⚠️ IMPORTANT: DO NOT CREATE NEW MIGRATIONS**
- The migration `extend_rpc_upsert_coffee_epic_c_parameters.sql` already handles ALL Epic C parameters
- This includes C.3 (tags/notes), C.4 (grind/species), C.5 (varieties/geographic), C.6 (sensory/hash), and C.7 (text cleaning)
- Dev should use the existing enhanced RPC function with `p_varieties`, `p_region`, `p_country`, `p_altitude` parameters
- No additional database migrations needed for this story

### Variety Extraction Strategy
[Source: Epic C requirements]

**Variety Detection:**
```python
class VarietyExtractionService:
    def __init__(self, config: VarietyConfig):
        self.config = config
        self.variety_patterns = {
            'bourbon': [r'bourbon', r'bourbon\s*variety'],
            'typica': [r'typica', r'typica\s*variety'],
            'caturra': [r'caturra', r'caturra\s*variety'],
            'catimor': [r'catimor', r'catimor\s*variety'],
            'kent': [r'kent', r'kent\s*variety'],
            'sl28': [r'sl28', r'sl\s*28'],
            'sl34': [r'sl34', r'sl\s*34'],
            'geisha': [r'geisha', r'gesha', r'geisha\s*variety'],
            'pacamara': [r'pacamara', r'pacamara\s*variety']
        }
    
    def extract_varieties(self, description: str) -> VarietyResult:
        """Extract coffee varieties from product description"""
        varieties = []
        confidence_scores = []
        warnings = []
        
        for variety, patterns in self.variety_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    varieties.append(variety)
                    confidence_scores.append(0.9)
                    break
        
        return VarietyResult(
            varieties=varieties,
            confidence_scores=confidence_scores,
            warnings=warnings
        )
```

### Geographic Parser Strategy
[Source: Epic C requirements]

**Geographic Data Extraction:**
```python
class GeographicParserService:
    def __init__(self, config: GeographicConfig):
        self.config = config
        self.region_patterns = {
            'africa': [r'africa', r'african', r'ethiopia', r'kenya', r'tanzania'],
            'central_america': [r'central\s*america', r'guatemala', r'costa\s*rica', r'panama'],
            'south_america': [r'south\s*america', r'colombia', r'brazil', r'peru'],
            'asia': [r'asia', r'asian', r'india', r'indonesia', r'vietnam']
        }
        self.country_patterns = {
            'ethiopia': [r'ethiopia', r'ethiopian'],
            'kenya': [r'kenya', r'kenyan'],
            'colombia': [r'colombia', r'colombian'],
            'brazil': [r'brazil', r'brazilian'],
            'guatemala': [r'guatemala', r'guatemalan'],
            'india': [r'india', r'indian']
        }
        self.altitude_patterns = [
            r'(\d+)\s*(?:m|meters?|ft|feet?)\s*(?:above\s*sea\s*level|asl)',
            r'(\d+)\s*(?:m|meters?|ft|feet?)\s*altitude',
            r'altitude[:\s]*(\d+)\s*(?:m|meters?|ft|feet?)'
        ]
    
    def parse_geographic(self, description: str) -> GeographicResult:
        """Parse geographic data from product description"""
        region = self._extract_region(description)
        country = self._extract_country(description)
        altitude = self._extract_altitude(description)
        
        return GeographicResult(
            region=region,
            country=country,
            altitude=altitude,
            confidence=self._calculate_confidence(region, country, altitude),
            warnings=self._generate_warnings(region, country, altitude)
        )
    
    def _extract_region(self, description: str) -> str:
        """Extract region from description"""
        for region, patterns in self.region_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return region
        return 'unknown'
    
    def _extract_country(self, description: str) -> str:
        """Extract country from description"""
        for country, patterns in self.country_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return country
        return 'unknown'
    
    def _extract_altitude(self, description: str) -> Optional[int]:
        """Extract altitude from description"""
        for pattern in self.altitude_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                altitude = int(match.group(1))
                # Convert feet to meters if needed
                if 'ft' in match.group(0).lower() or 'feet' in match.group(0).lower():
                    altitude = int(altitude * 0.3048)  # Convert feet to meters
                return altitude
        return None
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
        if config.enable_grind_parsing:
            self.grind_parser = GrindParserService(config.grind_config)
        if config.enable_species_parsing:
            self.species_parser = BeanSpeciesParserService(config.species_config)
        
        # New parsers
        if config.enable_variety_parsing:
            self.variety_parser = VarietyExtractionService(config.variety_config)
        if config.enable_geographic_parsing:
            self.geographic_parser = GeographicParserService(config.geographic_config)
        
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
        if self.integration_service.variety_parser:
            variety_result = self.integration_service.variety_parser.extract_varieties(
                artifact.get('description', '')
            )
            artifact['varieties'] = variety_result.varieties
        
        if self.integration_service.geographic_parser:
            geo_result = self.integration_service.geographic_parser.parse_geographic(
                artifact.get('description', '')
            )
            artifact['region'] = geo_result.region
            artifact['country'] = geo_result.country
            artifact['altitude'] = geo_result.altitude
        
        return artifact
```

### File Locations
Based on Epic C requirements and A.1-A.5 integration:

**New Files:**
- Variety extraction service: `src/parser/variety_extraction.py` (new)
- Geographic parser service: `src/parser/geographic_parser.py` (new)
- Variety configuration: `src/config/variety_config.py` (new)
- Geographic configuration: `src/config/geographic_config.py` (new)
- Integration tests: `tests/parser/test_variety_extraction_integration.py` (new)
- Integration tests: `tests/parser/test_geographic_parser_integration.py` (new)

**Extension Files (Modify Existing):**
- Extend existing: `src/validator/artifact_mapper.py` ✅ **EXISTS** (enhance `_map_artifact_data`)
- Extend existing: `src/validator/database_integration.py` ✅ **EXISTS** (add variety/geographic processing)
- Extend existing: `src/validator/rpc_client.py` ✅ **EXISTS** (enhance `upsert_coffee_artifact`)
- Extend existing: `tests/validator/test_artifact_mapper.py` ✅ **EXISTS** (add variety/geographic tests)

**Configuration Files:**
- Variety processing config: `src/config/variety_config.py` (new)
- Geographic processing config: `src/config/geographic_config.py` (new)
- Test fixtures: `tests/parser/fixtures/variety_samples.json` (new)
- Test fixtures: `tests/parser/fixtures/geographic_samples.json` (new)
- Documentation: `docs/parser/variety_extraction.md` (new)
- Documentation: `docs/parser/geographic_parser.md` (new)

### Performance Requirements
[Source: Epic C requirements]

**Processing Performance:**
- **Batch Processing**: Handle 100+ products per batch
- **Response Time**: < 3 seconds for 100 products (geographic parsing is more complex)
- **Memory Usage**: < 150MB for batch processing
- **Error Handling**: Graceful fallback for processing failures

### Testing Strategy
[Source: Epic C requirements]

**Unit Tests:**
- Variety extraction accuracy across different product types
- Geographic extraction accuracy across different product types
- Error handling for corrupted or invalid data
- Performance tests for batch processing

**Integration Tests:**
- A.1-A.5 pipeline integration with variety and geographic parsing
- Database integration with variety and geographic storage
- End-to-end artifact processing with parsing
- Performance benchmarks for large product sets

## Definition of Done
- [ ] Variety extraction service implemented with pattern matching
- [ ] Geographic parser service implemented with pattern matching
- [ ] ValidatorIntegrationService composition completed
- [ ] Database integration with normalized variety and geographic data
- [ ] Comprehensive test coverage for variety and geographic parsing
- [ ] Performance optimization for batch processing
- [ ] Integration tests with existing pipeline components
- [ ] Documentation updated with variety and geographic parser implementation

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation with A.1-A.5 integration strategy | Bob (Scrum Master) |
