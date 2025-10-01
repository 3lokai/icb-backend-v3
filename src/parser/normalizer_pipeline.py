"""
Normalizer pipeline orchestration service.

Features:
- Integrate all C.1-C.7 parsers into unified pipeline
- LLM fallback for ambiguous cases using Epic D services
- Pipeline state management and error recovery
- Batch processing optimization
- Comprehensive logging and metrics
"""

import time
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from structlog import get_logger

from .pipeline_state import (
    PipelineState, PipelineStage, PipelineError, PipelineWarning, 
    ParserResult, LLMResult
)
from .error_recovery import PipelineErrorRecovery, RecoveryDecision
from .transaction_manager import PipelineTransactionManager, TransactionBoundary
from ..config.pipeline_config import PipelineConfig
from ..llm.deepseek_wrapper import DeepSeekWrapperService
from ..llm.cache_service import CacheService
from ..llm.rate_limiter import RateLimiter
from ..llm.confidence_evaluator import ConfidenceEvaluator
from ..llm.review_workflow import ReviewWorkflow
from ..llm.enrichment_persistence import EnrichmentPersistence
from ..llm.llm_metrics import LLMServiceMetrics
from ..monitoring.confidence_metrics import ConfidenceMetrics
from ..monitoring.normalizer_pipeline_metrics import NormalizerPipelineMetrics

# Import all C.1-C.7 parsers
from .weight_parser import WeightParser, WeightResult
from .roast_parser import RoastLevelParser, RoastResult
from .process_parser import ProcessMethodParser, ProcessResult
from .tag_normalization import TagNormalizationService, TagNormalizationResult
from .notes_extraction import NotesExtractionService, NotesExtractionResult
from .grind_brewing_parser import GrindBrewingParser, GrindBrewingResult
from .species_parser import BeanSpeciesParserService, SpeciesResult
from .variety_extraction import VarietyExtractionService, VarietyResult
from .geographic_parser import GeographicParserService, GeographicResult
from .sensory_parser import SensoryParserService, SensoryResult
from .content_hash import ContentHashService, HashResult
from .text_cleaning import TextCleaningService, TextCleaningResult
from .text_normalization import TextNormalizationService, TextNormalizationResult

logger = get_logger(__name__)


class PipelineExecutionError(Exception):
    """Exception raised during pipeline execution."""
    
    def __init__(self, message: str, state: PipelineState):
        super().__init__(message)
        self.state = state


class NormalizerPipelineService:
    """Main normalizer pipeline orchestration service."""
    
    def __init__(self, config: PipelineConfig, rpc_client=None):
        self.config = config
        self.parsers = self._initialize_parsers(config)
        self.execution_order = self._define_execution_order()
        self.error_recovery = PipelineErrorRecovery(config.error_recovery)
        self.state_manager = PipelineStateManager()
        self.transaction_manager = PipelineTransactionManager(rpc_client) if rpc_client else None
        self.metrics = NormalizerPipelineMetrics() if config.enable_metrics else None
        
        # Epic D services (if available)
        self.llm_service = None
        self.cache_service = None
        self.rate_limiter = None
        self.confidence_evaluator = None
        self.review_workflow = None
        self.enrichment_persistence = None
        self.llm_metrics = None
        self.confidence_metrics = None
        
        logger.info("Normalizer pipeline service initialized", 
                   enabled_parsers=config.get_enabled_parsers())
    
    def _initialize_parsers(self, config: PipelineConfig) -> Dict[str, Any]:
        """Initialize all C.1-C.7 parsers."""
        parsers = {}
        
        try:
            # C.1: Weight parser
            if config.enable_weight_parsing:
                parsers['weight'] = WeightParser()
                logger.debug("Weight parser initialized")
            
            # C.2: Roast & process parser
            if config.enable_roast_parsing:
                parsers['roast'] = RoastLevelParser()
                logger.debug("Roast parser initialized")
            if config.enable_process_parsing:
                parsers['process'] = ProcessMethodParser()
                logger.debug("Process parser initialized")
            
            # C.3: Tags & notes parser
            if config.enable_tag_parsing:
                parsers['tags'] = TagNormalizationService()
                logger.debug("Tag parser initialized")
            if config.enable_notes_parsing:
                parsers['notes'] = NotesExtractionService()
                logger.debug("Notes parser initialized")
            
            # C.4: Grind & species parser
            if config.enable_grind_parsing:
                parsers['grind'] = GrindBrewingParser()
                logger.debug("Grind parser initialized")
            if config.enable_species_parsing:
                parsers['species'] = BeanSpeciesParserService()
                logger.debug("Species parser initialized")
            
            # C.5: Variety & geographic parser
            if config.enable_variety_parsing:
                parsers['variety'] = VarietyExtractionService()
                logger.debug("Variety parser initialized")
            if config.enable_geographic_parsing:
                parsers['geographic'] = GeographicParserService()
                logger.debug("Geographic parser initialized")
            
            # C.6: Sensory & hash parser
            if config.enable_sensory_parsing:
                parsers['sensory'] = SensoryParserService()
                logger.debug("Sensory parser initialized")
            if config.enable_hash_generation:
                parsers['hash'] = ContentHashService()
                logger.debug("Hash parser initialized")
            
            # C.7: Text cleaning parser
            if config.enable_text_cleaning:
                from ..config.text_cleaning_config import TextCleaningConfig
                text_cleaning_config = TextCleaningConfig()
                parsers['text_cleaning'] = TextCleaningService(text_cleaning_config)
                logger.debug("Text cleaning parser initialized")
            if config.enable_text_normalization:
                from ..config.text_normalization_config import TextNormalizationConfig
                text_normalization_config = TextNormalizationConfig()
                parsers['text_normalization'] = TextNormalizationService(text_normalization_config)      
                logger.debug("Text normalization parser initialized")
            
        except Exception as e:
            logger.error("Failed to initialize parsers", error=str(e))
            raise PipelineExecutionError(f"Parser initialization failed: {str(e)}", PipelineState())
        
        return parsers
    
    def _define_execution_order(self) -> List[str]:
        """Define parser execution order based on dependencies."""
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
    
    def initialize_epic_d_services(self, 
                                  llm_service: DeepSeekWrapperService,
                                  cache_service: CacheService,
                                  rate_limiter: RateLimiter,
                                  confidence_evaluator: ConfidenceEvaluator,
                                  review_workflow: ReviewWorkflow,
                                  enrichment_persistence: EnrichmentPersistence,
                                  llm_metrics: LLMServiceMetrics,
                                  confidence_metrics: ConfidenceMetrics):
        """Initialize Epic D services for LLM fallback."""
        self.llm_service = llm_service
        self.cache_service = cache_service
        self.rate_limiter = rate_limiter
        self.confidence_evaluator = confidence_evaluator
        self.review_workflow = review_workflow
        self.enrichment_persistence = enrichment_persistence
        self.llm_metrics = llm_metrics
        self.confidence_metrics = confidence_metrics
        
        logger.info("Epic D services initialized for LLM fallback")
    
    def process_artifact(self, artifact: Dict) -> Dict[str, Any]:
        """Process artifact through complete normalizer pipeline."""
        start_time = time.time()
        
        # Initialize pipeline state
        state = PipelineState(
            execution_id=str(uuid.uuid4()),
            stage=PipelineStage.INITIALIZED,
            deterministic_results={},
            llm_results={},
            errors=[],
            warnings=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Create transaction for pipeline processing
        transaction = None
        if self.transaction_manager:
            transaction = self.transaction_manager.create_transaction(
                state.execution_id, 
                TransactionBoundary.PIPELINE_START
            )
            transaction.mark_in_progress()
        
        try:
            logger.info("Starting pipeline processing", execution_id=state.execution_id)
            
            # Execute deterministic parsers
            state.stage = PipelineStage.DETERMINISTIC_PARSING
            deterministic_results = self._execute_deterministic_parsers(artifact, state)
            
            # Check if LLM fallback is needed
            needs_llm_fallback = self._needs_llm_fallback(deterministic_results)
            
            if needs_llm_fallback and self.llm_service:
                state.stage = PipelineStage.LLM_FALLBACK
                llm_results = self._execute_llm_fallback(artifact, deterministic_results, state)
                state.llm_results = llm_results
                
                # Record LLM fallback metrics
                if self.metrics and llm_results:
                    for field, result in llm_results.items():
                        self.metrics.record_llm_fallback_usage(state.execution_id, field)
            
            state.stage = PipelineStage.COMPLETED
            processing_time = time.time() - start_time
            
            # Commit transaction if successful
            if transaction:
                transaction.commit()
            
            # Record metrics
            if self.metrics:
                self.metrics.record_pipeline_execution(
                    state.execution_id,
                    processing_time,
                    state.stage.value,
                    list(deterministic_results.keys()),
                    len(state.llm_results) > 0
                )
                
                # Record pipeline confidence
                self.metrics.record_pipeline_confidence(
                    state.execution_id,
                    state.stage.value,
                    state.get_overall_confidence()
                )
            
            logger.info("Pipeline processing completed", 
                       execution_id=state.execution_id,
                       processing_time=processing_time,
                       deterministic_results=len(deterministic_results),
                       llm_results=len(state.llm_results))
            
            return self._create_pipeline_result(state, processing_time)
            
        except Exception as e:
            state.stage = PipelineStage.FAILED
            state.add_error(PipelineError(
                stage=state.stage,
                error_type="pipeline_failure",
                message=str(e),
                recoverable=self.error_recovery.is_recoverable(e)
            ))
            
            # Record error metrics
            if self.metrics:
                self.metrics.record_pipeline_error(
                    state.execution_id,
                    state.stage.value,
                    "pipeline_failure"
                )
            
            # Rollback transaction on failure
            if transaction:
                transaction.rollback()
            
            logger.error("Pipeline execution failed", 
                        execution_id=state.execution_id,
                        error=str(e))
            
            raise PipelineExecutionError(f"Pipeline execution failed: {str(e)}", state)
    
    def _execute_deterministic_parsers(self, artifact: Dict, state: PipelineState) -> Dict[str, ParserResult]:
        """Execute deterministic parsers with error recovery."""
        results = {}
        
        for parser_name in self.execution_order:
            if parser_name in self.parsers:
                try:
                    parser = self.parsers[parser_name]
                    result = self._execute_parser(parser, parser_name, artifact)
                    results[parser_name] = result
                    state.add_parser_result(parser_name, result)
                    
                    # Update artifact with intermediate results for sequential processing
                    if parser_name == 'text_cleaning' and result.success and result.result_data:
                        # Update artifact with cleaned text for next parsers
                        if 'title_cleaned' in result.result_data:
                            artifact['title_cleaned'] = result.result_data['title_cleaned']
                        if 'description_cleaned' in result.result_data:
                            artifact['description_cleaned'] = result.result_data['description_cleaned']
                    
                    # Record parser metrics
                    if self.metrics:
                        self.metrics.record_parser_success(
                            parser_name,
                            state.execution_id,
                            result.success,
                            result.confidence
                        )
                    
                    # Check if result needs LLM fallback
                    if result.confidence < self.config.llm_fallback_threshold:
                        state.add_warning(PipelineWarning(
                            stage=PipelineStage.DETERMINISTIC_PARSING,
                            parser_name=parser_name,
                            message=f"Low confidence: {result.confidence}",
                            severity="medium"
                        ))
                        
                except Exception as e:
                    # Attempt error recovery
                    recovery_decision = self.error_recovery.recover_from_parser_failure(parser_name, e)
                    
                    if recovery_decision.should_retry:
                        logger.info("Retrying parser", parser=parser_name, delay=recovery_decision.retry_delay)
                        time.sleep(recovery_decision.retry_delay)
                        # Retry logic would go here
                        continue
                    else:
                        state.add_error(PipelineError(
                            stage=PipelineStage.DETERMINISTIC_PARSING,
                            error_type="parser_failure",
                            message=f"Parser {parser_name} failed: {str(e)}",
                            recoverable=False,
                            parser_name=parser_name
                        ))
                        results[parser_name] = None
        
        return results
    
    def _extract_confidence(self, result: Any) -> float:
        """Extract confidence score from different result object types."""
        # Handle different confidence field types
        if hasattr(result, 'confidence'):
            confidence = result.confidence
            if isinstance(confidence, str):
                # Convert string confidence to float
                confidence_map = {'high': 0.9, 'medium': 0.6, 'low': 0.3}
                return confidence_map.get(confidence.lower(), 0.5)
            elif isinstance(confidence, (int, float)):
                return float(confidence)
        
        # Handle confidence_scores (List[float] or Dict[str, float])
        if hasattr(result, 'confidence_scores'):
            confidence_scores = result.confidence_scores
            if isinstance(confidence_scores, list) and confidence_scores:
                return float(sum(confidence_scores) / len(confidence_scores))
            elif isinstance(confidence_scores, dict) and confidence_scores:
                return float(sum(confidence_scores.values()) / len(confidence_scores))
        
        # Default confidence if no confidence field found
        return 0.5
    
    def _execute_parser(self, parser: Any, parser_name: str, artifact: Dict) -> ParserResult:
        """Execute individual parser with timing and error handling."""
        start_time = time.time()
        
        try:
            # Execute parser based on type with correct method signatures
            if parser_name == 'weight':
                result = parser.parse_weight(artifact.get('title', '') + ' ' + artifact.get('description', ''))
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'roast':
                result = parser.parse_roast_level(artifact.get('title', '') + ' ' + artifact.get('description', ''))
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'process':
                result = parser.parse_process_method(artifact.get('title', '') + ' ' + artifact.get('description', ''))
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'tags':
                # TagNormalizationService.normalize_tags() expects List[str]
                raw_tags = artifact.get('tags', [])
                if isinstance(raw_tags, str):
                    raw_tags = [raw_tags]
                result = parser.normalize_tags(raw_tags)
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'notes':
                result = parser.extract_notes(artifact.get('description', ''))
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'grind':
                # GrindBrewingParser.parse_grind_brewing() expects variant Dict
                variant = artifact.get('variants', [{}])[0] if artifact.get('variants') else {}
                result = parser.parse_grind_brewing(variant)
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'species':
                result = parser.parse_species(artifact.get('title', ''), artifact.get('description', ''))
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'variety':
                result = parser.extract_varieties(artifact.get('description', ''))
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'geographic':
                result = parser.parse_geographic(artifact.get('description', ''))
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'sensory':
                result = parser.parse_sensory(artifact.get('description', ''))
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'hash':
                # ContentHashService.generate_hashes() expects artifact Dict
                result = parser.generate_hashes(artifact)
                # Handle different confidence field types
                confidence = self._extract_confidence(result)
                return ParserResult(
                    parser_name=parser_name,
                    success=confidence > 0.0,
                    confidence=confidence,
                    result_data=result.to_dict(),
                    warnings=getattr(result, 'parsing_warnings', getattr(result, 'warnings', [])),
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'text_cleaning':
                # Process both title and description for text cleaning
                title_text = artifact.get('title', '')
                description_text = artifact.get('description', '')
                
                # Clean title
                title_result = parser.clean_text(title_text)
                # Clean description  
                description_result = parser.clean_text(description_text)
                
                # Combine results
                combined_result = {
                    'title_cleaned': title_result.cleaned_text,
                    'description_cleaned': description_result.cleaned_text,
                    'title_confidence': title_result.confidence,
                    'description_confidence': description_result.confidence,
                    'title_changes': title_result.changes_made,
                    'description_changes': description_result.changes_made,
                    'title_warnings': title_result.warnings,
                    'description_warnings': description_result.warnings
                }
                
                # Use average confidence
                avg_confidence = (title_result.confidence + description_result.confidence) / 2
                
                return ParserResult(
                    parser_name=parser_name,
                    success=avg_confidence > 0.0,
                    confidence=avg_confidence,
                    result_data=combined_result,
                    warnings=title_result.warnings + description_result.warnings,
                    execution_time=time.time() - start_time
                )
            elif parser_name == 'text_normalization':
                # Process both title and description for text normalization
                # Use cleaned text if available from text cleaning, otherwise use original
                # Check if we have cleaned text from previous text cleaning parser
                title_text = artifact.get('title_cleaned', artifact.get('title', ''))
                description_text = artifact.get('description_cleaned', artifact.get('description', ''))
                
                # Normalize title
                title_result = parser.normalize_text(title_text)
                # Normalize description
                description_result = parser.normalize_text(description_text)
                
                # Combine results
                combined_result = {
                    'title_normalized': title_result.normalized_text,
                    'description_normalized': description_result.normalized_text,
                    'title_confidence': title_result.confidence,
                    'description_confidence': description_result.confidence,
                    'title_changes': title_result.changes_made,
                    'description_changes': description_result.changes_made,
                    'title_warnings': title_result.warnings,
                    'description_warnings': description_result.warnings
                }
                
                # Use average confidence
                avg_confidence = (title_result.confidence + description_result.confidence) / 2
                
                return ParserResult(
                    parser_name=parser_name,
                    success=avg_confidence > 0.0,
                    confidence=avg_confidence,
                    result_data=combined_result,
                    warnings=title_result.warnings + description_result.warnings,
                    execution_time=time.time() - start_time
                )
            else:
                # Fallback for unknown parsers
                logger.warning("Unknown parser type", parser=parser_name)
                return ParserResult(
                    parser_name=parser_name,
                    success=False,
                    confidence=0.0,
                    result_data={},
                    warnings=[f"Unknown parser type: {parser_name}"],
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            logger.error("Parser execution failed", parser=parser_name, error=str(e))
            return ParserResult(
                parser_name=parser_name,
                success=False,
                confidence=0.0,
                result_data={},
                warnings=[f"Parser failed: {str(e)}"],
                execution_time=time.time() - start_time
            )
    
    def _needs_llm_fallback(self, deterministic_results: Dict[str, ParserResult]) -> bool:
        """Check if LLM fallback is needed based on confidence scores."""
        if not deterministic_results:
            return False
        
        low_confidence_count = sum(1 for result in deterministic_results.values() 
                                 if result and result.confidence < self.config.llm_fallback_threshold)
        
        return low_confidence_count > 0
    
    def _execute_llm_fallback(self, artifact: Dict, deterministic_results: Dict[str, ParserResult], state: PipelineState) -> Dict[str, LLMResult]:
        """Execute LLM fallback for ambiguous cases using Epic D services."""
        if not self.llm_service:
            logger.warning("LLM service not available for fallback")
            return {}
        
        llm_results = {}
        ambiguous_fields = self._identify_ambiguous_fields(deterministic_results)
        
        if not ambiguous_fields:
            return llm_results
        
        logger.info("Executing LLM fallback", fields=ambiguous_fields)
        
        for field in ambiguous_fields:
            try:
                # Check rate limits
                if not self.rate_limiter.can_make_request(artifact.get('roaster_id', 'default')):
                    logger.warning("Rate limit exceeded for LLM fallback", field=field)
                    continue
                
                # Use Epic D's LLM service
                llm_result = self.llm_service.enrich_field(artifact, field, self._get_llm_prompt(field))
                
                # Record the request
                self.rate_limiter.record_request(artifact.get('roaster_id', 'default'))
                
                # Apply confidence evaluation
                confidence_evaluation = self.confidence_evaluator.evaluate_confidence(llm_result)
                
                # Persist enrichment data
                enrichment_id = self.enrichment_persistence.persist_enrichment(artifact, llm_result, confidence_evaluation)
                
                if confidence_evaluation.action == 'auto_apply':
                    llm_results[field] = LLMResult(
                        field_name=field,
                        success=True,
                        confidence=confidence_evaluation.final_confidence,
                        result_data=llm_result.to_dict(),
                        warnings=[],
                        execution_time=0.0
                    )
                else:
                    # Mark for review
                    self.review_workflow.mark_for_review(artifact, llm_result, confidence_evaluation)
                    llm_results[field] = LLMResult(
                        field_name=field,
                        success=False,
                        confidence=confidence_evaluation.final_confidence,
                        result_data={'enrichment_id': enrichment_id, 'status': 'review'},
                        warnings=['Marked for manual review'],
                        execution_time=0.0
                    )
                
            except Exception as e:
                logger.error("LLM fallback failed", field=field, error=str(e))
                llm_results[field] = LLMResult(
                    field_name=field,
                    success=False,
                    confidence=0.0,
                    result_data={},
                    warnings=[f"LLM fallback failed: {str(e)}"],
                    execution_time=0.0
                )
        
        return llm_results
    
    def _identify_ambiguous_fields(self, deterministic_results: Dict[str, ParserResult]) -> List[str]:
        """Identify fields that need LLM fallback."""
        ambiguous_fields = []
        
        for parser_name, result in deterministic_results.items():
            if result is None or result.confidence < self.config.llm_fallback_threshold:
                ambiguous_fields.append(parser_name)
        
        return ambiguous_fields
    
    def _get_llm_prompt(self, field: str) -> str:
        """Get LLM prompt for specific field."""
        prompts = {
            'weight': "Extract and normalize weight information from the product title and description.",
            'roast': "Determine the roast level of this coffee product.",
            'process': "Identify the processing method used for this coffee.",
            'tags': "Extract and normalize product tags and categories.",
            'notes': "Extract tasting notes and flavor descriptions.",
            'grind': "Determine the grind type for this coffee product.",
            'species': "Identify the coffee species (arabica, robusta, blend).",
            'variety': "Extract coffee variety information.",
            'geographic': "Extract geographic origin information.",
            'sensory': "Extract sensory parameters and flavor profiles."
        }
        
        return prompts.get(field, f"Process the {field} field for this coffee product.")
    
    def _create_pipeline_result(self, state: PipelineState, processing_time: float) -> Dict[str, Any]:
        """Create final pipeline result."""
        return {
            'execution_id': state.execution_id,
            'stage': state.stage.value,
            'processing_time': processing_time,
            'deterministic_results': {k: v.to_dict() for k, v in state.deterministic_results.items()},
            'llm_results': {k: v.to_dict() for k, v in state.llm_results.items()},
            'errors': [error.to_dict() for error in state.errors],
            'warnings': [warning.to_dict() for warning in state.warnings],
            'overall_confidence': state.get_overall_confidence(),
            'deterministic_confidence': state.get_deterministic_confidence(),
            'llm_confidence': state.get_llm_confidence(),
            'needs_llm_fallback': state.needs_llm_fallback(self.config.llm_fallback_threshold),
            'is_completed': state.is_completed(),
            'has_errors': state.has_errors(),
            'has_warnings': state.has_warnings()
        }


class PipelineStateManager:
    """Manager for pipeline state operations."""
    
    def __init__(self):
        self.active_states: Dict[str, PipelineState] = {}
    
    def create_state(self) -> PipelineState:
        """Create new pipeline state."""
        state = PipelineState()
        self.active_states[state.execution_id] = state
        return state
    
    def get_state(self, execution_id: str) -> Optional[PipelineState]:
        """Get pipeline state by execution ID."""
        return self.active_states.get(execution_id)
    
    def update_state(self, state: PipelineState):
        """Update pipeline state."""
        self.active_states[state.execution_id] = state
    
    def cleanup_state(self, execution_id: str):
        """Clean up completed pipeline state."""
        if execution_id in self.active_states:
            del self.active_states[execution_id]
