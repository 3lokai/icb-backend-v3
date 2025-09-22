"""
Raw Artifact Persistence Service

Handles storage of raw artifact JSON, hashes, and audit fields in the database.
Integrates with A.4 RPC upsert flow for atomic operations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .models import ArtifactModel
from .database_integration import DatabaseIntegration
from .rpc_client import RPCClient

logger = logging.getLogger(__name__)


@dataclass
class RawArtifactData:
    """Container for raw artifact data to be persisted."""
    complete_artifact_json: Dict[str, Any]
    content_hash: str
    raw_payload_hash: str
    artifact_id: str
    created_at: str
    collected_by: str
    collector_signals: Dict[str, Any]
    first_seen_at: str


class RawArtifactPersistence:
    """
    Service for persisting raw artifacts with complete audit trails.
    
    Extracts and stores:
    - Complete raw artifact JSON
    - Content and raw payload hashes
    - Audit fields (artifact_id, created_at, collected_by)
    - Collector signals for debugging
    - First seen timestamp
    """
    
    def __init__(self, db_integration: DatabaseIntegration, rpc_client: RPCClient):
        self.db_integration = db_integration
        self.rpc_client = rpc_client
    
    def extract_raw_artifact_data(self, artifact: ArtifactModel) -> RawArtifactData:
        """
        Extract all required data from canonical artifact for persistence.
        
        Args:
            artifact: Validated canonical artifact
            
        Returns:
            RawArtifactData with all persistence fields
            
        Raises:
            ValueError: If required fields are missing
        """
        try:
            # Extract hashes from normalization section
            content_hash = artifact.normalization.content_hash
            raw_payload_hash = artifact.normalization.raw_payload_hash
            
            # Extract audit fields
            artifact_id = artifact.audit.artifact_id
            created_at = artifact.audit.created_at
            collected_by = artifact.audit.collected_by
            
            # Extract collector signals
            collector_signals = artifact.collector_signals.model_dump() if artifact.collector_signals else {}
            
            # Convert artifact to complete JSON
            complete_artifact_json = artifact.model_dump()
            
            return RawArtifactData(
                complete_artifact_json=complete_artifact_json,
                content_hash=content_hash,
                raw_payload_hash=raw_payload_hash,
                artifact_id=artifact_id,
                created_at=created_at,
                collected_by=collected_by,
                collector_signals=collector_signals,
                first_seen_at=created_at  # Use audit timestamp for first_seen_at
            )
            
        except AttributeError as e:
            raise ValueError(f"Missing required field in artifact: {e}")
        except Exception as e:
            raise ValueError(f"Failed to extract raw artifact data: {e}")
    
    def prepare_source_raw_json(self, raw_data: RawArtifactData) -> Dict[str, Any]:
        """
        Prepare the source_raw JSON structure for database storage.
        
        Args:
            raw_data: Extracted raw artifact data
            
        Returns:
            Dictionary ready for coffees.source_raw JSON field
        """
        return {
            "complete_artifact": raw_data.complete_artifact_json,
            "content_hash": raw_data.content_hash,
            "raw_payload_hash": raw_data.raw_payload_hash,
            "artifact_id": raw_data.artifact_id,
            "created_at": raw_data.created_at,
            "collected_by": raw_data.collected_by,
            "collector_signals": raw_data.collector_signals,
            "persisted_at": datetime.now(timezone.utc).isoformat(),
            "persistence_version": "1.0"
        }
    
    def persist_raw_artifact(self, artifact: ArtifactModel) -> Tuple[bool, Optional[str]]:
        """
        Persist raw artifact data to database.
        
        Args:
            artifact: Validated canonical artifact
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Extract raw artifact data
            raw_data = self.extract_raw_artifact_data(artifact)
            
            # Prepare source_raw JSON
            source_raw_json = self.prepare_source_raw_json(raw_data)
            
            # Store in database via RPC
            success = self.rpc_client.upsert_coffee_with_raw_data(
                coffee_data={
                    "source_raw": source_raw_json,
                    "first_seen_at": raw_data.first_seen_at
                }
            )
            
            if success:
                logger.info(f"Successfully persisted raw artifact {raw_data.artifact_id}")
                return True, None
            else:
                error_msg = f"Failed to persist raw artifact {raw_data.artifact_id}"
                logger.error(error_msg)
                return False, error_msg
                
        except ValueError as e:
            error_msg = f"Invalid artifact data: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error persisting raw artifact: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def verify_hash_integrity(self, artifact: ArtifactModel) -> bool:
        """
        Verify hash integrity of artifact before persistence.
        
        Args:
            artifact: Canonical artifact to verify
            
        Returns:
            True if hashes are valid, False otherwise
        """
        try:
            # Check that hashes exist and are non-empty
            content_hash = artifact.normalization.content_hash
            raw_payload_hash = artifact.normalization.raw_payload_hash
            
            if not content_hash or not raw_payload_hash:
                logger.warning("Missing hashes in artifact")
                return False
            
            # Additional hash validation could be added here
            # For now, just verify they exist and are strings
            if not isinstance(content_hash, str) or not isinstance(raw_payload_hash, str):
                logger.warning("Invalid hash types in artifact")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying hash integrity: {e}")
            return False
    
    def get_audit_trail(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve audit trail for a specific artifact.
        
        Args:
            artifact_id: Artifact ID to retrieve
            
        Returns:
            Audit trail data or None if not found
        """
        try:
            logger.info(f"Retrieving audit trail for artifact {artifact_id}")
            
            if not self.db_integration.supabase_client:
                logger.error("Database client not available")
                return None
            
            # Query the coffees table for the artifact by searching in source_raw JSON
            # The artifact_id is stored in source_raw.audit.artifact_id
            response = self.db_integration.supabase_client.table("coffees").select(
                "id, source_raw, first_seen_at, created_at, updated_at"
            ).contains("source_raw", {"audit": {"artifact_id": artifact_id}}).execute()
            
            if not response.data:
                logger.warning(f"No audit trail found for artifact {artifact_id}")
                return None
            
            # Extract audit information from the first matching record
            coffee_record = response.data[0]
            source_raw = coffee_record.get("source_raw", {})
            
            # Build audit trail response
            audit_trail = {
                "artifact_id": artifact_id,
                "coffee_id": coffee_record.get("id"),
                "first_seen_at": coffee_record.get("first_seen_at"),
                "created_at": coffee_record.get("created_at"),
                "updated_at": coffee_record.get("updated_at"),
                "audit_data": source_raw.get("audit", {}),
                "collector_signals": source_raw.get("collector_signals", {}),
                "normalization": source_raw.get("normalization", {}),
                "source": source_raw.get("source"),
                "roaster_domain": source_raw.get("roaster_domain"),
                "scraped_at": source_raw.get("scraped_at")
            }
            
            logger.info(f"Successfully retrieved audit trail for artifact {artifact_id}")
            return audit_trail
            
        except Exception as e:
            logger.error(f"Error retrieving audit trail for {artifact_id}: {e}")
            return None

