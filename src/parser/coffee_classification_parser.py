"""
Coffee classification parser for determining if products are coffee or equipment.

This parser uses a multi-tier approach:
1. Code-based classification with confidence scoring
2. LLM fallback for uncertain cases
3. Equipment skip for very low confidence

Features:
- Sophisticated keyword-based classification
- Confidence scoring system
- LLM integration for edge cases
- Performance optimized for batch processing
- Integration with existing pipeline
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger(__name__)


class ClassificationResult(BaseModel):
    """Represents a coffee classification result with metadata."""
    
    is_coffee: bool = Field(..., description="True if product is coffee, False if equipment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    method: str = Field(..., description="Classification method used")
    reasoning: str = Field(..., description="Human-readable reasoning")
    warnings: List[str] = Field(default_factory=list, description="Classification warnings")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassificationResult':
        """Create ClassificationResult from dictionary."""
        return cls.model_validate(data)


class CoffeeClassificationParser:
    """
    Coffee classification parser using multi-tier approach.
    
    Classification Flow:
    1. Code-based classification (confidence score)
    2. If confidence >= 0.7 → Direct classification
    3. If confidence < 0.7 → Send to LLM for analysis
    4. If LLM confidence >= 0.6 → Use LLM result
    5. If LLM confidence < 0.6 → Skip product (equipment)
    """
    
    # POSITIVE COFFEE INDICATORS - Strong signals this IS coffee
    _COFFEE_INDICATORS = [
        # Core coffee terms
        "coffee", "bean", "beans", "blend", "blends", "estate", "origin", "single origin",
        "arabica", "robusta", "roast", "roasted", "light roast", "medium roast", "dark roast",
        
        # Processing/origin terms
        "washed", "natural", "honey", "pulp", "sun dried", "monsoon", "malabar",
        "single origin", "estate", "plantation", "farm",
        
        # Indian coffee regions/estates
        "karnataka", "kerala", "tamil nadu", "coorg", "chikmagalur", "araku",
        "krishnagiri", "attikan", "kalledevarapura", "basankhan", "sandalwood",
        "silver oak", "dhak", "vienna", "kerehaklu", "riverdale", "seethargundu",
        "monsoon malabar", "st. joseph", "hoysala", "thogarihunkal",
        
        # International coffee regions
        "kenya", "ethiopia", "colombia", "brazil", "guatemala", "costa rica",
        "jamaica", "hawaii", "sumatra", "java", "sulawesi", "papua new guinea",
        
        # Coffee varietals
        "selection", "bourbon", "typica", "caturra", "gesha", "sl-28", "kent",
        
        # Specialty terms
        "specialty", "direct trade", "freshly roasted", "peaberry", "micro lot",
        
        # Additional coffee terms
        "espresso", "cappuccino", "latte", "mocha", "americano", "pour-over",
        "drip", "filter", "ground", "whole", "single-origin",
        "organic", "fair-trade", "premium"
    ]
    
    # Coffee product types
    _COFFEE_TYPES = {
        "coffee", "beans", "ground coffee", "whole bean", "single estate coffee",
        "espresso beans", "filter coffee", "specialty coffee", "whole bean coffee"
    }
    
    # HARD EXCLUSIONS - These are NEVER coffee products, even if they mention coffee
    _HARD_EXCLUSIONS = [
        # Equipment (product names, not brewing method mentions)
        "espresso machine", "coffee maker", "coffee grinder", "grinder", "machine",
        "kettle", "scale", "tamper", "thermometer", "cleaning", "cleaner", "descaler",
        
        # Training/Events
        "workshop", "masterclass", "course", "training", "seminar", "tutorial",
        "lesson", "education", "certification", "bootcamp", "academy", "program",
        "event", "launch event", "tasting", "cupping session",
        
        # Subscriptions (as products)
        "subscription", "delivery service", "membership",
        
        # Gift items and non-coffee packs
        "gift card", "gift set", "gift box", "gift hamper", "gift", "hamper", "set", "box",
        "starter kit", "sampler pack", "combo pack", "trio pack", "explorer pack",
        "bundle", "kit", "pack", "combo", "trio", "explorer", "sampler",
        "pack of", "pack of 2", "pack of 4", "pack of 6", "pack of coffee",
        "5-in-1", "trio pack", "explorer pack", "sampler pack", "customised sampler",
        
        # Food items
        "cookie", "cookies", "almond", "almonds", "trail mix", "granola", "energy bar",
        "candy", "jam", "sauce", "condiment",
        
        # RTD beverages
        "cold coffee", "iced coffee", "ready to drink", "rtd",
        
        # Merchandise
        "t-shirt", "shirt", "hat", "tote", "backpack", "wallet", "keychain", 
        "coaster", "towel", "apron", "mask", "book", "magazine", "poster",
        "merchandise", "clothing", "apparel", "mug", "mugs"
    ]
    
    # CONTEXTUAL EXCLUSIONS - Only check specific equipment products, not mentions in descriptions
    _CONTEXTUAL_EXCLUSIONS = {
        "french press": ["french press 600ml", "bullet french press", "french press starter"],
        "aeropress": ["aeropress filter", "aeropress paper", "aeropress coffee filter"],  
        "v60": ["v60 filter", "v60 paper"],
        "chemex": ["chemex filter", "chemex paper"],
        "bags": ["drip bags", "cold brew bags", "brew bags", "filter bags"],
        "cups": ["coffee cup", "measuring cup", "tasting cup"],
        "mugs": ["coffee mug", "travel mug"],
        "papers": ["filter paper", "coffee filter paper", "filter papers", "coffee filter papers"]
    }
    
    # SOFT EXCLUSIONS - Only exclude if NO coffee indicators present
    _SOFT_EXCLUSIONS = [
        "equipment", "tool", "accessory", "dripper", "carafe", "basket", "tray",
        "brush", "mat", "cloth", "reusable", "spoon", "thermometer", "cup", "cups",
        "french press", "aeropress", "v60", "chemex", "bags", "mugs", "papers"
    ]
    
    # Brewing method mentions in coffee context (these are ACCEPTED)
    _BREWING_IN_COFFEE_CONTEXT = [
        "espresso blend", "pour over roast", "french press grind", "filter coffee",
        "cold brew blend", "espresso suitable", "moka pot suitable",
        "cold brew", "cold brewed", "french press", "aeropress", "pour over",
        "espresso", "drip", "filter", "moka pot", "chemex", "v60"
    ]
    
    def __init__(self, llm_service: Optional[Any] = None):
        """
        Initialize the coffee classification parser.
        
        Args:
            llm_service: Optional LLM service for fallback classification
        """
        self.llm_service = llm_service
        logger.info("CoffeeClassificationParser initialized")
    
    def _extract_text(self, *parts: Any) -> str:
        """Extract and normalize text from various data structures."""
        vals = []
        for p in parts:
            if isinstance(p, list):
                vals.extend([str(x) for x in p])
            elif isinstance(p, dict):
                vals.extend([str(x) for x in p.values()])
            elif p is not None:
                vals.append(str(p))
        return " ".join(vals).lower()
    
    def _has_coffee_indicator(self, name: str, tags: List[str]) -> bool:
        """Check if product has coffee indicators using word boundaries."""
        name_lower = name.lower()
        
        # Check name using word boundaries
        for indicator in self._COFFEE_INDICATORS:
            pattern = r'\b' + re.escape(indicator) + r'\b'
            if re.search(pattern, name_lower):
                return True
        
        # Check tags using word boundaries
        for tag in tags:
            tag_lower = tag.lower()
            for indicator in self._COFFEE_INDICATORS:
                pattern = r'\b' + re.escape(indicator) + r'\b'
                if re.search(pattern, tag_lower):
                    return True
        
        return False
    
    def _check_hard_exclusions(self, name: str, product_type: str) -> bool:
        """Check for hard exclusions using word boundaries."""
        name_lower = name.lower()
        product_type_lower = product_type.lower()
        
        # Check name
        for term in self._HARD_EXCLUSIONS:
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, name_lower):
                return True
        
        # Check product type
        for term in self._HARD_EXCLUSIONS:
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, product_type_lower):
                return True
        
        return False
    
    def _check_contextual_exclusions(self, name: str) -> bool:
        """Check contextual exclusions in name only."""
        name_lower = name.lower()
        
        for base_term, specific_terms in self._CONTEXTUAL_EXCLUSIONS.items():
            for specific_term in specific_terms:
                pattern = r'\b' + re.escape(specific_term) + r'\b'
                if re.search(pattern, name_lower):
                    return True
        
        return False
    
    def _check_soft_exclusions(self, name: str, tags: List[str]) -> bool:
        """Check soft exclusions (only if no coffee indicators present)."""
        name_lower = name.lower()
        
        # Check name
        for term in self._SOFT_EXCLUSIONS:
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, name_lower):
                return True
        
        # Check tags
        for tag in tags:
            tag_lower = tag.lower()
            for term in self._SOFT_EXCLUSIONS:
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, tag_lower):
                    return True
        
        return False
    
    def _has_brewing_in_coffee_context(self, name: str, tags: List[str]) -> bool:
        """Check for brewing method mentions in coffee context."""
        name_lower = name.lower()
        
        for context_term in self._BREWING_IN_COFFEE_CONTEXT:
            pattern = r'\b' + re.escape(context_term) + r'\b'
            if re.search(pattern, name_lower):
                return True
        
        for tag in tags:
            tag_lower = tag.lower()
            for context_term in self._BREWING_IN_COFFEE_CONTEXT:
                pattern = r'\b' + re.escape(context_term) + r'\b'
                if re.search(pattern, tag_lower):
                    return True
        
        return False
    
    def _calculate_confidence(self, name: str, tags: List[str], product_type: str) -> float:
        """Calculate confidence score for classification."""
        confidence = 0.0
        
        # Base confidence from coffee indicators
        if self._has_coffee_indicator(name, tags):
            confidence += 0.65
            
            # Additional boost for strong coffee indicators
            strong_indicators = ['arabica', 'robusta', 'beans', 'coffee', 'single origin', 'whole beans']
            name_lower = name.lower()
            tag_text = ' '.join(tags).lower()
            combined_text = f"{name_lower} {tag_text}"
            
            strong_count = 0
            for indicator in strong_indicators:
                if indicator in combined_text:
                    strong_count += 1
            
            # Boost confidence based on number of strong indicators
            if strong_count >= 3:
                confidence += 0.25  # Very strong coffee indicators
            elif strong_count >= 2:
                confidence += 0.15  # Strong coffee indicators
            elif strong_count >= 1:
                confidence += 0.05  # Some coffee indicators
        
        # Boost for brewing context
        if self._has_brewing_in_coffee_context(name, tags):
            confidence += 0.2
        
        # Penalty for soft exclusions (only if no coffee indicators)
        if not self._has_coffee_indicator(name, tags) and self._check_soft_exclusions(name, tags):
            confidence -= 0.4
        
        # Ensure confidence is between 0.0 and 1.0
        return max(0.0, min(1.0, confidence))
    
    async def _classify_with_llm(self, product_data: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        Classify product using LLM service for uncertain cases.
        
        Args:
            product_data: Product data dictionary
            
        Returns:
            Tuple of (is_coffee, confidence, reasoning)
        """
        if not self.llm_service:
            logger.warning("LLM service not available, defaulting to equipment")
            return False, 0.0, "LLM service not available"
        
        try:
            # Prepare context for LLM
            context = {
                "name": product_data.get("name", ""),
                "product_type": product_data.get("product_type", ""),
                "tags": product_data.get("tags", []),
                "description": product_data.get("description", "")
            }
            
            # Use LLM service for classification (async)
            result = await self.llm_service.classify_coffee_product(context)
            
            return (
                result.get("is_coffee", False),
                result.get("confidence", 0.0),
                result.get("reasoning", "LLM classification")
            )
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return False, 0.0, f"LLM classification failed: {str(e)}"
    
    async def classify_product(self, product_data: Dict[str, Any], platform: str) -> ClassificationResult:
        """
        Classify if a product is coffee-related using multi-tier approach.
        
        Args:
            product_data: Product data dictionary
            platform: "shopify" or "woo" (case insensitive)
        
        Returns:
            ClassificationResult with classification and metadata
        """
        platform = platform.lower()
        warnings = []
        
        # Extract data based on platform
        if platform == "shopify":
            name = self._extract_text(product_data.get("title"), product_data.get("product_type"))
            product_type = (product_data.get("product_type") or "").lower()
            tags = [str(tag).lower() for tag in (product_data.get("tags") or [])]
        else:
            # WooCommerce Store API fields: name, categories, tags, type, short_description
            cat_names = [c.get("name") for c in (product_data.get("categories") or [])]
            tag_names = [t.get("name") for t in (product_data.get("tags") or [])]
            short_desc = product_data.get("short_description", "")
            name = self._extract_text(
                product_data.get("name"), 
                cat_names, 
                short_desc
            )
            product_type = (product_data.get("type") or "").lower()
            tags = [str(tag).lower() for tag in tag_names if tag]
        
        # Check for hard exclusions FIRST - these always take precedence
        if self._check_hard_exclusions(name, product_type):
            return ClassificationResult(
                is_coffee=False,
                confidence=1.0,
                method="hard_exclusion",
                reasoning="Product matches hard exclusion patterns (equipment, gifts, etc.)",
                warnings=warnings
            )
        
        # Check contextual exclusions
        if self._check_contextual_exclusions(name):
            return ClassificationResult(
                is_coffee=False,
                confidence=1.0,
                method="contextual_exclusion",
                reasoning="Product matches contextual exclusion patterns (specific equipment)",
                warnings=warnings
            )
        
        # Check for positive coffee indicators first
        has_coffee_indicator = self._has_coffee_indicator(name, tags)
        
        # Definitely coffee if product type says so (after exclusions)
        if product_type in self._COFFEE_TYPES:
            return ClassificationResult(
                is_coffee=True,
                confidence=1.0,
                method="product_type",
                reasoning=f"Product type '{product_type}' indicates coffee",
                warnings=warnings
            )
        
        # Calculate confidence for code-based classification
        confidence = self._calculate_confidence(name, tags, product_type)
        
        # High confidence - use code-based result
        if confidence >= 0.7:
            is_coffee = self._has_coffee_indicator(name, tags) or self._has_brewing_in_coffee_context(name, tags)
            return ClassificationResult(
                is_coffee=is_coffee,
                confidence=confidence,
                method="code_based",
                reasoning=f"High confidence code-based classification (confidence: {confidence:.2f})",
                warnings=warnings
            )
        
        # Medium confidence - use LLM fallback
        if confidence >= 0.3:
            logger.info(f"Using LLM fallback for medium confidence product: {name[:50]}...")
            is_coffee, llm_confidence, llm_reasoning = await self._classify_with_llm(product_data)
            
            # Use LLM result if confidence is sufficient
            if llm_confidence >= 0.5:
                return ClassificationResult(
                    is_coffee=is_coffee,
                    confidence=llm_confidence,
                    method="llm_fallback",
                    reasoning=f"LLM classification: {llm_reasoning}",
                    warnings=warnings
                )
        
        # Low confidence - default to equipment (skip)
        logger.info(f"Low confidence product classified as equipment: {name[:50]}...")
        return ClassificationResult(
            is_coffee=False,
            confidence=confidence,
            method="low_confidence_skip",
            reasoning=f"Low confidence classification, defaulting to equipment (confidence: {confidence:.2f})",
            warnings=warnings + ["Product classified as equipment due to low confidence"]
        )
    
    async def batch_classify_products(self, products: List[Dict[str, Any]], platform: str) -> List[ClassificationResult]:
        """
        Classify multiple products in batch for performance optimization.
        
        Args:
            products: List of product data dictionaries
            platform: "shopify" or "woo" (case insensitive)
            
        Returns:
            List of ClassificationResult objects
        """
        results = []
        for product in products:
            result = await self.classify_product(product, platform)
            results.append(result)
        
        logger.info(f"Batch classified {len(products)} products")
        return results
