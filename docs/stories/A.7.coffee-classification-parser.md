# Story A.7: Coffee Classification Parser

## Status
In Progress

## Story
**As a** system administrator,
**I want** a coffee classification parser that determines if products are coffee or equipment during artifact validation,
**so that** only coffee products are processed by Epic C parsers and equipment products are handled separately.

## Acceptance Criteria
1. Coffee classification parser accurately identifies coffee vs equipment products
2. Classification happens during artifact validation (Epic A) before Epic C normalization
3. Coffee products proceed to Epic C parsers for normalization
4. Equipment products are stored with `is_coffee = false` and skipped from normalization
5. Uncertain products are automatically classified as equipment (skip to equipment)
6. Classification achieves >= 95% accuracy on test dataset
7. False negatives are minimized to prevent equipment contamination of coffee data
8. Parser integrates with existing artifact validation pipeline
9. Classification results are logged for monitoring and debugging
10. Parser handles edge cases (mixed product pages, seasonal items, gifts)
11. Classification only runs during full pipeline runs (not price-only runs)
12. Integration with metadata_only flag to skip classification during price-only runs
13. Performance validation that price-only runs remain fast without classification overhead
14. Automated dual-classification: code-based (≥0.7) → LLM fallback (<0.7) → equipment skip (<0.6)
15. No manual review required - fully automated pipeline

## Context
This story addresses the critical need to classify products before normalization to prevent equipment products from contaminating the Epic C normalization pipeline. Without proper classification, equipment products could be processed as coffee, leading to garbage data in the coffee database.

## Tasks / Subtasks
- [ ] Task 1: Extend existing classification logic (AC: 1, 6, 7)
  - [ ] Extend `src/parser/weight_parser.py` `_is_coffee_context()` method to `_is_coffee_product()`
  - [ ] Add equipment-specific keyword patterns following same structure as coffee keywords
  - [ ] Implement confidence scoring system following weight_parser.py pattern
  - [ ] Create test dataset with known coffee/equipment products
  - [ ] Add confidence thresholds for ambiguous cases (follow existing heuristics pattern)
- [ ] Task 2: Implement classification parser (AC: 2, 8, 14, 15)
  - [ ] Create `src/parser/coffee_classification_parser.py` following weight_parser.py structure
  - [ ] Implement keyword-based classification with confidence scoring (follow weight_parser pattern)
  - [ ] Add LLM fallback for low-confidence classifications (< 0.7) using existing Epic D services
  - [ ] Implement hybrid approach: keywords first, LLM for edge cases
  - [ ] Add tag-based classification for products with tags
  - [ ] Integrate with existing artifact validation pipeline
  - [ ] Add classification result logging and monitoring (follow existing patterns)
  - [ ] Implement LLM rate limiting and cost controls using existing Epic D infrastructure
- [ ] Task 3: Pipeline integration (AC: 3, 4, 5, 11, 12, 13)
  - [ ] Modify main pipeline to classify before normalization (full pipeline only)
  - [ ] Add metadata_only flag checks to skip classification during price-only runs
  - [ ] Route coffee products to Epic C normalization
  - [ ] Route equipment products to equipment storage (skip normalization)
  - [ ] Route ambiguous products to manual review queue
  - [ ] Update artifact mapper to handle classification results
  - [ ] Validate price-only runs remain fast without classification overhead
- [ ] Task 4: Testing and validation (AC: 6, 7, 9)
  - [ ] Create comprehensive test dataset with edge cases
  - [ ] Test classification accuracy on known products
  - [ ] Test false negative prevention (equipment not classified as coffee)
  - [ ] Test false positive handling (coffee not classified as equipment)
  - [ ] Validate integration with existing pipeline
- [ ] Task 5: Monitoring and maintenance (AC: 9, 10)
  - [ ] Add classification accuracy monitoring
  - [ ] Implement alerting for classification failures
  - [ ] Document classification rules and edge cases
  - [ ] Add performance monitoring for classification step
  - [ ] Monitor automated skip rates for uncertain products

## Dev Notes
### Classification Logic Design
- **Leverage Existing**: Extend `src/parser/weight_parser.py` `_is_coffee_context()` method to `_is_coffee_product()`
- **Follow Existing Patterns**: Use same confidence scoring and heuristics as weight_parser.py
- **Coffee Keywords**: Leverage existing coffee keywords from weight_parser.py (lines 430-438)
- **Equipment Keywords**: Add equipment-specific keywords following same pattern
- **Automated Flow**: 
  1. Code-based classification (confidence score)
  2. If confidence ≥ 0.7 → Direct classification
  3. If confidence < 0.7 → Send to LLM for analysis
  4. If LLM confidence ≥ 0.6 → Use LLM result
  5. If LLM confidence < 0.6 → Skip product (equipment)
- **LLM Integration**: Use existing Epic D LLM services for uncertain cases
- **Edge Cases**: Mixed product pages, seasonal items, coffee gifts, equipment bundles

### Integration Points
- **Input**: Raw product data from fetcher (before validation)
- **Output**: Classification result (`is_coffee: true/false/null`) added to artifact
- **Coffee Path**: Validation → Classification → Epic C Normalization → Database
- **Equipment Path**: Validation → Classification → Equipment Storage (skip normalization)
- **Uncertain Path**: Validation → Classification → Equipment Storage (automated skip)
- **Price-Only Path**: Skip classification, use existing database values

### Pipeline Integration
- **Full Pipeline**: Validation → Classification → Epic C Normalization (if coffee)
- **Price-Only Pipeline**: Skip classification, use existing database values
- **Integration**: Use existing `metadata_only` flag pattern (like `ImageProcessingGuard`)
- **Performance**: Classification must not impact price-only run speed

### Database Impact
- **No schema changes** - `is_coffee` field already exists
- **Coffee products** - `is_coffee = true`, proceed to Epic C normalization
- **Equipment products** - `is_coffee = false`, skip Epic C normalization but still store in `coffees` table
- **Uncertain products** - `is_coffee = false`, automated skip to equipment (no manual review)

### File Structure Alignment
- **Classification Service**: `src/parser/coffee_classification_parser.py` (follows weight_parser.py structure)
- **Integration**: Extend `src/validator/artifact_validator.py` to include classification
- **Configuration**: Add to `src/config/validator_config.py`
- **Tests**: `tests/parser/test_coffee_classification_parser.py`

### Existing Infrastructure to Leverage
- **Coffee Context Logic**: `src/parser/weight_parser.py` lines 430-438 (`_is_coffee_context()`)
- **Confidence Scoring**: `src/parser/weight_parser.py` lines 440-465 (`_apply_coffee_heuristics()`)
- **Heuristics Pattern**: `src/parser/roast_parser.py` and `src/parser/process_parser.py` have similar patterns
- **LLM Services**: Epic D services already implemented for fallback classification
- **Configuration System**: Existing parser configuration patterns in `src/config/`
- **Monitoring**: Existing `NormalizerPipelineMetrics` pattern for classification monitoring

### Performance Considerations
- **Classification speed** - Must be fast to not slow down pipeline
- **Memory usage** - Efficient keyword matching algorithms
- **Scalability** - Handle high-volume product processing
- **Caching** - Cache classification results for similar products
- **LLM Cost Control** - Use existing Epic D rate limiting and cost monitoring
- **Price-Only Performance** - Must not impact price-only run speed
- **Monitoring** - Use existing `NormalizerPipelineMetrics` pattern

## Testing
### Test Cases
- **Coffee Products**: Various coffee types, roasts, origins
- **Equipment Products**: Grinders, scales, brewers, accessories
- **Edge Cases**: Mixed products, seasonal items, gifts, bundles
- **Ambiguous Cases**: Products with unclear classification

### Success Criteria
- **Accuracy**: >= 95% correct classification on test dataset
- **False Negatives**: < 2% equipment classified as coffee
- **False Positives**: < 3% coffee classified as equipment
- **Performance**: Classification completes within 100ms per product
- **Integration**: Seamless integration with existing pipeline
- **LLM Efficiency**: LLM used only for < 20% of products (medium confidence)
- **Price-Only Performance**: No impact on price-only run speed

## Definition of Done
- [ ] Coffee classification parser implemented and tested
- [ ] Classification accuracy >= 95% on test dataset
- [ ] False negative rate < 2% (equipment not classified as coffee)
- [ ] Integration with existing pipeline completed
- [ ] Coffee products route to Epic C normalization
- [ ] Equipment products skip normalization
- [ ] Uncertain products automatically skip to equipment (no manual review)
- [ ] Classification monitoring and alerting implemented
- [ ] Documentation updated with classification rules
- [ ] Performance requirements met (< 100ms per product)
- [ ] LLM integration implemented for medium confidence cases
- [ ] Price-only runs skip classification and maintain performance
- [ ] LLM cost controls and rate limiting implemented
- [ ] Automated dual-classification flow implemented (code → LLM → equipment skip)

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial draft created | Architect |

## Related Stories
- **A.3**: Artifact validation (Pydantic models) - Validates `is_coffee` field
- **Epic C**: Normalization parsers - Only processes coffee products
- **Future**: Equipment scraping expansion - Uses `is_coffee = false` products
