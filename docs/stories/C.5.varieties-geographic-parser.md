# Story C.5: Indian Coffee Varieties & Geographic Parser

## Status
Draft

## Story
**As a** data processing engineer,
**I want** to extract Indian coffee varieties, regions, estates, states, and altitude from product descriptions to enhance the existing coffee artifact mapping,
**so that** I can provide comprehensive geographic and varietal information for Indian coffee products following the established C.2 pattern without creating separate database operations.

## Acceptance Criteria
1. Indian coffee varieties extracted from product descriptions (S795, S9, S8, S5, Cauvery, Kent, SL28, SL34, Geisha, Monsoon Malabar, etc.)
2. Indian geographic data extracted (regions, estates, states, altitude) from product descriptions
3. Indian coffee estate recognition from seed data patterns
4. Ambiguous cases flagged in `parsing_warnings` with confidence scoring
5. Integration with A.1-A.5 pipeline through ValidatorIntegrationService composition
6. Enhancement of `ArtifactMapper._map_artifact_data()` following C.2 pattern
7. Use existing `rpc_upsert_coffee()` with existing `varieties` and geographic fields
8. Comprehensive test coverage for Indian variety and geographic extraction
9. Performance optimized for batch processing of Indian coffee product data

## Tasks / Subtasks
- [ ] Task 1: Indian variety extraction service implementation (AC: 1, 4, 8, 9)
  - [ ] Create `VarietyExtractionService` with Pydantic result models
  - [ ] Implement Indian variety detection (S795, S9, S8, S5, Cauvery, Kent, SL28, SL34, Geisha, Monsoon Malabar)
  - [ ] Add confidence scoring for variety extraction accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for Indian variety extraction accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 2: Indian geographic parser service implementation (AC: 2, 3, 4, 8, 9)
  - [ ] Create `GeographicParserService` with Pydantic result models
  - [ ] Implement Indian region/state/country detection from descriptions
  - [ ] Implement Indian coffee estate recognition from seed data patterns
  - [ ] Implement altitude extraction from descriptions
  - [ ] Add confidence scoring for geographic extraction accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for Indian geographic extraction accuracy
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
[Source: Epic C requirements and Indian coffee seed data analysis]

**Indian Coffee Variety Detection:**
```python
class VarietyExtractionService:
    def __init__(self, config: VarietyConfig):
        self.config = config
        # Indian-specific variety patterns based on seed data analysis
        self.variety_patterns = {
            # Traditional Indian varieties
            's795': [r's795', r's\s*795', r'selection\s*795'],
            's9': [r's9', r's\s*9', r'selection\s*9'],
            's8': [r's8', r's\s*8', r'selection\s*8'],
            's5': [r's5', r's\s*5', r'selection\s*5'],
            's5a': [r's5a', r's\s*5a', r'selection\s*5a'],
            's5b': [r's5b', r's\s*5b', r'selection\s*5b'],
            'cauvery': [r'cauvery', r'cauvery\s*variety'],
            'cxr': [r'cxr', r'cxr\s*variety'],
            'chandagiri': [r'chandagiri', r'chandagiri\s*variety'],
            'kent': [r'kent', r'kent\s*variety'],
            'sl28': [r'sl28', r'sl\s*28'],
            'sl34': [r'sl34', r'sl\s*34'],
            'catimor': [r'catimor', r'catimor\s*variety'],
            'caturra': [r'caturra', r'caturra\s*variety'],
            'bourbon': [r'bourbon', r'bourbon\s*variety'],
            'typica': [r'typica', r'typica\s*variety'],
            # Premium varieties found in Indian estates
            'geisha': [r'geisha', r'gesha', r'geisha\s*variety', r'green\s*tip\s*gesha', r'brown\s*tip\s*gesha'],
            'pacamara': [r'pacamara', r'pacamara\s*variety'],
            # Indian processing-specific varieties
            'monsoon_malabar': [r'monsoon\s*malabar', r'monsooned\s*malabar'],
            'malabar': [r'malabar', r'malabar\s*variety']
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
[Source: Epic C requirements and Indian coffee regions seed data]

**Indian Coffee Geographic Data Extraction:**
```python
class GeographicParserService:
    def __init__(self, config: GeographicConfig):
        self.config = config
        # Indian coffee regions based on seed data analysis
        self.region_patterns = {
            # Major Indian coffee regions
            'chikmagalur': [r'chikmagalur', r'chikmagalur\s*region', r'baba\s*budangiri', r'baba\s*budan\s*giri'],
            'coorg': [r'coorg', r'kodagu', r'coorg\s*region'],
            'nilgiris': [r'nilgiris', r'blue\s*mountains', r'nilgiri\s*hills'],
            'yercaud': [r'yercaud', r'shevaroy\s*hills', r'shevaroy'],
            'wayanad': [r'wayanad', r'wayanad\s*highlands'],
            'araku_valley': [r'araku\s*valley', r'araku'],
            'biligiri_ranga': [r'biligiri\s*ranga', r'biligiriranga', r'br\s*hills'],
            'malnad': [r'malnad', r'land\s*of\s*hills'],
            'pulneys': [r'pulneys', r'pulney\s*hills', r'palani\s*hills'],
            'anamalais': [r'anamalais', r'elephant\s*hills'],
            'kodaikanal': [r'kodaikanal', r'kodaikanal\s*hills'],
            'travancore': [r'travancore'],
            'coimbatore': [r'coimbatore'],
            'salem': [r'salem'],
            'theni': [r'theni'],
            'idukki': [r'idukki'],
            'manjarabad': [r'manjarabad'],
            'sakleshpur': [r'sakleshpur'],
            # Northeast Indian regions
            'arunachal_pradesh': [r'arunachal\s*pradesh', r'arunachal'],
            'meghalaya': [r'meghalaya', r'abode\s*of\s*clouds'],
            'mizoram': [r'mizoram'],
            'manipur': [r'manipur'],
            'tripura': [r'tripura'],
            'nagaland': [r'nagaland', r'kohima'],
            # Eastern Indian regions
            'odisha': [r'odisha', r'orissa', r'koraput', r'rayagada', r'mayurbhanj', r'keonjhar'],
            'andhra_pradesh': [r'andhra\s*pradesh', r'andhra'],
            # International regions (for context)
            'colombia': [r'colombia', r'colombian'],
            'ethiopia': [r'ethiopia', r'ethiopian'],
            'kenya': [r'kenya', r'kenyan']
        }
        
        # Indian states and countries
        self.country_patterns = {
            'india': [r'india', r'indian', r'from\s*india'],
            'colombia': [r'colombia', r'colombian'],
            'ethiopia': [r'ethiopia', r'ethiopian'],
            'kenya': [r'kenya', r'kenyan'],
            'brazil': [r'brazil', r'brazilian'],
            'guatemala': [r'guatemala', r'guatemalan']
        }
        
        # Indian states
        self.state_patterns = {
            'karnataka': [r'karnataka', r'karnataka\s*state'],
            'tamil_nadu': [r'tamil\s*nadu', r'tamil\s*nadu\s*state'],
            'kerala': [r'kerala', r'kerala\s*state'],
            'andhra_pradesh': [r'andhra\s*pradesh', r'andhra\s*pradesh\s*state'],
            'odisha': [r'odisha', r'orissa', r'odisha\s*state'],
            'arunachal_pradesh': [r'arunachal\s*pradesh', r'arunachal\s*pradesh\s*state'],
            'meghalaya': [r'meghalaya', r'meghalaya\s*state'],
            'mizoram': [r'mizoram', r'mizoram\s*state'],
            'manipur': [r'manipur', r'manipur\s*state'],
            'tripura': [r'tripura', r'tripura\s*state'],
            'nagaland': [r'nagaland', r'nagaland\s*state'],
            'assam': [r'assam', r'assam\s*state']
        }
        self.altitude_patterns = [
            r'(\d+)\s*(?:m|meters?|ft|feet?)\s*(?:above\s*sea\s*level|asl)',
            r'(\d+)\s*(?:m|meters?|ft|feet?)\s*altitude',
            r'altitude[:\s]*(\d+)\s*(?:m|meters?|ft|feet?)'
        ]
    
    def parse_geographic(self, description: str) -> GeographicResult:
        """Parse Indian coffee geographic data from product description"""
        region = self._extract_region(description)
        country = self._extract_country(description)
        state = self._extract_state(description)
        altitude = self._extract_altitude(description)
        
        return GeographicResult(
            region=region,
            country=country,
            state=state,
            altitude=altitude,
            confidence=self._calculate_confidence(region, country, state, altitude),
            warnings=self._generate_warnings(region, country, state, altitude)
        )
    
    def _extract_region(self, description: str) -> str:
        """Extract Indian coffee region from description"""
        for region, patterns in self.region_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return region
        return 'unknown'
    
    def _extract_country(self, description: str) -> str:
        """Extract country from description (India-focused)"""
        for country, patterns in self.country_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return country
        return 'unknown'
    
    def _extract_state(self, description: str) -> str:
        """Extract Indian state from description"""
        for state, patterns in self.state_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return state
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

### Indian Coffee Estate Patterns
[Source: Indian coffee estates seed data analysis]

**Estate Name Recognition:**
```python
# Indian coffee estate patterns from seed data
self.estate_patterns = {
    # Chikmagalur estates
    'krishnagiri_estate': [r'krishnagiri\s*estate', r'krishnagiri'],
    'kerehaklu_estate': [r'kerehaklu\s*estate', r'kerehaklu'],
    'basankhan_estate': [r'basankhan\s*estate', r'basankhan'],
    'thogarihunkal_estate': [r'thogarihunkal\s*estate', r'thogarihunkal'],
    'baarbara_estate': [r'baarbara\s*estate', r'baarbara'],
    'kalledevarapura_estate': [r'kalledevarapura\s*estate', r'kalledevarapura'],
    'hoysala_estate': [r'hoysala\s*estate', r'hoysala'],
    'sandalwood_estate': [r'sandalwood\s*estate', r'sandalwood'],
    'st_joseph_estate': [r'st\s*joseph\s*estate', r'st\s*margaret\s*estate'],
    'thippanahalli_estate': [r'thippanahalli\s*estate', r'thippanahalli'],
    'kolli_berri_estate': [r'kolli\s*berri\s*estate', r'kolli\s*berri'],
    'kondadkan_estate': [r'kondadkan\s*estate', r'kondadkan'],
    'ratnagiri_estate': [r'ratnagiri\s*estate', r'ratnagiri'],
    'gungegiri_estate': [r'gungegiri\s*estate', r'gungegiri'],
    
    # Coorg estates
    'mercara_gold_estate': [r'mercara\s*gold\s*estate', r'mercara\s*gold'],
    'old_kent_estates': [r'old\s*kent\s*estates', r'old\s*kent'],
    
    # Yercaud estates
    'stanmore_estate': [r'stanmore\s*estate', r'stanmore'],
    'hidden_falls_estate': [r'hidden\s*falls\s*estate', r'hidden\s*falls'],
    'riverdale_estate': [r'riverdale\s*estate', r'riverdale'],
    'gowri_estate': [r'gowri\s*estate', r'gowri'],
    
    # Biligiri-Ranga estates
    'attikan_estate': [r'attikan\s*estate', r'attikan'],
    'veer_attikan_estate': [r'veer\s*attikan\s*estate', r'veer\s*attikan'],
    
    # Other regions
    'seethargundu_estate': [r'seethargundu\s*estate', r'seethargundu'],
    'balmaadi_estate': [r'balmaadi\s*estate', r'balmaadi'],
    'ananthagiri_plantations': [r'ananthagiri\s*plantations', r'ananthagiri'],
    'cascara_coffee_cottages': [r'cascara\s*coffee\s*cottages', r'cascara'],
    'dream_hill_coffee': [r'dream\s*hill\s*coffee', r'dream\s*hill'],
    'hathikuli_estate': [r'hathikuli\s*estate', r'hathikuli'],
    'jampui_hills': [r'jampui\s*hills', r'jampui'],
    'darzo_village': [r'darzo\s*village', r'darzo'],
    'mynriah_village': [r'mynriah\s*village', r'mynriah']
}

def _extract_estate(self, description: str) -> str:
    """Extract Indian coffee estate from description"""
    for estate, patterns in self.estate_patterns.items():
        for pattern in patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return estate
    return 'unknown'
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
            artifact['state'] = geo_result.state
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
- Test fixtures: `tests/parser/fixtures/indian_variety_samples.json` (new)
- Test fixtures: `tests/parser/fixtures/indian_geographic_samples.json` (new)
- Documentation: `docs/parser/variety_extraction.md` (new)
- Documentation: `docs/parser/geographic_parser.md` (new)

**Indian Coffee Test Samples:**
```json
{
  "variety_samples": [
    {
      "description": "Premium Selection 9 Arabica from Chikmagalur estate",
      "expected_varieties": ["s9"],
      "expected_region": "chikmagalur"
    },
    {
      "description": "Monsoon Malabar coffee from Coorg region",
      "expected_varieties": ["monsoon_malabar"],
      "expected_region": "coorg"
    },
    {
      "description": "Green Tip Gesha from Riverdale Estate, Yercaud",
      "expected_varieties": ["geisha"],
      "expected_region": "yercaud",
      "expected_estate": "riverdale_estate"
    },
    {
      "description": "S795 and Chandagiri varieties from Krishnagiri Estate at 1500m altitude",
      "expected_varieties": ["s795", "chandagiri"],
      "expected_region": "chikmagalur",
      "expected_estate": "krishnagiri_estate",
      "expected_altitude": 1500
    }
  ],
  "geographic_samples": [
    {
      "description": "High-grown Arabica from Baba Budangiri hills in Karnataka",
      "expected_region": "chikmagalur",
      "expected_state": "karnataka",
      "expected_country": "india"
    },
    {
      "description": "Organic coffee from Araku Valley, Andhra Pradesh",
      "expected_region": "araku_valley",
      "expected_state": "andhra_pradesh",
      "expected_country": "india"
    },
    {
      "description": "Specialty coffee from Meghalaya at 1300m elevation",
      "expected_region": "meghalaya",
      "expected_state": "meghalaya",
      "expected_country": "india",
      "expected_altitude": 1300
    }
  ]
}
```

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
| 2025-01-25 | 1.1 | Enhanced for Indian coffee focus with seed data patterns | Winston (Architect) |
