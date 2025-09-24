# Story A.5: Coffee Classification Parser

## Status
Draft

## Story
**As a** system administrator,
**I want** a coffee classification parser that determines if products are coffee or equipment before normalization,
**so that** only coffee products are processed by Epic C parsers and equipment products are handled separately.

## Acceptance Criteria
1. Coffee classification parser accurately identifies coffee vs equipment products
2. Classification happens before Epic C normalization pipeline (full pipeline only)
3. Coffee products proceed to Epic C parsers for normalization
4. Equipment products are stored with `is_coffee = false` and skipped from normalization
5. Ambiguous products are flagged for manual review with `is_coffee = null`
6. Classification achieves >= 95% accuracy on test dataset
7. False negatives are minimized to prevent equipment contamination of coffee data
8. Parser integrates with existing artifact validation pipeline
9. Classification results are logged for monitoring and debugging
10. Parser handles edge cases (mixed product pages, seasonal items, gifts)
11. Classification only runs during full pipeline runs (not price-only runs)
12. Integration with metadata_only flag to skip classification during price-only runs
13. Performance validation that price-only runs remain fast without classification overhead
14. LLM fallback for low-confidence classifications (< 0.7 confidence)
15. Hybrid approach: keyword-based classification with LLM enhancement for edge cases

## Context
This story addresses the critical need to classify products before normalization to prevent equipment products from contaminating the Epic C normalization pipeline. Without proper classification, equipment products could be processed as coffee, leading to garbage data in the coffee database.

## Tasks / Subtasks
- [ ] Task 1: Design coffee classification logic (AC: 1, 6, 7)
  - [ ] Research coffee vs equipment keyword patterns
  - [ ] Design classification algorithm with confidence scoring
  - [ ] Create test dataset with known coffee/equipment products
  - [ ] Implement keyword-based classification with fallback logic
  - [ ] Add confidence thresholds for ambiguous cases
- [ ] Task 2: Implement classification parser (AC: 2, 8, 14, 15)
  - [ ] Create `coffee_classification_parser.py` module
  - [ ] Implement keyword-based classification with confidence scoring
  - [ ] Add LLM fallback for low-confidence classifications (< 0.7)
  - [ ] Implement hybrid approach: keywords first, LLM for edge cases
  - [ ] Add tag-based classification for products with tags
  - [ ] Integrate with existing artifact validation pipeline
  - [ ] Add classification result logging and monitoring
  - [ ] Implement LLM rate limiting and cost controls
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
  - [ ] Create manual review interface for ambiguous products
  - [ ] Document classification rules and edge cases
  - [ ] Add performance monitoring for classification step

## Dev Notes
### Classification Logic Design
- **Coffee Keywords**: "coffee", "beans", "roast", "blend", "single origin", "espresso", "filter", "pour over"
- **Equipment Keywords**: "grinder", "scale", "brewer", "machine", "equipment", "accessory", "tool", "kit"
- **Confidence Scoring**: 
  - High confidence (>0.8) = auto-classify
  - Medium confidence (0.5-0.8) = LLM fallback
  - Low confidence (<0.5) = manual review
- **LLM Integration**: Use LLM for medium confidence cases to improve accuracy
- **Edge Cases**: Mixed product pages, seasonal items, coffee gifts, equipment bundles

### Integration Points
- **Input**: Raw product data from fetcher
- **Output**: Classification result (`is_coffee: true/false/null`)
- **Coffee Path**: Classification → Epic C Normalization → Database
- **Equipment Path**: Classification → Equipment Storage → Database
- **Ambiguous Path**: Classification → Manual Review Queue
- **Price-Only Path**: Skip classification, use existing database values

### Pipeline Integration
- **Full Pipeline**: Run classification before Epic C normalization
- **Price-Only Pipeline**: Skip classification, use existing database values
- **Integration**: Use metadata_only flag to determine when to classify
- **Performance**: Classification must not impact price-only run speed

### Database Impact
- **No schema changes** - `is_coffee` field already exists
- **Coffee products** - `is_coffee = true`, proceed to normalization
- **Equipment products** - `is_coffee = false`, skip normalization
- **Ambiguous products** - `is_coffee = null`, manual review

### Performance Considerations
- **Classification speed** - Must be fast to not slow down pipeline
- **Memory usage** - Efficient keyword matching algorithms
- **Scalability** - Handle high-volume product processing
- **Caching** - Cache classification results for similar products
- **LLM Cost Control** - Rate limiting and cost monitoring for LLM calls
- **Price-Only Performance** - Must not impact price-only run speed

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
- [ ] Ambiguous products flagged for manual review
- [ ] Classification monitoring and alerting implemented
- [ ] Documentation updated with classification rules
- [ ] Performance requirements met (< 100ms per product)
- [ ] LLM integration implemented for medium confidence cases
- [ ] Price-only runs skip classification and maintain performance
- [ ] LLM cost controls and rate limiting implemented

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-12 | 1.0 | Initial draft created | Architect |

## Related Stories
- **A.3**: Artifact validation (Pydantic models) - Validates `is_coffee` field
- **Epic C**: Normalization parsers - Only processes coffee products
- **Future**: Equipment scraping expansion - Uses `is_coffee = false` products
