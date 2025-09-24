# Story C.8: Integration: Complete normalizer pipeline

## Status
Draft

## Story
**As a** data processing engineer,
**I want** to integrate all deterministic normalizers into a complete pipeline to enhance the existing coffee artifact mapping,
**so that** I can provide comprehensive normalization for all coffee product data following the established C.2 pattern without creating separate database operations.

## Acceptance Criteria
1. All deterministic parsers (C.1-C.7) integrated into unified pipeline
2. LLM fallback implemented for ambiguous cases not handled by deterministic parsers
3. Processing warnings stored in `processing_warnings` for all ambiguous cases
4. Integration with A.1-A.5 pipeline through ValidatorIntegrationService composition
5. Enhancement of `ArtifactMapper._map_artifact_data()` following C.2 pattern
6. Use existing `rpc_upsert_coffee()` with all normalized fields
7. Comprehensive test coverage for complete normalizer pipeline
8. Performance optimized for batch processing of product data
9. End-to-end pipeline testing with real product data

## Tasks / Subtasks
- [ ] Task 1: Normalizer pipeline orchestration service implementation (AC: 1, 4, 7, 8)
  - [ ] Create `NormalizerPipelineService` with Pydantic result models
  - [ ] Integrate all C.1-C.7 parsers into unified pipeline
  - [ ] Implement parser execution order and dependency management
  - [ ] Add comprehensive error handling and logging
  - [ ] Create batch processing optimization for multiple products
  - [ ] Add integration tests for pipeline orchestration
  - [ ] Add performance tests for complete pipeline

- [ ] Task 2: LLM fallback service implementation (AC: 2, 3, 7, 8)
  - [ ] Create `LLMFallbackService` with Pydantic result models
  - [ ] Implement LLM integration for ambiguous cases
  - [ ] Implement confidence scoring for LLM results
  - [ ] Add processing warnings for LLM fallback usage
  - [ ] Create batch processing optimization for LLM calls
  - [ ] Add comprehensive error handling and logging
  - [ ] Create unit tests for LLM fallback accuracy
  - [ ] Add performance tests for LLM integration

- [ ] Task 3: ValidatorIntegrationService composition (AC: 4, 5)
  - [ ] Integrate normalizer pipeline with ValidatorIntegrationService
  - [ ] Integrate LLM fallback with ValidatorIntegrationService
  - [ ] Add pipeline configuration to ValidatorConfig
  - [ ] Update ArtifactMapper to use complete pipeline
  - [ ] Add integration tests for complete pipeline composition
  - [ ] Test A.1-A.5 pipeline integration

- [ ] Task 4: ArtifactMapper enhancement following C.2 pattern (AC: 5, 6)
  - [ ] Enhance `ArtifactMapper._map_artifact_data()` with complete normalizer pipeline
  - [ ] Integrate all C.1-C.7 parsers into unified `ArtifactMapper._map_artifact_data()` method
  - [ ] Use existing `rpc_upsert_coffee()` with all normalized fields
  - [ ] Add integration tests for complete ArtifactMapper enhancement
  - [ ] Test end-to-end data flow from complete pipeline to existing RPC
  - [ ] Add end-to-end testing with real product data

## Dev Notes
[Source: Epic C requirements and A.1-A.5 implementation patterns]

**⚠️ IMPORTANT: DO NOT CREATE NEW MIGRATIONS**
- The migration `extend_rpc_upsert_coffee_epic_c_parameters.sql` already handles ALL Epic C parameters
- This includes C.3 (tags/notes), C.4 (grind/species), C.5 (varieties/geographic), C.6 (sensory/hash), and C.7 (text cleaning)
- Dev should use the existing enhanced RPC function with ALL Epic C parameters
- No additional database migrations needed for this story

### Normalizer Pipeline Strategy
[Source: Epic C requirements]

**Pipeline Orchestration:**
```python
class NormalizerPipelineService:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.parsers = self._initialize_parsers(config)
        self.execution_order = self._define_execution_order()
    
    def _initialize_parsers(self, config: PipelineConfig) -> Dict[str, Any]:
        """Initialize all C.1-C.7 parsers"""
        parsers = {}
        
        # C.1: Weight parser
        if config.enable_weight_parsing:
            parsers['weight'] = WeightParser(config.weight_config)
        
        # C.2: Roast & process parser
        if config.enable_roast_parsing:
            parsers['roast'] = RoastLevelParser(config.roast_config)
        if config.enable_process_parsing:
            parsers['process'] = ProcessMethodParser(config.process_config)
        
        # C.3: Tags & notes parser
        if config.enable_tag_parsing:
            parsers['tags'] = TagNormalizationService(config.tag_config)
        if config.enable_notes_parsing:
            parsers['notes'] = NotesExtractionService(config.notes_config)
        
        # C.4: Grind & species parser
        if config.enable_grind_parsing:
            parsers['grind'] = GrindParserService(config.grind_config)
        if config.enable_species_parsing:
            parsers['species'] = BeanSpeciesParserService(config.species_config)
        
        # C.5: Variety & geographic parser
        if config.enable_variety_parsing:
            parsers['variety'] = VarietyExtractionService(config.variety_config)
        if config.enable_geographic_parsing:
            parsers['geographic'] = GeographicParserService(config.geographic_config)
        
        # C.6: Sensory & hash parser
        if config.enable_sensory_parsing:
            parsers['sensory'] = SensoryParserService(config.sensory_config)
        if config.enable_hash_generation:
            parsers['hash'] = ContentHashService(config.hash_config)
        
        # C.7: Text cleaning parser
        if config.enable_text_cleaning:
            parsers['text_cleaning'] = TextCleaningService(config.text_cleaning_config)
        if config.enable_text_normalization:
            parsers['text_normalization'] = TextNormalizationService(config.text_normalization_config)
        
        return parsers
    
    def _define_execution_order(self) -> List[str]:
        """Define parser execution order based on dependencies"""
        return [
            'text_cleaning',      # C.7: Clean text first
            'text_normalization', # C.7: Normalize text
            'weight',             # C.1: Parse weight
            'roast',              # C.2: Parse roast level
            'process',            # C.2: Parse process method
            'grind',              # C.4: Parse grind type
            'species',            # C.4: Parse bean species
            'variety',            # C.5: Parse varieties
            'geographic',         # C.5: Parse geographic data
            'sensory',            # C.6: Parse sensory parameters
            'tags',               # C.3: Parse tags
            'notes',              # C.3: Parse notes
            'hash'                # C.6: Generate hashes last
        ]
    
    def process_artifact(self, artifact: Dict) -> PipelineResult:
        """Process artifact through complete normalizer pipeline"""
        results = {}
        warnings = []
        confidence_scores = []
        
        # Execute parsers in order
        for parser_name in self.execution_order:
            if parser_name in self.parsers:
                try:
                    parser = self.parsers[parser_name]
                    result = self._execute_parser(parser, parser_name, artifact)
                    results[parser_name] = result
                    confidence_scores.append(result.confidence)
                    
                    # Check if result needs LLM fallback
                    if result.confidence < self.config.llm_fallback_threshold:
                        warnings.append(f"Low confidence for {parser_name}: {result.confidence}")
                        
                except Exception as e:
                    warnings.append(f"Parser {parser_name} failed: {str(e)}")
                    results[parser_name] = None
        
        # Determine if LLM fallback is needed
        needs_llm_fallback = any(
            result is None or result.confidence < self.config.llm_fallback_threshold
            for result in results.values()
            if result is not None
        )
        
        return PipelineResult(
            results=results,
            warnings=warnings,
            confidence_scores=confidence_scores,
            needs_llm_fallback=needs_llm_fallback,
            overall_confidence=self._calculate_overall_confidence(confidence_scores)
        )
```

### LLM Fallback Strategy
[Source: Epic C requirements]

**LLM Integration:**
```python
class LLMFallbackService:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.llm_client = self._initialize_llm_client(config)
    
    def _initialize_llm_client(self, config: LLMConfig) -> Any:
        """Initialize LLM client based on configuration"""
        if config.llm_provider == 'openai':
            return OpenAI(api_key=config.api_key)
        elif config.llm_provider == 'anthropic':
            return Anthropic(api_key=config.api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")
    
    def process_ambiguous_cases(self, artifact: Dict, pipeline_results: PipelineResult) -> LLMResult:
        """Process ambiguous cases using LLM fallback"""
        ambiguous_fields = self._identify_ambiguous_fields(pipeline_results)
        
        if not ambiguous_fields:
            return LLMResult(
                results={},
                warnings=[],
                confidence_scores=[],
                llm_usage=None
            )
        
        # Prepare LLM prompt
        prompt = self._prepare_llm_prompt(artifact, ambiguous_fields)
        
        # Call LLM
        llm_response = self._call_llm(prompt)
        
        # Parse LLM response
        parsed_results = self._parse_llm_response(llm_response, ambiguous_fields)
        
        return LLMResult(
            results=parsed_results,
            warnings=[f"LLM fallback used for: {', '.join(ambiguous_fields)}"],
            confidence_scores=[0.8] * len(ambiguous_fields),  # LLM confidence
            llm_usage=self._calculate_llm_usage(llm_response)
        )
    
    def _identify_ambiguous_fields(self, pipeline_results: PipelineResult) -> List[str]:
        """Identify fields that need LLM fallback"""
        ambiguous_fields = []
        
        for parser_name, result in pipeline_results.results.items():
            if result is None or result.confidence < self.config.llm_fallback_threshold:
                ambiguous_fields.append(parser_name)
        
        return ambiguous_fields
    
    def _prepare_llm_prompt(self, artifact: Dict, ambiguous_fields: List[str]) -> str:
        """Prepare LLM prompt for ambiguous cases"""
        prompt = f"""
        Analyze the following coffee product data and provide structured information for the ambiguous fields: {', '.join(ambiguous_fields)}
        
        Product Title: {artifact.get('title', '')}
        Product Description: {artifact.get('description', '')}
        
        Please provide structured JSON output for the following fields:
        """
        
        for field in ambiguous_fields:
            prompt += f"\n- {field}: [your analysis]"
        
        prompt += "\n\nProvide only valid JSON output."
        return prompt
```

### Integration Points
[Source: A.1-A.5 implementation patterns]

**ValidatorIntegrationService Integration:**
```python
class ValidatorIntegrationService:
    def __init__(self, config: ValidatorConfig):
        # Initialize all parsers
        self.weight_parser = WeightParser() if config.enable_weight_parsing else None
        self.roast_parser = RoastLevelParser() if config.enable_roast_parsing else None
        self.process_parser = ProcessMethodParser() if config.enable_process_parsing else None
        self.grind_parser = GrindParserService(config.grind_config) if config.enable_grind_parsing else None
        self.species_parser = BeanSpeciesParserService(config.species_config) if config.enable_species_parsing else None
        self.variety_parser = VarietyExtractionService(config.variety_config) if config.enable_variety_parsing else None
        self.geographic_parser = GeographicParserService(config.geographic_config) if config.enable_geographic_parsing else None
        self.sensory_parser = SensoryParserService(config.sensory_config) if config.enable_sensory_parsing else None
        self.hash_service = ContentHashService(config.hash_config) if config.enable_hash_generation else None
        self.text_cleaner = TextCleaningService(config.text_cleaning_config) if config.enable_text_cleaning else None
        self.text_normalizer = TextNormalizationService(config.text_normalization_config) if config.enable_text_normalization else None
        self.tags_parser = TagNormalizationService(config.tag_config) if config.enable_tag_parsing else None
        self.notes_parser = NotesExtractionService(config.notes_config) if config.enable_notes_parsing else None
        
        # Initialize complete pipeline
        self.normalizer_pipeline = NormalizerPipelineService(config.pipeline_config)
        self.llm_fallback = LLMFallbackService(config.llm_config) if config.enable_llm_fallback else None
        
        # Pass to ArtifactMapper
        self.artifact_mapper = ArtifactMapper(integration_service=self)
```

**ArtifactMapper Integration:**
```python
class ArtifactMapper:
    def __init__(self, integration_service: ValidatorIntegrationService):
        self.integration_service = integration_service
    
    def _map_artifact_data(self, artifact: Dict) -> Dict:
        """Process artifact through complete normalizer pipeline"""
        # Run through complete pipeline
        pipeline_result = self.integration_service.normalizer_pipeline.process_artifact(artifact)
        
        # Apply LLM fallback if needed
        if pipeline_result.needs_llm_fallback and self.integration_service.llm_fallback:
            llm_result = self.integration_service.llm_fallback.process_ambiguous_cases(artifact, pipeline_result)
            # Merge LLM results with pipeline results
            pipeline_result = self._merge_results(pipeline_result, llm_result)
        
        # Map results to artifact
        artifact = self._map_pipeline_results(artifact, pipeline_result)
        
        return artifact
```

### File Locations
Based on Epic C requirements and A.1-A.5 integration:

**New Files:**
- Normalizer pipeline service: `src/parser/normalizer_pipeline.py` (new)
- LLM fallback service: `src/parser/llm_fallback.py` (new)
- Pipeline configuration: `src/config/pipeline_config.py` (new)
- LLM configuration: `src/config/llm_config.py` (new)
- Integration tests: `tests/parser/test_normalizer_pipeline_integration.py` (new)
- Integration tests: `tests/parser/test_llm_fallback_integration.py` (new)

**Extension Files (Modify Existing):**
- Extend existing: `src/validator/artifact_mapper.py` ✅ **EXISTS** (enhance `_map_artifact_data`)
- Extend existing: `src/validator/database_integration.py` ✅ **EXISTS** (add complete pipeline processing)
- Extend existing: `src/validator/rpc_client.py` ✅ **EXISTS** (enhance `upsert_coffee_artifact`)
- Extend existing: `tests/validator/test_artifact_mapper.py` ✅ **EXISTS** (add complete pipeline tests)

**Configuration Files:**
- Pipeline processing config: `src/config/pipeline_config.py` (new)
- LLM processing config: `src/config/llm_config.py` (new)
- Test fixtures: `tests/parser/fixtures/pipeline_samples.json` (new)
- Test fixtures: `tests/parser/fixtures/llm_fallback_samples.json` (new)
- Documentation: `docs/parser/normalizer_pipeline.md` (new)
- Documentation: `docs/parser/llm_fallback.md` (new)

### Performance Requirements
[Source: Epic C requirements]

**Processing Performance:**
- **Batch Processing**: Handle 100+ products per batch
- **Response Time**: < 10 seconds for 100 products (complete pipeline)
- **Memory Usage**: < 500MB for batch processing
- **LLM Fallback**: < 5 seconds per LLM call
- **Error Handling**: Graceful fallback for processing failures

### Testing Strategy
[Source: Epic C requirements]

**Unit Tests:**
- Pipeline orchestration accuracy across different product types
- LLM fallback accuracy for ambiguous cases
- Error handling for corrupted or invalid data
- Performance tests for complete pipeline

**Integration Tests:**
- A.1-A.5 pipeline integration with complete normalizer pipeline
- Database integration with all normalized data storage
- End-to-end artifact processing with complete pipeline
- Performance benchmarks for large product sets
- LLM fallback integration testing

## Definition of Done
- [ ] Normalizer pipeline service implemented with all C.1-C.7 parsers
- [ ] LLM fallback service implemented for ambiguous cases
- [ ] ValidatorIntegrationService composition completed
- [ ] Database integration with all normalized data storage
- [ ] Comprehensive test coverage for complete normalizer pipeline
- [ ] Performance optimization for batch processing
- [ ] Integration tests with existing pipeline components
- [ ] End-to-end testing with real product data
- [ ] Documentation updated with complete normalizer pipeline implementation

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial story creation with A.1-A.5 integration strategy | Bob (Scrum Master) |
