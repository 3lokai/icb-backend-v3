"""
Indian Coffee Geographic Parser Service

Extracts Indian coffee geographic data (regions, estates, states, altitude) from product descriptions.
Supports major Indian coffee regions, estates, and geographic information.
"""

import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from structlog import get_logger

logger = get_logger(__name__)


@dataclass
class GeographicResult:
    """Result of geographic parsing from product description."""
    region: str
    country: str
    state: str
    estate: str
    altitude: Optional[int]
    confidence: float
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'region': self.region,
            'country': self.country,
            'state': self.state,
            'estate': self.estate,
            'altitude': self.altitude,
            'confidence': self.confidence,
            'warnings': self.warnings
        }


class GeographicParserService:
    """
    Service for parsing Indian coffee geographic data from product descriptions.
    
    Features:
    - Indian region detection (Chikmagalur, Coorg, Nilgiris, etc.)
    - Estate recognition from seed data patterns
    - State and country extraction
    - Altitude extraction with unit conversion
    - Confidence scoring for geographic accuracy
    - Batch processing optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize geographic parser service.
        
        Args:
            config: Configuration dictionary for geographic parsing
        """
        self.config = config or {}
        
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
        
        # Altitude patterns
        self.altitude_patterns = [
            r'(\d+)\s*(?:m|meters?|ft|feet?)\s*(?:above\s*sea\s*level|asl)',
            r'(\d+)\s*(?:m|meters?|ft|feet?)\s*altitude',
            r'altitude[:\s]*(\d+)\s*(?:m|meters?|ft|feet?)'
        ]
        
        # Statistics tracking
        self.stats = {
            'total_parses': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'regions_found': 0,
            'estates_found': 0,
            'altitudes_found': 0,
            'warnings_generated': 0
        }
    
    def parse_geographic(self, description: str) -> GeographicResult:
        """
        Parse Indian coffee geographic data from product description.
        
        Args:
            description: Product description text
            
        Returns:
            GeographicResult with extracted geographic data
        """
        if not description or not isinstance(description, str):
            logger.warning("Invalid description provided for geographic parsing")
            return GeographicResult(
                region='unknown',
                country='unknown',
                state='unknown',
                estate='unknown',
                altitude=None,
                confidence=0.0,
                warnings=["Invalid or empty description provided"]
            )
        
        self.stats['total_parses'] += 1
        
        try:
            region = self._extract_region(description)
            country = self._extract_country(description)
            state = self._extract_state(description)
            estate = self._extract_estate(description)
            altitude = self._extract_altitude(description)
            
            # Calculate confidence based on extracted data
            confidence = self._calculate_confidence(region, country, state, estate, altitude)
            
            # Generate warnings for ambiguous cases
            warnings = self._generate_warnings(region, country, state, estate, altitude)
            
            result = GeographicResult(
                region=region,
                country=country,
                state=state,
                estate=estate,
                altitude=altitude,
                confidence=confidence,
                warnings=warnings
            )
            
            self.stats['successful_parses'] += 1
            if region != 'unknown':
                self.stats['regions_found'] += 1
            if estate != 'unknown':
                self.stats['estates_found'] += 1
            if altitude is not None:
                self.stats['altitudes_found'] += 1
            self.stats['warnings_generated'] += len(warnings)
            
            logger.debug(
                "Geographic parsing completed",
                description_length=len(description),
                region=region,
                country=country,
                state=state,
                estate=estate,
                altitude=altitude,
                confidence=confidence
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to parse geographic data from description",
                error=str(e),
                description_length=len(description) if description else 0
            )
            
            self.stats['failed_parses'] += 1
            
            return GeographicResult(
                region='unknown',
                country='unknown',
                state='unknown',
                estate='unknown',
                altitude=None,
                confidence=0.0,
                warnings=[f"Geographic parsing failed: {str(e)}"]
            )
    
    def parse_geographic_batch(self, descriptions: List[str]) -> List[GeographicResult]:
        """
        Parse geographic data from multiple descriptions in batch.
        
        Args:
            descriptions: List of product descriptions
            
        Returns:
            List of GeographicResult objects
        """
        if not descriptions:
            logger.warning("Empty descriptions list provided for batch geographic parsing")
            return []
        
        logger.info(
            "Starting batch geographic parsing",
            batch_size=len(descriptions)
        )
        
        results = []
        for i, description in enumerate(descriptions):
            try:
                result = self.parse_geographic(description)
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to parse geographic data in batch",
                    batch_index=i,
                    error=str(e)
                )
                results.append(GeographicResult(
                    region='unknown',
                    country='unknown',
                    state='unknown',
                    estate='unknown',
                    altitude=None,
                    confidence=0.0,
                    warnings=[f"Batch parsing failed: {str(e)}"]
                ))
        
        logger.info(
            "Completed batch geographic parsing",
            batch_size=len(descriptions),
            successful_parses=sum(1 for r in results if r.region != 'unknown'),
            total_regions_found=sum(1 for r in results if r.region != 'unknown'),
            total_estates_found=sum(1 for r in results if r.estate != 'unknown'),
            total_altitudes_found=sum(1 for r in results if r.altitude is not None)
        )
        
        return results
    
    def _extract_region(self, description: str) -> str:
        """Extract Indian coffee region from description."""
        for region, patterns in self.region_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return region
        return 'unknown'
    
    def _extract_country(self, description: str) -> str:
        """Extract country from description (India-focused)."""
        for country, patterns in self.country_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return country
        return 'unknown'
    
    def _extract_state(self, description: str) -> str:
        """Extract Indian state from description."""
        for state, patterns in self.state_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return state
        return 'unknown'
    
    def _extract_estate(self, description: str) -> str:
        """Extract Indian coffee estate from description."""
        for estate, patterns in self.estate_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return estate
        return 'unknown'
    
    def _extract_altitude(self, description: str) -> Optional[int]:
        """Extract altitude from description."""
        for pattern in self.altitude_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                altitude = int(match.group(1))
                # Convert feet to meters if needed
                if 'ft' in match.group(0).lower() or 'feet' in match.group(0).lower():
                    altitude = int(altitude * 0.3048)  # Convert feet to meters
                return altitude
        return None
    
    def _calculate_confidence(self, region: str, country: str, state: str, estate: str, altitude: Optional[int]) -> float:
        """Calculate confidence score for geographic extraction."""
        confidence = 0.0
        
        # Base confidence for each extracted field
        if region != 'unknown':
            confidence += 0.3
        if country != 'unknown':
            confidence += 0.2
        if state != 'unknown':
            confidence += 0.2
        if estate != 'unknown':
            confidence += 0.2
        if altitude is not None:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_warnings(self, region: str, country: str, state: str, estate: str, altitude: Optional[int]) -> List[str]:
        """Generate warnings for ambiguous geographic data."""
        warnings = []
        
        # Check for region-state mismatches
        if region != 'unknown' and state != 'unknown':
            region_state_mapping = {
                'chikmagalur': 'karnataka',
                'coorg': 'karnataka',
                'nilgiris': 'tamil_nadu',
                'yercaud': 'tamil_nadu',
                'wayanad': 'kerala',
                'araku_valley': 'andhra_pradesh',
                'biligiri_ranga': 'karnataka',
                'malnad': 'karnataka',
                'pulneys': 'tamil_nadu',
                'anamalais': 'tamil_nadu',
                'kodaikanal': 'tamil_nadu',
                'travancore': 'kerala',
                'coimbatore': 'tamil_nadu',
                'salem': 'tamil_nadu',
                'theni': 'tamil_nadu',
                'idukki': 'kerala',
                'manjarabad': 'karnataka',
                'sakleshpur': 'karnataka'
            }
            
            expected_state = region_state_mapping.get(region)
            if expected_state and expected_state != state:
                warnings.append(f"Region-state mismatch: {region} typically in {expected_state}, found {state}")
        
        # Check for unrealistic altitude values
        if altitude is not None:
            if altitude < 0:
                warnings.append(f"Negative altitude detected: {altitude}m")
            elif altitude > 3000:
                warnings.append(f"Very high altitude detected: {altitude}m (may be unrealistic)")
            elif altitude < 200:
                warnings.append(f"Very low altitude detected: {altitude}m (may be unrealistic for coffee)")
        
        # Check for missing context
        if region == 'unknown' and country == 'unknown' and state == 'unknown':
            warnings.append("No geographic information detected")
        
        return warnings
    
    def get_parsing_stats(self) -> Dict[str, Any]:
        """
        Get geographic parsing statistics.
        
        Returns:
            Dictionary with parsing statistics
        """
        stats = self.stats.copy()
        
        # Calculate success rate
        if stats['total_parses'] > 0:
            stats['success_rate'] = stats['successful_parses'] / stats['total_parses']
            stats['failure_rate'] = stats['failed_parses'] / stats['total_parses']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # Calculate extraction rates
        if stats['successful_parses'] > 0:
            stats['region_extraction_rate'] = stats['regions_found'] / stats['successful_parses']
            stats['estate_extraction_rate'] = stats['estates_found'] / stats['successful_parses']
            stats['altitude_extraction_rate'] = stats['altitudes_found'] / stats['successful_parses']
        else:
            stats['region_extraction_rate'] = 0.0
            stats['estate_extraction_rate'] = 0.0
            stats['altitude_extraction_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset parsing statistics."""
        self.stats = {
            'total_parses': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'regions_found': 0,
            'estates_found': 0,
            'altitudes_found': 0,
            'warnings_generated': 0
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on geographic parser service.
        
        Returns:
            Dictionary with health check results
        """
        return {
            'status': 'healthy',
            'region_patterns_count': len(self.region_patterns),
            'estate_patterns_count': len(self.estate_patterns),
            'state_patterns_count': len(self.state_patterns),
            'country_patterns_count': len(self.country_patterns),
            'altitude_patterns_count': len(self.altitude_patterns),
            'stats': self.get_parsing_stats(),
            'timestamp': logger.info("Geographic parser service health check completed")
        }
