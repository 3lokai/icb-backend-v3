"""DeepSeek API wrapper service with rate limiting and caching."""

import time
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import structlog

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from src.config.deepseek_config import DeepSeekConfig
from src.llm.llm_interface import LLMServiceInterface, LLMResult
from src.llm.cache_service import CacheService
from src.llm.rate_limiter import RateLimiter
from src.llm.llm_metrics import LLMServiceMetrics

logger = structlog.get_logger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service errors"""
    pass


class RateLimitExceededError(LLMServiceError):
    """Raised when rate limit is exceeded"""
    pass


class DeepSeekWrapperService(LLMServiceInterface):
    """DeepSeek API wrapper with OpenAI-compatible interface, caching, rate limiting, and G.1 metrics integration"""
    
    def __init__(self, config: DeepSeekConfig, cache_service: CacheService, rate_limiter: RateLimiter, metrics: Optional[LLMServiceMetrics] = None):
        self.config = config
        self.provider = self._initialize_deepseek_client(config)
        self.cache_service = cache_service
        self.rate_limiter = rate_limiter
        self.metrics = metrics or LLMServiceMetrics()
        self._health_status = {
            'available': True,
            'last_success': None,
            'last_error': None,
            'consecutive_failures': 0
        }
    
    def _initialize_deepseek_client(self, config: DeepSeekConfig) -> OpenAI:
        """Initialize DeepSeek API client with OpenAI-compatible interface"""
        return OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )
    
    async def enrich_field(self, artifact: Dict, field: str, prompt: str) -> LLMResult:
        """Enrich a single field using DeepSeek API with caching and rate limiting
        
        Args:
            artifact: The artifact to enrich
            field: The field to enrich
            prompt: The prompt to use for enrichment
            
        Returns:
            LLMResult with enriched value and metadata
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
            LLMServiceError: For other service errors
        """
        start_time = time.time()
        cache_hit = False
        success = False
        tokens_used = None
        confidence = None
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(artifact, field)
            
            # Check cache first
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                cache_hit = True
                success = True
                confidence = cached_result.confidence
                logger.info("cache_hit", field=field, cache_key=cache_key)
                return cached_result
            
            # Check rate limits
            roaster_id = artifact.get('roaster_id', 'unknown')
            if not self.rate_limiter.can_make_request(roaster_id):
                logger.warning("rate_limit_exceeded", roaster_id=roaster_id, field=field)
                # Record rate limit hit
                self.metrics.record_rate_limit_hit(roaster_id)
                raise RateLimitExceededError(f"Rate limit exceeded for roaster {roaster_id}")
            
            # Make DeepSeek API call with retry logic
            result = await self._call_deepseek_with_retry(artifact, field, prompt)
            success = True
            tokens_used = result.usage
            confidence = result.confidence
            
            # Cache successful result
            await self.cache_service.set(cache_key, result, ttl=self.config.timeout)
            
            return result
        
        finally:
            # Record metrics regardless of success/failure
            duration = time.time() - start_time
            self.metrics.record_llm_call(
                duration=duration,
                field=field,
                model=self.config.model,
                success=success,
                cache_hit=cache_hit,
                tokens_used=tokens_used,
                confidence=confidence
            )
            
            # Update service health
            self.metrics.record_service_health(
                is_healthy=self._health_status['available'],
                consecutive_failures=self._health_status['consecutive_failures']
            )
    
    async def batch_enrich(self, artifacts: List[Dict], fields: List[str]) -> List[LLMResult]:
        """Enrich multiple fields across multiple artifacts using DeepSeek API
        
        Args:
            artifacts: List of artifacts to enrich
            fields: List of fields to enrich
            
        Returns:
            List of LLMResults for each enrichment
        """
        results = []
        for artifact in artifacts:
            for field in fields:
                try:
                    # Generate prompt for this field (would be customized per field)
                    prompt = f"Extract {field} from this coffee data"
                    result = await self.enrich_field(artifact, field, prompt)
                    results.append(result)
                except Exception as e:
                    logger.error("batch_enrich_failed", field=field, error=str(e))
                    # Continue processing other items even if one fails
                    continue
        
        return results
    
    async def _call_deepseek_with_retry(self, artifact: Dict, field: str, prompt: str) -> LLMResult:
        """Call DeepSeek API with retry logic for transient failures"""
        last_error = None
        
        for attempt in range(self.config.retry_attempts):
            try:
                start_time = time.time()
                
                # Make synchronous OpenAI call (OpenAI library handles async internally)
                response = await asyncio.to_thread(
                    self.provider.chat.completions.create,
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                
                duration = time.time() - start_time
                
                # Parse response
                content = response.choices[0].message.content
                usage = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
                
                # Update health status
                self._health_status['available'] = True
                self._health_status['last_success'] = datetime.now()
                self._health_status['consecutive_failures'] = 0
                
                logger.info(
                    "deepseek_call_success",
                    field=field,
                    duration=duration,
                    tokens=usage['total_tokens'],
                    attempt=attempt + 1
                )
                
                # Return standardized result
                return LLMResult(
                    field=field,
                    value=content,
                    confidence=0.8,  # Default confidence, would be refined based on response
                    provider="deepseek",
                    model=self.config.model,
                    usage=usage,
                    created_at=datetime.now()
                )
                
            except (APITimeoutError, APIError) as e:
                last_error = e
                self._health_status['consecutive_failures'] += 1
                self._health_status['last_error'] = str(e)
                
                logger.warning(
                    "deepseek_call_failed",
                    attempt=attempt + 1,
                    max_attempts=self.config.retry_attempts,
                    error=str(e),
                    field=field
                )
                
                # Wait before retry with exponential backoff
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    
            except Exception as e:
                # Non-retryable error
                self._health_status['consecutive_failures'] += 1
                self._health_status['available'] = False
                self._health_status['last_error'] = str(e)
                logger.error("deepseek_call_error", error=str(e), field=field)
                raise LLMServiceError(f"DeepSeek API call failed: {str(e)}")
        
        # All retries exhausted
        self._health_status['available'] = self._health_status['consecutive_failures'] < 5
        raise LLMServiceError(f"DeepSeek API call failed after {self.config.retry_attempts} attempts: {last_error}")
    
    def _generate_cache_key(self, artifact: Dict, field: str) -> str:
        """Generate cache key using raw_payload_hash and field"""
        raw_hash = artifact.get('raw_payload_hash', '')
        if not raw_hash:
            # Fallback: generate hash from artifact content
            import hashlib
            import json
            content = json.dumps(artifact, sort_keys=True)
            raw_hash = hashlib.sha256(content.encode()).hexdigest()
        
        return f"llm:{raw_hash}:{field}"
    
    def get_confidence_threshold(self, field: str) -> float:
        """Get confidence threshold for specific field
        
        Default threshold is 0.70 as per Epic D requirements
        """
        # Could be customized per field in future
        return 0.70
    
    def is_available(self) -> bool:
        """Check if DeepSeek service is available
        
        Returns False if there have been 5+ consecutive failures
        """
        return self._health_status['available']
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status
        
        Returns:
            Dictionary with health metrics and status
        """
        return {
            'provider': 'deepseek',
            'model': self.config.model,
            'available': self._health_status['available'],
            'last_success': self._health_status['last_success'],
            'last_error': self._health_status['last_error'],
            'consecutive_failures': self._health_status['consecutive_failures'],
            'rate_limit_config': self.config.rate_limits
        }
    
    async def classify_coffee_product(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Classify if a product is coffee-related using LLM"""
        prompt = self._create_coffee_classification_prompt(context)
        
        try:
            # Use the existing enrich_field method with a special field name
            result = await self.enrich_field(
                artifact=context,
                field="coffee_classification", 
                prompt=prompt
            )
            
            # Parse the LLM response to extract classification
            return self._parse_coffee_classification_result(result)
            
        except Exception as e:
            logger.error(f"LLM coffee classification failed: {e}")
            return {
                "is_coffee": False,
                "confidence": 0.0,
                "reasoning": f"LLM classification failed: {str(e)}"
            }
    
    def _create_coffee_classification_prompt(self, context: Dict[str, Any]) -> str:
        """Create a prompt for coffee classification"""
        name = context.get("name", "")
        product_type = context.get("product_type", "")
        tags = context.get("tags", [])
        description = context.get("description", "")
        
        prompt = f"""
You are a coffee product classification expert. Analyze the following product and determine if it's a coffee product or equipment/accessory.

Product Name: {name}
Product Type: {product_type}
Tags: {', '.join(tags) if tags else 'None'}
Description: {description}

Classification Rules:
- Coffee products: Coffee beans, ground coffee, whole beans, single origin, blends, espresso beans, filter coffee, specialty coffee
- Equipment/Accessories: Coffee makers, grinders, filters, cups, mugs, cleaning supplies, training materials, gift sets

Respond with JSON format:
{{
    "is_coffee": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of classification decision"
}}
"""
        return prompt
    
    def _parse_coffee_classification_result(self, llm_result: LLMResult) -> Dict[str, Any]:
        """Parse LLM result to extract coffee classification"""
        try:
            import json
            # Extract the value from LLM result
            response_text = str(llm_result.value)
            
            # Try to parse as JSON
            if response_text.strip().startswith('{'):
                result = json.loads(response_text)
                return {
                    "is_coffee": result.get("is_coffee", False),
                    "confidence": float(result.get("confidence", 0.0)),
                    "reasoning": result.get("reasoning", "LLM classification")
                }
            else:
                # Fallback parsing if not JSON
                return {
                    "is_coffee": "true" in response_text.lower() or "coffee" in response_text.lower(),
                    "confidence": 0.7,  # Default confidence for LLM results
                    "reasoning": response_text
                }
                
        except Exception as e:
            logger.error(f"Failed to parse LLM coffee classification result: {e}")
            return {
                "is_coffee": False,
                "confidence": 0.0,
                "reasoning": f"Failed to parse LLM result: {str(e)}"
            }