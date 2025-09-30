"""Abstract interface for LLM service operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from datetime import datetime
from pydantic import BaseModel


class LLMResult(BaseModel):
    """Standardized LLM API result model"""
    field: str
    value: Any
    confidence: float
    provider: str = "deepseek"
    model: str  # deepseek-chat or deepseek-reasoner
    usage: Dict[str, int]
    created_at: datetime


class LLMServiceInterface(ABC):
    """Abstract interface for LLM operations - provides clear contracts for C.8"""
    
    @abstractmethod
    async def enrich_field(self, artifact: Dict, field: str, prompt: str) -> LLMResult:
        """Enrich a single field using LLM API
        
        Args:
            artifact: The artifact to enrich
            field: The field to enrich
            prompt: The prompt to use for enrichment
            
        Returns:
            LLMResult with enriched value and metadata
        """
        pass
    
    @abstractmethod
    async def batch_enrich(self, artifacts: List[Dict], fields: List[str]) -> List[LLMResult]:
        """Enrich multiple fields across multiple artifacts using LLM API
        
        Args:
            artifacts: List of artifacts to enrich
            fields: List of fields to enrich
            
        Returns:
            List of LLMResults for each enrichment
        """
        pass
    
    @abstractmethod
    def get_confidence_threshold(self, field: str) -> float:
        """Get confidence threshold for specific field
        
        Args:
            field: The field name
            
        Returns:
            Confidence threshold (0.0-1.0)
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if LLM service is available
        
        Returns:
            True if service is healthy and available
        """
        pass
    
    @abstractmethod
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status
        
        Returns:
            Dictionary with health metrics and status
        """
        pass
