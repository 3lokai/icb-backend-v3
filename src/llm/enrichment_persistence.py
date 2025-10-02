"""Enrichment persistence service for storing LLM results."""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

from src.llm.llm_interface import LLMResult
from src.llm.confidence_evaluator import ConfidenceEvaluation

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentData:
    """Enrichment data for persistence."""
    
    artifact_id: str
    roaster_id: Optional[str]
    field: str
    llm_result: LLMResult
    confidence_evaluation: ConfidenceEvaluation
    processing_status: str
    created_at: datetime
    updated_at: datetime
    enrichment_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'enrichment_id': self.enrichment_id,
            'artifact_id': self.artifact_id,
            'roaster_id': self.roaster_id,
            'field': self.field,
            'llm_result': self.llm_result.to_dict() if hasattr(self.llm_result, 'to_dict') else {
                'field': self.llm_result.field,
                'value': self.llm_result.value,
                'confidence': self.llm_result.confidence,
                'provider': self.llm_result.provider,
                'model': self.llm_result.model,
                'usage': self.llm_result.usage,
                'created_at': self.llm_result.created_at.isoformat()
            },
            'confidence_evaluation': self.confidence_evaluation.to_dict(),
            'processing_status': self.processing_status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class EnrichmentPersistence:
    """Service for persisting LLM enrichment results regardless of confidence level."""
    
    def __init__(self, config: Dict[str, Any] = None, rpc_client=None):
        """Initialize enrichment persistence with configuration."""
        self.config = config or {}
        self.rpc_client = rpc_client
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._enrichment_storage = {}  # In-memory storage for now
    
    def persist_enrichment(self, artifact: Dict, llm_result: LLMResult, evaluation: ConfidenceEvaluation) -> str:
        """Persist LLM enrichment regardless of confidence level."""
        try:
            # Create enrichment data
            enrichment_data = EnrichmentData(
                artifact_id=artifact.get('id', 'unknown'),
                roaster_id=artifact.get('roaster_id'),
                field=llm_result.field,
                llm_result=llm_result,
                confidence_evaluation=evaluation,
                processing_status=evaluation.status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Generate enrichment ID
            enrichment_id = self._generate_enrichment_id(enrichment_data)
            enrichment_data.enrichment_id = enrichment_id
            
            # Store enrichment data
            self._store_enrichment(enrichment_data)
            
            # Apply if confidence is above threshold
            if evaluation.action == 'auto_apply':
                self._apply_enrichment_to_artifact(artifact, llm_result)
            
            # Log persistence
            self.logger.info(
                f"Enrichment persisted: {enrichment_id}, "
                f"artifact={enrichment_data.artifact_id}, "
                f"field={enrichment_data.field}, "
                f"confidence={evaluation.final_confidence:.3f}, "
                f"status={evaluation.status}"
            )
            
            return enrichment_id
            
        except Exception as e:
            self.logger.error(f"Enrichment persistence failed: {str(e)}")
            raise EnrichmentPersistenceError(f"Enrichment persistence failed: {str(e)}")
    
    def batch_persist_enrichments(self, enrichments: List[Dict[str, Any]]) -> List[str]:
        """Persist multiple enrichments in batch."""
        enrichment_ids = []
        
        for enrichment in enrichments:
            try:
                enrichment_id = self.persist_enrichment(
                    enrichment['artifact'],
                    enrichment['llm_result'],
                    enrichment['evaluation']
                )
                enrichment_ids.append(enrichment_id)
            except Exception as e:
                self.logger.error(f"Batch enrichment persistence failed for item: {str(e)}")
                # Continue with other enrichments
        
        return enrichment_ids
    
    def get_enrichment(self, enrichment_id: str) -> Optional[EnrichmentData]:
        """Get enrichment data by ID."""
        return self._enrichment_storage.get(enrichment_id)
    
    def get_enrichments_by_artifact(self, artifact_id: str) -> List[EnrichmentData]:
        """Get all enrichments for a specific artifact."""
        enrichments = []
        for enrichment in self._enrichment_storage.values():
            if enrichment.artifact_id == artifact_id:
                enrichments.append(enrichment)
        return enrichments
    
    def get_enrichments_by_status(self, status: str) -> List[EnrichmentData]:
        """Get all enrichments with specific status."""
        enrichments = []
        for enrichment in self._enrichment_storage.values():
            if enrichment.processing_status == status:
                enrichments.append(enrichment)
        return enrichments
    
    def update_enrichment_status(self, enrichment_id: str, status: str, reviewer_id: str = None) -> bool:
        """Update enrichment status after review."""
        try:
            enrichment = self._enrichment_storage.get(enrichment_id)
            if not enrichment:
                return False
            
            # Update status
            enrichment.processing_status = status
            enrichment.updated_at = datetime.now(timezone.utc)
            
            # Store updated enrichment
            self._enrichment_storage[enrichment_id] = enrichment
            
            # Log status update
            self.logger.info(
                f"Enrichment status updated: {enrichment_id}, "
                f"status={status}, "
                f"reviewer={reviewer_id}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Enrichment status update failed: {str(e)}")
            return False
    
    def _generate_enrichment_id(self, enrichment_data: EnrichmentData) -> str:
        """Generate unique enrichment ID."""
        timestamp = int(time.time())
        return f"enrich_{enrichment_data.artifact_id}_{enrichment_data.field}_{timestamp}"
    
    def _store_enrichment(self, enrichment_data: EnrichmentData):
        """Store enrichment data to database."""
        try:
            if not self.rpc_client:
                # Fallback to in-memory storage if no RPC client
                self._enrichment_storage[enrichment_data.enrichment_id] = enrichment_data
                self.logger.warning("No RPC client available, using in-memory storage")
                return
            
            # Store to database using direct table access (simpler than RPC for this case)
            db_record = {
                "enrichment_id": enrichment_data.enrichment_id,
                "artifact_id": enrichment_data.artifact_id,
                "field": enrichment_data.field,
                "llm_result": enrichment_data.llm_result.model_dump() if hasattr(enrichment_data.llm_result, 'model_dump') else enrichment_data.llm_result,
                "confidence_score": enrichment_data.confidence_score,
                "applied": enrichment_data.evaluation_action == 'auto_apply'
            }
            
            # Use direct table upsert (simpler than RPC for enrichments)
            result = self.rpc_client.supabase_client.table("enrichments").upsert(db_record).execute()
            
            if result.data:
                self.logger.debug(f"Enrichment stored successfully: {enrichment_data.enrichment_id}")
            else:
                self.logger.warning(f"Failed to store enrichment: {enrichment_data.enrichment_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to store enrichment {enrichment_data.enrichment_id}: {str(e)}")
            # Fallback to in-memory storage
            self._enrichment_storage[enrichment_data.enrichment_id] = enrichment_data
    
    def _apply_enrichment_to_artifact(self, artifact: Dict, llm_result: LLMResult):
        """Apply high-confidence enrichment to artifact."""
        field = llm_result.field
        value = llm_result.value
        
        # Apply enrichment based on field type
        if field in ['roast_level', 'process_method', 'bean_species']:
            artifact[field] = value
        elif field in ['varieties', 'geographic_data', 'sensory_parameters']:
            artifact[field] = value
        elif field in ['tags', 'notes', 'cleaned_text']:
            artifact[field] = value
        
        # Update processing status
        artifact['processing_status'] = 'enriched'
        artifact['enrichment_applied'] = True
        artifact['enrichment_timestamp'] = datetime.now(timezone.utc)
    
    def get_enrichment_stats(self, enrichments: List[EnrichmentData]) -> Dict[str, Any]:
        """Get statistics from enrichment data."""
        if not enrichments:
            return {}
        
        status_counts = {}
        field_counts = {}
        confidence_scores = []
        
        for enrichment in enrichments:
            # Count by status
            status = enrichment.processing_status
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by field
            field = enrichment.field
            field_counts[field] = field_counts.get(field, 0) + 1
            
            # Collect confidence scores
            confidence_scores.append(enrichment.confidence_evaluation.final_confidence)
        
        return {
            'total_enrichments': len(enrichments),
            'status_distribution': status_counts,
            'field_distribution': field_counts,
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
            'min_confidence': min(confidence_scores) if confidence_scores else 0.0,
            'max_confidence': max(confidence_scores) if confidence_scores else 0.0
        }


class EnrichmentPersistenceError(Exception):
    """Exception raised for enrichment persistence errors."""
    pass
