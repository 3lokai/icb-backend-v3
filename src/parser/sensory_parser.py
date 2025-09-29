"""
Sensory parameter parsing service for extracting numeric ratings from product descriptions.
"""

import re
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from structlog import get_logger

from ..config.sensory_config import SensoryConfig

logger = get_logger(__name__)


class SensoryResult(BaseModel):
    """Result model for sensory parameter extraction."""
    
    acidity: Optional[float] = Field(default=None, ge=1.0, le=10.0, description="Acidity rating (1-10 scale)")
    body: Optional[float] = Field(default=None, ge=1.0, le=10.0, description="Body rating (1-10 scale)")
    sweetness: Optional[float] = Field(default=None, ge=1.0, le=10.0, description="Sweetness rating (1-10 scale)")
    bitterness: Optional[float] = Field(default=None, ge=1.0, le=10.0, description="Bitterness rating (1-10 scale)")
    aftertaste: Optional[float] = Field(default=None, ge=1.0, le=10.0, description="Aftertaste rating (1-10 scale)")
    clarity: Optional[float] = Field(default=None, ge=1.0, le=10.0, description="Clarity rating (1-10 scale)")
    confidence: str = Field(default="medium", description="Confidence level (high/medium/low)")
    source: str = Field(default="icb_inferred", description="Source of sensory data")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Extraction timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SensoryParserService:
    """
    Service for extracting numeric sensory parameters from product descriptions.
    
    Features:
    - Pattern-based extraction for 6 sensory parameters (1-10 scale)
    - Confidence scoring for extraction accuracy
    - Source tracking for data provenance
    - Batch processing optimization
    - Comprehensive error handling
    """
    
    def __init__(self, config: Optional[SensoryConfig] = None):
        """
        Initialize sensory parser service.
        
        Args:
            config: Sensory configuration
        """
        self.config = config or SensoryConfig()
        self.logger = logger.bind(service="sensory_parser")
        
        # Initialize pattern mappings
        self.pattern_mappings = {
            'acidity': self.config.acidity_patterns,
            'body': self.config.body_patterns,
            'sweetness': self.config.sweetness_patterns,
            'bitterness': self.config.bitterness_patterns,
            'aftertaste': self.config.aftertaste_patterns,
            'clarity': self.config.clarity_patterns
        }
        
        # Service stats
        self.stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'parameters_extracted': 0,
            'confidence_scores': {'high': 0, 'medium': 0, 'low': 0}
        }
    
    def parse_sensory(self, description: str) -> SensoryResult:
        """
        Parse numeric sensory parameters from product description.
        
        Args:
            description: Product description text
            
        Returns:
            SensoryResult with extracted parameters
        """
        if not description or not isinstance(description, str):
            self.logger.warning("Invalid description provided for sensory parsing")
            return SensoryResult()
        
        self.logger.debug("Starting sensory parameter extraction", description_length=len(description))
        
        try:
            # Extract individual parameters
            acidity = self._extract_numeric_rating(description, 'acidity')
            body = self._extract_numeric_rating(description, 'body')
            sweetness = self._extract_numeric_rating(description, 'sweetness')
            bitterness = self._extract_numeric_rating(description, 'bitterness')
            aftertaste = self._extract_numeric_rating(description, 'aftertaste')
            clarity = self._extract_numeric_rating(description, 'clarity')
            
            # Calculate confidence based on extraction success
            confidence = self._calculate_confidence(acidity, body, sweetness, bitterness, aftertaste, clarity)
            
            result = SensoryResult(
                acidity=acidity,
                body=body,
                sweetness=sweetness,
                bitterness=bitterness,
                aftertaste=aftertaste,
                clarity=clarity,
                confidence=confidence,
                source=self.config.default_source
            )
            
            # Update stats
            self.stats['total_processed'] += 1
            self.stats['successful_extractions'] += 1
            self.stats['parameters_extracted'] += sum(1 for param in [acidity, body, sweetness, bitterness, aftertaste, clarity] if param is not None)
            self.stats['confidence_scores'][confidence] += 1
            
            self.logger.debug(
                "Sensory parameter extraction completed",
                parameters_found=sum(1 for param in [acidity, body, sweetness, bitterness, aftertaste, clarity] if param is not None),
                confidence=confidence
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to extract sensory parameters", error=str(e))
            self.stats['total_processed'] += 1
            self.stats['failed_extractions'] += 1
            return SensoryResult()
    
    def parse_sensory_batch(self, descriptions: List[str]) -> List[SensoryResult]:
        """
        Parse sensory parameters for multiple descriptions in batch.
        
        Optimized for processing 100+ products with < 4 second response time.
        
        Args:
            descriptions: List of product descriptions
            
        Returns:
            List of SensoryResult objects
        """
        if not descriptions:
            return []
        
        batch_size = len(descriptions)
        self.logger.info("Starting batch sensory parameter extraction", batch_size=batch_size)
        
        # Process descriptions in batch for performance
        results = []
        for i, description in enumerate(descriptions):
            try:
                result = self.parse_sensory(description)
                results.append(result)
            except Exception as e:
                self.logger.error("Failed to process description in batch", index=i, error=str(e))
                results.append(SensoryResult())
        
        # Log batch completion stats
        successful_extractions = sum(1 for r in results if r.acidity is not None or r.body is not None)
        self.logger.info(
            "Batch sensory parameter extraction completed",
            total_processed=batch_size,
            successful=successful_extractions,
            success_rate=successful_extractions / batch_size if batch_size > 0 else 0
        )
        
        return results
    
    def _extract_numeric_rating(self, description: str, parameter: str) -> Optional[float]:
        """
        Extract numeric rating (1-10 scale) for specific sensory parameter.
        
        Args:
            description: Product description text
            parameter: Sensory parameter name (acidity, body, etc.)
            
        Returns:
            Numeric rating or None if not found
        """
        if parameter not in self.pattern_mappings:
            self.logger.warning(f"Unknown sensory parameter: {parameter}")
            return None
        
        patterns = self.pattern_mappings[parameter]
        
        for level, pattern_list in patterns.items():
            for pattern in pattern_list:
                try:
                    if re.search(pattern, description, re.IGNORECASE):
                        rating = self._map_to_numeric_rating(level)
                        self.logger.debug(f"Found {parameter} pattern", level=level, rating=rating, pattern=pattern)
                        return rating
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern for {parameter}: {pattern}", error=str(e))
                    continue
        
        return None
    
    def _map_to_numeric_rating(self, level: str) -> float:
        """
        Map text levels to numeric ratings (1-10 scale).
        
        Args:
            level: Text level (low, medium, high, etc.)
            
        Returns:
            Numeric rating
        """
        return self.config.rating_mapping.get(level, 5.0)  # Default to medium
    
    def _calculate_confidence(self, acidity: Optional[float], body: Optional[float], 
                            sweetness: Optional[float], bitterness: Optional[float],
                            aftertaste: Optional[float], clarity: Optional[float]) -> str:
        """
        Calculate confidence level based on extraction success.
        
        Args:
            acidity, body, sweetness, bitterness, aftertaste, clarity: Extracted ratings
            
        Returns:
            Confidence level (high/medium/low)
        """
        parameters = [acidity, body, sweetness, bitterness, aftertaste, clarity]
        extracted_count = sum(1 for param in parameters if param is not None)
        
        if extracted_count >= 3:
            return "high"
        elif extracted_count >= 1:
            return "medium"
        else:
            return "low"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        stats = self.stats.copy()
        
        # Calculate success rate
        if stats['total_processed'] > 0:
            stats['success_rate'] = stats['successful_extractions'] / stats['total_processed']
            stats['failure_rate'] = stats['failed_extractions'] / stats['total_processed']
            stats['avg_parameters_per_extraction'] = stats['parameters_extracted'] / stats['successful_extractions'] if stats['successful_extractions'] > 0 else 0
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['avg_parameters_per_extraction'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset service statistics."""
        self.stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'parameters_extracted': 0,
            'confidence_scores': {'high': 0, 'medium': 0, 'low': 0}
        }
