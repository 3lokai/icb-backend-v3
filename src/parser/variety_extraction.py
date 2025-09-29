"""
Indian Coffee Variety Extraction Service

Extracts Indian coffee varieties from product descriptions using pattern matching.
Supports traditional Indian varieties (S795, S9, S8, S5, Cauvery, Kent, etc.) and
premium varieties found in Indian estates (Geisha, SL28, SL34, etc.).
"""

import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from structlog import get_logger

logger = get_logger(__name__)


@dataclass
class VarietyResult:
    """Result of variety extraction from product description."""
    varieties: List[str]
    confidence_scores: List[float]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'varieties': self.varieties,
            'confidence_scores': self.confidence_scores,
            'warnings': self.warnings
        }


class VarietyExtractionService:
    """
    Service for extracting Indian coffee varieties from product descriptions.
    
    Features:
    - Pattern matching for traditional Indian varieties
    - Premium variety detection (Geisha, SL28, SL34, etc.)
    - Confidence scoring for extraction accuracy
    - Batch processing optimization
    - Comprehensive error handling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize variety extraction service.
        
        Args:
            config: Configuration dictionary for variety extraction
        """
        self.config = config or {}
        
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
        
        # Statistics tracking
        self.stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'varieties_found': 0,
            'warnings_generated': 0
        }
    
    def extract_varieties(self, description: str) -> VarietyResult:
        """
        Extract coffee varieties from product description.
        
        Args:
            description: Product description text
            
        Returns:
            VarietyResult with extracted varieties, confidence scores, and warnings
        """
        if not description or not isinstance(description, str):
            logger.warning("Invalid description provided for variety extraction")
            return VarietyResult(
                varieties=[],
                confidence_scores=[],
                warnings=["Invalid or empty description provided"]
            )
        
        self.stats['total_extractions'] += 1
        
        try:
            varieties = []
            confidence_scores = []
            warnings = []
            
            # Extract varieties using pattern matching
            for variety, patterns in self.variety_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, description, re.IGNORECASE):
                        varieties.append(variety)
                        confidence_scores.append(0.9)  # High confidence for pattern matches
                        break
            
            # Check for ambiguous cases
            if len(varieties) > 3:
                warnings.append(f"Multiple varieties detected ({len(varieties)}): {', '.join(varieties)}")
                self.stats['warnings_generated'] += 1
            
            # Check for potential conflicts
            conflicting_varieties = self._check_variety_conflicts(varieties)
            if conflicting_varieties:
                warnings.append(f"Potential variety conflicts: {', '.join(conflicting_varieties)}")
                self.stats['warnings_generated'] += 1
            
            result = VarietyResult(
                varieties=varieties,
                confidence_scores=confidence_scores,
                warnings=warnings
            )
            
            self.stats['successful_extractions'] += 1
            self.stats['varieties_found'] += len(varieties)
            
            logger.debug(
                "Variety extraction completed",
                description_length=len(description),
                varieties_found=len(varieties),
                warnings_count=len(warnings)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to extract varieties from description",
                error=str(e),
                description_length=len(description) if description else 0
            )
            
            self.stats['failed_extractions'] += 1
            
            return VarietyResult(
                varieties=[],
                confidence_scores=[],
                warnings=[f"Variety extraction failed: {str(e)}"]
            )
    
    def extract_varieties_batch(self, descriptions: List[str]) -> List[VarietyResult]:
        """
        Extract varieties from multiple descriptions in batch.
        
        Args:
            descriptions: List of product descriptions
            
        Returns:
            List of VarietyResult objects
        """
        if not descriptions:
            logger.warning("Empty descriptions list provided for batch variety extraction")
            return []
        
        logger.info(
            "Starting batch variety extraction",
            batch_size=len(descriptions)
        )
        
        results = []
        for i, description in enumerate(descriptions):
            try:
                result = self.extract_varieties(description)
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to extract varieties in batch",
                    batch_index=i,
                    error=str(e)
                )
                results.append(VarietyResult(
                    varieties=[],
                    confidence_scores=[],
                    warnings=[f"Batch extraction failed: {str(e)}"]
                ))
        
        logger.info(
            "Completed batch variety extraction",
            batch_size=len(descriptions),
            successful_extractions=sum(1 for r in results if r.varieties),
            total_varieties_found=sum(len(r.varieties) for r in results)
        )
        
        return results
    
    def _check_variety_conflicts(self, varieties: List[str]) -> List[str]:
        """
        Check for potential variety conflicts.
        
        Args:
            varieties: List of extracted varieties
            
        Returns:
            List of conflicting variety pairs
        """
        conflicts = []
        
        # Define conflicting variety pairs
        conflict_pairs = [
            ('s795', 's9'),
            ('s8', 's9'),
            ('s5', 's5a'),
            ('s5', 's5b'),
            ('s5a', 's5b'),
            ('geisha', 'gesha'),
            ('monsoon_malabar', 'malabar')
        ]
        
        for variety1, variety2 in conflict_pairs:
            if variety1 in varieties and variety2 in varieties:
                conflicts.append(f"{variety1} vs {variety2}")
        
        return conflicts
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """
        Get variety extraction statistics.
        
        Returns:
            Dictionary with extraction statistics
        """
        stats = self.stats.copy()
        
        # Calculate success rate
        if stats['total_extractions'] > 0:
            stats['success_rate'] = stats['successful_extractions'] / stats['total_extractions']
            stats['failure_rate'] = stats['failed_extractions'] / stats['total_extractions']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # Calculate average varieties per extraction
        if stats['successful_extractions'] > 0:
            stats['avg_varieties_per_extraction'] = stats['varieties_found'] / stats['successful_extractions']
        else:
            stats['avg_varieties_per_extraction'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset extraction statistics."""
        self.stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'varieties_found': 0,
            'warnings_generated': 0
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on variety extraction service.
        
        Returns:
            Dictionary with health check results
        """
        return {
            'status': 'healthy',
            'variety_patterns_count': len(self.variety_patterns),
            'stats': self.get_extraction_stats(),
            'timestamp': logger.info("Variety extraction service health check completed")
        }
