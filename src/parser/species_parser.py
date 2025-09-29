"""
Bean species parser for detecting coffee species from product titles and descriptions.

Features:
- Detects arabica, robusta, liberica, and blend species
- Handles ratio-based blends (80/20, 70/30, etc.)
- Supports chicory mixes and filter coffee blends
- Confidence scoring for species detection accuracy
- Batch processing optimization for multiple products
- Comprehensive error handling and logging
- Standalone library with no external dependencies
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger(__name__)


class SpeciesResult(BaseModel):
    """Represents a parsed species result with metadata."""
    
    species: str = Field(..., description="Detected species (arabica, robusta, liberica, blend, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    source: str = Field(..., description="Source of detection (content_parsing, blend_detection, no_match)")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")
    detected_species: List[str] = Field(default_factory=list, description="All detected species")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpeciesResult':
        """Create SpeciesResult from dictionary."""
        return cls.model_validate(data)


class SpeciesConfig(BaseModel):
    """Configuration for species parser."""
    
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for species detection")
    enable_blend_detection: bool = Field(default=True, description="Enable blend detection")
    enable_chicory_detection: bool = Field(default=True, description="Enable chicory mix detection")
    enable_ratio_detection: bool = Field(default=True, description="Enable ratio-based blend detection")
    batch_size: int = Field(default=100, ge=1, description="Batch size for processing")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SpeciesConfig':
        """Create configuration from dictionary."""
        return cls.model_validate(config_dict)


class BeanSpeciesParserService:
    """
    Bean species parser for detecting coffee species from product content.
    
    Supports:
    - Pure species: arabica, robusta, liberica
    - Ratio-based blends: 80/20, 70/30, 60/40, 50/50
    - Chicory mixes: arabica_chicory, robusta_chicory, blend_chicory
    - Filter coffee mixes: filter_coffee_mix
    - Generic blends: blend
    """
    
    def __init__(self, config: Optional[SpeciesConfig] = None):
        """Initialize the species parser with comprehensive patterns."""
        self.config = config or SpeciesConfig()
        
        # Species patterns for detection
        self.species_patterns = {
            'arabica': [
                r'100%\s*arabica', r'pure\s*arabica', r'arabica\s*only',
                r'arabica\s*coffee', r'arabica\s*beans', r'arabica\s*blend'
            ],
            'robusta': [
                r'100%\s*robusta', r'pure\s*robusta', r'robusta\s*only',
                r'robusta\s*coffee', r'robusta\s*beans', r'robusta\s*blend'
            ],
            'liberica': [
                r'liberica', r'coffea\s*liberica', r'liberica\s*coffee',
                r'liberica\s*beans', r'liberica\s*blend'
            ],
            # Ratio-based blends
            'arabica_80_robusta_20': [
                r'80.*20', r'80%\s*arabica.*20%\s*robusta', r'80-20',
                r'arabica.*80.*robusta.*20', r'80/20'
            ],
            'arabica_70_robusta_30': [
                r'70.*30', r'70%\s*arabica.*30%\s*robusta', r'70-30',
                r'arabica.*70.*robusta.*30', r'70/30'
            ],
            'arabica_60_robusta_40': [
                r'60.*40', r'60%\s*arabica.*40%\s*robusta', r'60-40',
                r'arabica.*60.*robusta.*40', r'60/40'
            ],
            'arabica_50_robusta_50': [
                r'50.*50', r'50%\s*arabica.*50%\s*robusta', r'50-50',
                r'arabica.*50.*robusta.*50', r'50/50'
            ],
            'robusta_80_arabica_20': [
                r'80%\s*robusta.*20%\s*arabica', r'robusta.*80.*arabica.*20',
                r'80/20\s*robusta', r'80-20\s*robusta'
            ],
            # Chicory mixes
            'arabica_chicory': [
                r'arabica.*chicory', r'chicory.*arabica',
                r'arabica.*with.*chicory', r'chicory.*with.*arabica'
            ],
            'robusta_chicory': [
                r'robusta.*chicory', r'chicory.*robusta',
                r'robusta.*with.*chicory', r'chicory.*with.*robusta'
            ],
            'blend_chicory': [
                r'blend.*chicory', r'chicory.*blend', r'coffee.*chicory',
                r'chicory.*coffee', r'chicory.*mix'
            ],
            'filter_coffee_mix': [
                r'filter\s*coffee', r'south\s*indian\s*filter',
                r'filter\s*mix', r'filter\s*blend'
            ],
            # Generic blends (fallback)
            'blend': [
                r'arabica\s*&\s*robusta', r'arabica\s*and\s*robusta',
                r'mixed\s*blend', r'coffee\s*blend', r'blend\s*of',
                r'arabica.*robusta', r'robusta.*arabica',
                r'coffee\s*mix', r'mixed\s*coffee'
            ]
        }
        
        # Context patterns for better detection
        self.context_patterns = {
            'species_mention': [
                r'species', r'variety', r'type\s*of\s*bean',
                r'bean\s*type', r'coffee\s*type', r'bean\s*species'
            ],
            'blend_indicators': [
                r'blend', r'mix', r'combination', r'fusion',
                r'blended', r'mixed', r'combined'
            ]
        }
        
        logger.info("Initialized bean species parser with comprehensive patterns")
    
    def parse_species(self, title: str, description: str) -> SpeciesResult:
        """
        Parse bean species from product title and description.
        
        Args:
            title: Product title
            description: Product description
            
        Returns:
            SpeciesResult with detected species and metadata
        """
        try:
            # Handle None inputs
            if title is None and description is None:
                return SpeciesResult(
                    species='unknown',
                    confidence=0.0,
                    source='error',
                    warnings=['Both title and description are None'],
                    detected_species=[]
                )
            if title is None:
                title = ""
            if description is None:
                description = ""
                
            # Combine title and description for analysis
            text = f"{title} {description}".lower()
            
            if not text.strip():
                return SpeciesResult(
                    species='unknown',
                    confidence=0.0,
                    source='no_match',
                    warnings=['Empty title and description'],
                    detected_species=[]
                )
            
            detected_species = []
            confidence_scores = []
            warnings = []
            
            # Check for explicit species mentions in priority order
            # Priority: specific patterns first, then generic ones
            priority_order = [
                'arabica_80_robusta_20', 'arabica_70_robusta_30', 'arabica_60_robusta_40', 'arabica_50_robusta_50',
                'robusta_80_arabica_20',
                'arabica_chicory', 'robusta_chicory', 'blend_chicory',
                'filter_coffee_mix',
                'arabica', 'robusta', 'liberica',
                'blend'
            ]
            
            for species in priority_order:
                if species not in self.species_patterns:
                    continue
                    
                # Skip patterns if detection is disabled
                if species == 'blend' and not self.config.enable_blend_detection:
                    continue
                if species.endswith('_chicory') and not self.config.enable_chicory_detection:
                    continue
                if species.startswith('arabica_') and 'robusta_' in species and not self.config.enable_ratio_detection:
                    continue
                    
                patterns = self.species_patterns[species]
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        detected_species.append(species)
                        confidence_scores.append(0.9)
                        
                        # Check for context that increases confidence
                        if any(re.search(ctx_pattern, text, re.IGNORECASE) 
                               for ctx_pattern in self.context_patterns['species_mention']):
                            confidence_scores[-1] = 0.95
                        
                        # For specific patterns, return immediately
                        if species in ['arabica_chicory', 'robusta_chicory', 'blend_chicory', 'filter_coffee_mix', 
                                     'arabica_80_robusta_20', 'arabica_70_robusta_30', 'arabica_60_robusta_40', 
                                     'arabica_50_robusta_50', 'robusta_80_arabica_20']:
                            return SpeciesResult(
                                species=species,
                                confidence=confidence_scores[-1],
                                source='content_parsing',
                                warnings=warnings,
                                detected_species=detected_species
                            )
            
            # Handle blend detection for generic blends
            if self.config.enable_blend_detection:
                blend_result = self._detect_blends(text, detected_species)
                if blend_result:
                    return blend_result
            
            # Determine primary species
            if detected_species:
                primary_species = max(set(detected_species), key=detected_species.count)
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                
                # Apply confidence threshold
                if avg_confidence < self.config.confidence_threshold:
                    warnings.append(f'Low confidence detection: {avg_confidence:.2f}')
                
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
            
        except Exception as e:
            logger.warning(
                "Species parsing failed",
                title=title,
                description=description,
                error=str(e)
            )
            return SpeciesResult(
                species='unknown',
                confidence=0.0,
                source='error',
                warnings=[f'Parsing error: {str(e)}'],
                detected_species=[]
            )
    
    def _detect_blends(self, text: str, detected_species: List[str]) -> Optional[SpeciesResult]:
        """Detect blend patterns in text."""
        if not self.config.enable_blend_detection:
            return None
        
        # Check for generic blend patterns
        blend_patterns = self.species_patterns['blend']
        for pattern in blend_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Check if both arabica and robusta are mentioned in text
                if (re.search(r'arabica', text, re.IGNORECASE) and 
                    re.search(r'robusta', text, re.IGNORECASE)):
                    # Both species mentioned - likely a blend
                    return SpeciesResult(
                        species='blend',
                        confidence=0.9,
                        source='blend_detection',
                        warnings=[],
                        detected_species=detected_species + ['arabica', 'robusta']
                    )
        
        return None
    
    def batch_parse_species(self, products: List[Dict[str, str]]) -> List[SpeciesResult]:
        """
        Parse species for multiple products in batch for performance optimization.
        
        Args:
            products: List of product dictionaries with 'title' and 'description' keys
            
        Returns:
            List of SpeciesResult objects
        """
        results = []
        
        for i, product in enumerate(products):
            try:
                title = product.get('title', '')
                description = product.get('description', '')
                
                result = self.parse_species(title, description)
                results.append(result)
                
            except Exception as e:
                logger.warning(
                    "Batch species parsing failed for product",
                    product_index=i,
                    error=str(e)
                )
                results.append(SpeciesResult(
                    species='unknown',
                    confidence=0.0,
                    source='error',
                    warnings=[f'Batch parsing error: {str(e)}'],
                    detected_species=[]
                ))
        
        logger.info(
            "Batch species parsing completed",
            total_products=len(products),
            successful_parses=sum(1 for r in results if r.species != 'unknown'),
            average_confidence=sum(r.confidence for r in results) / len(results) if results else 0
        )
        
        return results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the parser."""
        return {
            'parser_version': '1.0.0',
            'supported_species': list(self.species_patterns.keys()),
            'pattern_count': sum(len(patterns) for patterns in self.species_patterns.values()),
            'confidence_threshold': self.config.confidence_threshold,
            'batch_size': self.config.batch_size
        }
    
    def validate_species_enum(self, species: str) -> bool:
        """
        Validate that the detected species is a valid enum value.
        
        Args:
            species: Species string to validate
            
        Returns:
            True if valid enum value, False otherwise
        """
        valid_species = [
            'arabica', 'robusta', 'liberica', 'blend',
            'arabica_80_robusta_20', 'arabica_70_robusta_30',
            'arabica_60_robusta_40', 'arabica_50_robusta_50',
            'robusta_80_arabica_20',
            'arabica_chicory', 'robusta_chicory', 'blend_chicory',
            'filter_coffee_mix'
        ]
        
        return species in valid_species