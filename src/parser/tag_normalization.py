"""
Tag normalization service for categorizing and standardizing product tags.

Features:
- India-specific coffee tag categorization
- Confidence scoring for tag normalization accuracy
- Batch processing optimization for multiple products
- Comprehensive error handling and logging
- Pydantic result models for type safety
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger(__name__)


class TagNormalizationResult(BaseModel):
    """Represents a tag normalization result with metadata."""
    
    normalized_tags: Dict[str, List[str]] = Field(..., description="Normalized tags by category")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores by category")
    warnings: List[str] = Field(default_factory=list, description="Normalization warnings")
    total_tags: int = Field(..., description="Total number of input tags")
    normalized_count: int = Field(..., description="Number of successfully normalized tags")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TagNormalizationResult':
        """Create TagNormalizationResult from dictionary."""
        return cls.model_validate(data)


class TagNormalizationService:
    """
    Service for normalizing product tags into consistent categories.
    
    Features:
    - India-specific coffee tag categorization
    - Confidence scoring for normalization accuracy
    - Batch processing for multiple products
    - Comprehensive error handling
    """
    
    def __init__(self, config=None):
        """Initialize tag normalization service with India-specific categories."""
        self.config = config
        # India-specific coffee tag categories
        self.category_mapping = {
            'flavor': [
                'chocolate', 'caramel', 'vanilla', 'nutty', 'fruity', 'spicy', 
                'earthy', 'bold', 'smooth', 'rich', 'sweet', 'bitter', 'acidic',
                'citrus', 'berry', 'floral', 'herbal', 'woody', 'smoky'
            ],
            'origin': [
                'karnataka', 'kerala', 'tamil-nadu', 'andhra-pradesh', 'odisha',
                'manipur', 'nagaland', 'assam', 'west-bengal', 'madhya-pradesh',
                'karnataka-coorg', 'karnataka-chikmagalur', 'kerala-wayanad',
                'tamil-nadu-nilgiris', 'andhra-araku-valley'
            ],
            'regions': [
                'chikmagalur', 'coorg', 'wayanad', 'baba-budangiri', 'nilgiris',
                'araku-valley', 'manipur-hills', 'nagaland-hills', 'assam-valley',
                'baba-budangiri-hills', 'coorg-hills', 'wayanad-hills'
            ],
            'roasters': [
                'blue-tokai', 'third-wave', 'davidoff', 'tata-coffee', 'hunkal-heights',
                'kapi-kottai', 'black-baza', 'flying-squirrel', 'devans', 'coffee-day',
                'starbucks-india', 'costa-coffee', 'cafe-coffee-day', 'barista'
            ],
            'process': [
                'washed', 'natural', 'honey', 'semi-washed', 'monsooned', 'wet-hulled',
                'dry-processed', 'semi-washed', 'fully-washed', 'pulped-natural'
            ],
            'roast': [
                'light', 'medium', 'dark', 'espresso', 'city', 'full-city',
                'vienna', 'french', 'italian', 'blonde', 'medium-light',
                'medium-dark', 'extra-dark'
            ],
            'grind': [
                'whole-bean', 'coarse', 'medium', 'fine', 'espresso', 'extra-fine',
                'french-press', 'drip', 'pour-over', 'cold-brew', 'turkish'
            ],
            'estates': [
                'tata-coffee', 'hunkal-heights', 'kapi-kottai', 'blue-tokai-estates',
                'devans-estates', 'coffee-day-estates', 'starbucks-estates'
            ],
            'varieties': [
                'kent', 'sl28', 'sl34', 'caturra', 'bourbon', 'typica', 'catimor',
                'arabica', 'robusta', 'liberica', 'excelsa', 'hybrid'
            ],
            'specialty': [
                'single-origin', 'blend', 'organic', 'fair-trade', 'rainforest-alliance',
                'bird-friendly', 'shade-grown', 'direct-trade', 'specialty-grade',
                'premium', 'artisan', 'craft', 'micro-lot'
            ]
        }
        
        # Create reverse mapping for faster lookups
        self.tag_to_category = {}
        for category, tags in self.category_mapping.items():
            for tag in tags:
                self.tag_to_category[tag.lower()] = category
        
        # Fuzzy matching patterns for common variations
        self.fuzzy_patterns = {
            'chocolate': ['choco', 'cocoa', 'choc'],
            'caramel': ['caramal', 'caramell'],
            'vanilla': ['vanila', 'vanill'],
            'nutty': ['nut', 'nuts', 'almond', 'walnut', 'pecan'],
            'fruity': ['fruit', 'fruits', 'berry', 'berries'],
            'spicy': ['spice', 'spices', 'cinnamon', 'clove', 'cardamom'],
            'earthy': ['earth', 'soil', 'mushroom'],
            'bold': ['strong', 'intense', 'robust'],
            'smooth': ['creamy', 'silky', 'velvety'],
            'rich': ['full-bodied', 'heavy', 'dense'],
            'sweet': ['sugary', 'honeyed', 'syrupy'],
            'bitter': ['bitterness', 'harsh', 'astringent'],
            'acidic': ['acidity', 'bright', 'tart', 'sour'],
            'citrus': ['lemon', 'orange', 'lime', 'grapefruit'],
            'floral': ['flower', 'blossom', 'jasmine', 'rose'],
            'herbal': ['herb', 'sage', 'thyme', 'basil'],
            'woody': ['wood', 'oak', 'cedar', 'pine'],
            'smoky': ['smoke', 'charred', 'burnt', 'toasted']
        }
        
        logger.info(
            "Tag normalization service initialized",
            categories=len(self.category_mapping),
            total_tags=sum(len(tags) for tags in self.category_mapping.values())
        )
    
    def normalize_tags(self, raw_tags: List[str]) -> TagNormalizationResult:
        """
        Normalize raw tags into structured categories.
        
        Args:
            raw_tags: List of raw tag strings
            
        Returns:
            TagNormalizationResult with normalized tags and metadata
        """
        try:
            if not raw_tags:
                return TagNormalizationResult(
                    normalized_tags={},
                    confidence_scores={},
                    warnings=['No tags provided'],
                    total_tags=0,
                    normalized_count=0
                )
            
            normalized = {}
            confidence_scores = {}
            warnings = []
            normalized_count = 0
            
            for tag in raw_tags:
                if not tag or not tag.strip():
                    continue
                
                tag_clean = tag.strip().lower()
                category, confidence = self._categorize_tag(tag_clean)
                
                if category:
                    if category not in normalized:
                        normalized[category] = []
                    normalized[category].append(tag.strip())
                    confidence_scores[category] = max(
                        confidence_scores.get(category, 0.0), 
                        confidence
                    )
                    normalized_count += 1
                else:
                    warnings.append(f"Unrecognized tag: {tag}")
            
            # Sort tags within each category for consistent output
            for category in normalized:
                normalized[category] = sorted(normalized[category])
            
            result = TagNormalizationResult(
                normalized_tags=normalized,
                confidence_scores=confidence_scores,
                warnings=warnings,
                total_tags=len(raw_tags),
                normalized_count=normalized_count
            )
            
            logger.info(
                "Tag normalization completed",
                total_tags=len(raw_tags),
                normalized_count=normalized_count,
                categories=len(normalized),
                warnings_count=len(warnings)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Tag normalization failed",
                raw_tags=raw_tags,
                error=str(e)
            )
            return TagNormalizationResult(
                normalized_tags={},
                confidence_scores={},
                warnings=[f"Normalization error: {str(e)}"],
                total_tags=len(raw_tags) if raw_tags else 0,
                normalized_count=0
            )
    
    def _categorize_tag(self, tag: str) -> Tuple[Optional[str], float]:
        """
        Categorize a single tag and return confidence score.
        
        Args:
            tag: Clean tag string
            
        Returns:
            Tuple of (category, confidence) or (None, 0.0) if not found
        """
        # Direct match (highest confidence)
        if tag in self.tag_to_category:
            return self.tag_to_category[tag], 0.95
        
        # Fuzzy matching
        for pattern_tag, variations in self.fuzzy_patterns.items():
            if tag in variations:
                category = self.tag_to_category.get(pattern_tag)
                if category:
                    return category, 0.85
        
        # Partial matching (lower confidence)
        for category, tags in self.category_mapping.items():
            for category_tag in tags:
                if tag in category_tag or category_tag in tag:
                    return category, 0.70
        
        # No match found
        return None, 0.0
    
    def batch_normalize_tags(self, tag_lists: List[List[str]]) -> List[TagNormalizationResult]:
        """
        Normalize multiple tag lists in batch for performance optimization.
        
        Args:
            tag_lists: List of tag lists to normalize
            
        Returns:
            List of TagNormalizationResult objects
        """
        results = []
        for tag_list in tag_lists:
            result = self.normalize_tags(tag_list)
            results.append(result)
        
        total_tags = sum(len(tag_list) for tag_list in tag_lists)
        total_normalized = sum(result.normalized_count for result in results)
        
        logger.info(
            "Batch tag normalization completed",
            total_lists=len(tag_lists),
            total_tags=total_tags,
            total_normalized=total_normalized,
            average_confidence=sum(
                sum(result.confidence_scores.values()) / len(result.confidence_scores)
                for result in results if result.confidence_scores
            ) / len(results) if results else 0
        )
        
        return results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the service."""
        return {
            'service_version': '1.0.0',
            'category_mapping': len(self.category_mapping),
            'fuzzy_matching': len(self.fuzzy_patterns),
            'supported_categories': len(self.category_mapping)
        }
