# Story C.7: Name & description cleaner

## Status
Draft

## Story
**As a** data processing engineer,
**I want** to clean and normalize product names and descriptions to enhance the existing coffee artifact mapping,
**so that** I can provide consistent, clean text data for coffee products following the established C.2 pattern without creating separate database operations.

## Acceptance Criteria
1. Product names cleaned and normalized (HTML removal, formatting standardization)
2. Product descriptions cleaned and normalized (HTML removal, formatting standardization)
3. Text cleaning confidence scoring implemented with parsing warnings for ambiguous cases
4. Integration with A.1-A.5 pipeline through ValidatorIntegrationService composition
5. Enhancement of `ArtifactMapper._map_artifact_data()` following C.2 pattern
6. Use existing `rpc_upsert_coffee()` with existing name and description fields
7. Comprehensive test coverage for text cleaning and normalization
8. Performance optimized for batch processing of product data

## Tasks / Subtasks
- [ ] Task 1: Text cleaning service implementation (AC: 1, 2, 3, 7, 8)
  - [ ] Create `TextCleaningService` with Pydantic result models
  - [ ] Implement HTML removal from names and descriptions
  - [ ] Implement text formatting standardization
  - [ ] Add confidence scoring for text cleaning accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for text cleaning accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 2: Text normalization service implementation (AC: 1, 2, 3, 7, 8)
  - [ ] Create `TextNormalizationService` with Pydantic result models
  - [ ] Implement text standardization (case, spacing, punctuation)
  - [ ] Implement special character handling and encoding
  - [ ] Add confidence scoring for text normalization accuracy
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for text normalization accuracy
  - [ ] Add performance tests for batch processing scenarios

- [ ] Task 3: ValidatorIntegrationService composition (AC: 4, 5)
  - [ ] Integrate text cleaning with ValidatorIntegrationService
  - [ ] Integrate text normalization with ValidatorIntegrationService
  - [ ] Add parser configuration to ValidatorConfig
  - [ ] Update ArtifactMapper to use new parsers
  - [ ] Add integration tests for parser composition
  - [ ] Test A.1-A.5 pipeline integration

- [ ] Task 4: ArtifactMapper enhancement following C.2 pattern (AC: 5, 6)
  - [ ] Enhance `ArtifactMapper._map_artifact_data()` with text cleaning
  - [ ] Enhance `ArtifactMapper._map_artifact_data()` with text normalization
  - [ ] Use existing `rpc_upsert_coffee()` with existing name and description fields
  - [ ] Add integration tests for ArtifactMapper enhancement
  - [ ] Test end-to-end data flow from cleaning to existing RPC

## Dev Notes
[Source: Epic C requirements and A.1-A.5 implementation patterns]

**⚠️ IMPORTANT: DO NOT CREATE NEW MIGRATIONS**
- The migration `extend_rpc_upsert_coffee_epic_c_parameters.sql` already handles ALL Epic C parameters
- This includes C.3 (tags/notes), C.4 (grind/species), C.5 (varieties/geographic), C.6 (sensory/hash), and C.7 (text cleaning)
- Dev should use the existing enhanced RPC function with `p_title_cleaned`, `p_description_cleaned` parameters
- No additional database migrations needed for this story

### Text Cleaning Strategy
[Source: Epic C requirements]

**HTML Removal and Cleaning:**
```python
class TextCleaningService:
    def __init__(self, config: TextCleaningConfig):
        self.config = config
        self.html_parser = BeautifulSoup if config.use_beautifulsoup else None
        self.cleaning_rules = config.cleaning_rules
    
    def clean_text(self, text: str) -> TextCleaningResult:
        """Clean and normalize text content"""
        original_text = text
        cleaned_text = text
        
        # HTML removal
        if self.html_parser:
            cleaned_text = self._remove_html(cleaned_text)
        else:
            cleaned_text = self._remove_html_regex(cleaned_text)
        
        # Special character handling
        cleaned_text = self._handle_special_characters(cleaned_text)
        
        # Whitespace normalization
        cleaned_text = self._normalize_whitespace(cleaned_text)
        
        return TextCleaningResult(
            original_text=original_text,
            cleaned_text=cleaned_text,
            changes_made=self._identify_changes(original_text, cleaned_text),
            confidence=self._calculate_confidence(original_text, cleaned_text),
            warnings=self._generate_warnings(original_text, cleaned_text)
        )
    
    def _remove_html(self, text: str) -> str:
        """Remove HTML tags using BeautifulSoup"""
        if self.html_parser:
            soup = BeautifulSoup(text, 'html.parser')
            return soup.get_text()
        return text
    
    def _remove_html_regex(self, text: str) -> str:
        """Remove HTML tags using regex"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = html.unescape(text)
        return text
    
    def _handle_special_characters(self, text: str) -> str:
        """Handle special characters and encoding"""
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        # Remove control characters
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace characters"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text
```

### Text Normalization Strategy
[Source: Epic C requirements]

**Text Standardization:**
```python
class TextNormalizationService:
    def __init__(self, config: TextNormalizationConfig):
        self.config = config
        self.normalization_rules = config.normalization_rules
    
    def normalize_text(self, text: str) -> TextNormalizationResult:
        """Normalize text content"""
        original_text = text
        normalized_text = text
        
        # Case normalization
        if self.config.normalize_case:
            normalized_text = self._normalize_case(normalized_text)
        
        # Spacing normalization
        if self.config.normalize_spacing:
            normalized_text = self._normalize_spacing(normalized_text)
        
        # Punctuation normalization
        if self.config.normalize_punctuation:
            normalized_text = self._normalize_punctuation(normalized_text)
        
        return TextNormalizationResult(
            original_text=original_text,
            normalized_text=normalized_text,
            changes_made=self._identify_changes(original_text, normalized_text),
            confidence=self._calculate_confidence(original_text, normalized_text),
            warnings=self._generate_warnings(original_text, normalized_text)
        )
    
    def _normalize_case(self, text: str) -> str:
        """Normalize text case"""
        if self.config.case_style == 'title':
            return text.title()
        elif self.config.case_style == 'lower':
            return text.lower()
        elif self.config.case_style == 'upper':
            return text.upper()
        elif self.config.case_style == 'sentence':
            return text.capitalize()
        return text
    
    def _normalize_spacing(self, text: str) -> str:
        """Normalize spacing in text"""
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove spaces around punctuation
        text = re.sub(r'\s+([.!?,:;])', r'\1', text)
        return text
    
    def _normalize_punctuation(self, text: str) -> str:
        """Normalize punctuation in text"""
        # Standardize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r'[''']', "'", text)
        # Standardize dashes
        text = re.sub(r'[–—]', '-', text)
        return text
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
        if config.enable_variety_parsing:
            self.variety_parser = VarietyExtractionService(config.variety_config)
        if config.enable_geographic_parsing:
            self.geographic_parser = GeographicParserService(config.geographic_config)
        if config.enable_sensory_parsing:
            self.sensory_parser = SensoryParserService(config.sensory_config)
        if config.enable_hash_generation:
            self.hash_service = ContentHashService(config.hash_config)
        
        # New parsers
        if config.enable_text_cleaning:
            self.text_cleaner = TextCleaningService(config.text_cleaning_config)
        if config.enable_text_normalization:
            self.text_normalizer = TextNormalizationService(config.text_normalization_config)
        
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
        if self.integration_service.text_cleaner:
            title_result = self.integration_service.text_cleaner.clean_text(artifact.get('title', ''))
            description_result = self.integration_service.text_cleaner.clean_text(artifact.get('description', ''))
            artifact['title_cleaned'] = title_result.cleaned_text
            artifact['description_cleaned'] = description_result.cleaned_text
        
        if self.integration_service.text_normalizer:
            title_norm_result = self.integration_service.text_normalizer.normalize_text(artifact.get('title_cleaned', ''))
            description_norm_result = self.integration_service.text_normalizer.normalize_text(artifact.get('description_cleaned', ''))
            artifact['title_normalized'] = title_norm_result.normalized_text
            artifact['description_normalized'] = description_norm_result.normalized_text
        
        return artifact
```

### File Locations
Based on Epic C requirements and A.1-A.5 integration:

**New Files:**
- Text cleaning service: `src/parser/text_cleaning.py` (new)
- Text normalization service: `src/parser/text_normalization.py` (new)
- Text cleaning configuration: `src/config/text_cleaning_config.py` (new)
- Text normalization configuration: `src/config/text_normalization_config.py` (new)
- Integration tests: `tests/parser/test_text_cleaning_integration.py` (new)
- Integration tests: `tests/parser/test_text_normalization_integration.py` (new)

**Extension Files (Modify Existing):**
- Extend existing: `src/validator/artifact_mapper.py` ✅ **EXISTS** (enhance `_map_artifact_data`)
- Extend existing: `src/validator/database_integration.py` ✅ **EXISTS** (add text cleaning processing)
- Extend existing: `src/validator/rpc_client.py` ✅ **EXISTS** (enhance `upsert_coffee_artifact`)
- Extend existing: `tests/validator/test_artifact_mapper.py` ✅ **EXISTS** (add text cleaning tests)

**Configuration Files:**
- Text cleaning config: `src/config/text_cleaning_config.py` (new)
- Text normalization config: `src/config/text_normalization_config.py` (new)
- Test fixtures: `tests/parser/fixtures/text_cleaning_samples.json` (new)
- Test fixtures: `tests/parser/fixtures/text_normalization_samples.json` (new)
- Documentation: `docs/parser/text_cleaning.md` (new)
- Documentation: `docs/parser/text_normalization.md` (new)

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
- Text cleaning accuracy across different HTML formats
- Text normalization accuracy across different text formats
- Error handling for corrupted or invalid data
- Performance tests for batch processing

**Integration Tests:**
- A.1-A.5 pipeline integration with text cleaning and normalization
- Database integration with cleaned text storage
- End-to-end artifact processing with text cleaning
- Performance benchmarks for large product sets

## Definition of Done
- [ ] Text cleaning service implemented with HTML removal and cleaning
- [ ] Text normalization service implemented with text standardization
- [ ] ValidatorIntegrationService composition completed
- [ ] Database integration with cleaned and normalized text data
- [ ] Comprehensive test coverage for text cleaning and normalization
- [ ] Performance optimization for batch processing
- [ ] Integration tests with existing pipeline components
- [ ] Documentation updated with text cleaning and normalization implementation

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation with A.1-A.5 integration strategy | Bob (Scrum Master) |
