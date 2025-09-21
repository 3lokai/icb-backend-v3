"""
Database integration for validator - stores validation results in scrape_artifacts table.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

from structlog import get_logger

from .artifact_validator import ValidationResult

logger = get_logger(__name__)


class DatabaseIntegration:
    """
    Handles database operations for validation results.
    
    Features:
    - Store validation results in scrape_artifacts table
    - Track validation status and errors
    - Support for manual review workflow
    - Integration with existing database schema
    """
    
    def __init__(self, supabase_client=None):
        """
        Initialize database integration.
        
        Args:
            supabase_client: Supabase client for database operations
        """
        self.supabase_client = supabase_client
        self.validation_stats = {
            'total_stored': 0,
            'valid_stored': 0,
            'invalid_stored': 0,
            'error_count': 0
        }
    
    def store_validation_result(
        self,
        validation_result: ValidationResult,
        scrape_run_id: str,
        roaster_id: str,
        platform: str,
        response_filename: str
    ) -> Optional[str]:
        """
        Store validation result in database.
        
        Args:
            validation_result: Validation result to store
            scrape_run_id: Scrape run identifier
            roaster_id: Roaster identifier
            platform: Platform type
            response_filename: Response filename from storage
            
        Returns:
            Artifact ID if successful, None if failed
        """
        try:
            # Determine validation status
            if validation_result.is_valid:
                validation_status = "valid"
            else:
                validation_status = "invalid"
            
            # Prepare artifact data for storage
            artifact_data = {
                "scrape_run_id": scrape_run_id,
                "artifact_data": validation_result.artifact_data,
                "validation_status": validation_status,
                "validation_errors": validation_result.errors if not validation_result.is_valid else None,
                "created_at": validation_result.validated_at.isoformat(),
                "processed_at": datetime.now(timezone.utc).isoformat() if validation_result.is_valid else None
            }
            
            # Store in database
            if self.supabase_client:
                result = self.supabase_client.table("scrape_artifacts").insert(artifact_data).execute()
                
                if result.data:
                    artifact_id = result.data[0].get("id")
                    
                    logger.info(
                        "Stored validation result in database",
                        artifact_id=artifact_id,
                        validation_status=validation_status,
                        roaster_id=roaster_id,
                        platform=platform,
                        response_filename=response_filename
                    )
                    
                    # Update stats
                    self.validation_stats['total_stored'] += 1
                    if validation_result.is_valid:
                        self.validation_stats['valid_stored'] += 1
                    else:
                        self.validation_stats['invalid_stored'] += 1
                    
                    return artifact_id
                else:
                    logger.error(
                        "Failed to store validation result - no data returned",
                        roaster_id=roaster_id,
                        platform=platform,
                        response_filename=response_filename
                    )
                    return None
            else:
                # Mock database storage for testing
                artifact_id = f"artifact_{scrape_run_id}_{validation_result.artifact_id}"
                
                logger.info(
                    "Mock stored validation result",
                    artifact_id=artifact_id,
                    validation_status=validation_status,
                    roaster_id=roaster_id,
                    platform=platform,
                    response_filename=response_filename
                )
                
                # Update stats
                self.validation_stats['total_stored'] += 1
                if validation_result.is_valid:
                    self.validation_stats['valid_stored'] += 1
                else:
                    self.validation_stats['invalid_stored'] += 1
                
                return artifact_id
                
        except Exception as e:
            logger.error(
                "Failed to store validation result in database",
                roaster_id=roaster_id,
                platform=platform,
                response_filename=response_filename,
                error=str(e)
            )
            
            self.validation_stats['error_count'] += 1
            return None
    
    def store_batch_validation_results(
        self,
        validation_results: List[ValidationResult],
        scrape_run_id: str,
        roaster_id: str,
        platform: str,
        response_filenames: List[str]
    ) -> List[Optional[str]]:
        """
        Store batch validation results in database.
        
        Args:
            validation_results: List of validation results to store
            scrape_run_id: Scrape run identifier
            roaster_id: Roaster identifier
            platform: Platform type
            response_filenames: List of response filenames
            
        Returns:
            List of artifact IDs (None for failed storage)
        """
        artifact_ids = []
        
        for i, (result, filename) in enumerate(zip(validation_results, response_filenames)):
            artifact_id = self.store_validation_result(
                validation_result=result,
                scrape_run_id=scrape_run_id,
                roaster_id=roaster_id,
                platform=platform,
                response_filename=filename
            )
            artifact_ids.append(artifact_id)
        
        logger.info(
            "Stored batch validation results",
            total_results=len(validation_results),
            successful_storage=sum(1 for aid in artifact_ids if aid is not None),
            failed_storage=sum(1 for aid in artifact_ids if aid is None),
            roaster_id=roaster_id,
            platform=platform
        )
        
        return artifact_ids
    
    def get_validation_results(
        self,
        scrape_run_id: Optional[str] = None,
        validation_status: Optional[str] = None,
        roaster_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get validation results from database.
        
        Args:
            scrape_run_id: Filter by scrape run ID
            validation_status: Filter by validation status (valid, invalid)
            roaster_id: Filter by roaster ID
            limit: Maximum number of results to return
            
        Returns:
            List of validation result dictionaries
        """
        try:
            if self.supabase_client:
                query = self.supabase_client.table("scrape_artifacts").select("*")
                
                if scrape_run_id:
                    query = query.eq("scrape_run_id", scrape_run_id)
                
                if validation_status:
                    query = query.eq("validation_status", validation_status)
                
                if roaster_id:
                    # Note: This would require a join with scrape_runs table
                    # For now, we'll filter by artifact_data content
                    pass
                
                query = query.limit(limit).order("created_at", desc=True)
                
                result = query.execute()
                
                if result.data:
                    logger.info(
                        "Retrieved validation results from database",
                        count=len(result.data),
                        scrape_run_id=scrape_run_id,
                        validation_status=validation_status
                    )
                    return result.data
                else:
                    logger.info("No validation results found")
                    return []
            else:
                # Mock database query for testing
                logger.info("Mock retrieved validation results")
                return []
                
        except Exception as e:
            logger.error(
                "Failed to get validation results from database",
                error=str(e)
            )
            return []
    
    def update_validation_status(
        self,
        artifact_id: str,
        new_status: str,
        manual_review_notes: Optional[str] = None
    ) -> bool:
        """
        Update validation status for manual review workflow.
        
        Args:
            artifact_id: Artifact ID to update
            new_status: New validation status
            manual_review_notes: Notes from manual review
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "validation_status": new_status,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            if manual_review_notes:
                # Store manual review notes in validation_errors field
                update_data["validation_errors"] = {
                    "manual_review_notes": manual_review_notes,
                    "manual_review_at": datetime.now(timezone.utc).isoformat()
                }
            
            if self.supabase_client:
                result = self.supabase_client.table("scrape_artifacts").update(update_data).eq("id", artifact_id).execute()
                
                if result.data:
                    logger.info(
                        "Updated validation status",
                        artifact_id=artifact_id,
                        new_status=new_status,
                        manual_review_notes=manual_review_notes is not None
                    )
                    return True
                else:
                    logger.error(
                        "Failed to update validation status - no data returned",
                        artifact_id=artifact_id
                    )
                    return False
            else:
                # Mock database update for testing
                logger.info(
                    "Mock updated validation status",
                    artifact_id=artifact_id,
                    new_status=new_status
                )
                return True
                
        except Exception as e:
            logger.error(
                "Failed to update validation status",
                artifact_id=artifact_id,
                error=str(e)
            )
            return False
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics.
        
        Returns:
            Dictionary with validation statistics
        """
        stats = self.validation_stats.copy()
        
        if stats['total_stored'] > 0:
            stats['valid_rate'] = stats['valid_stored'] / stats['total_stored']
            stats['invalid_rate'] = stats['invalid_stored'] / stats['total_stored']
            stats['error_rate'] = stats['error_count'] / stats['total_stored']
        else:
            stats['valid_rate'] = 0.0
            stats['invalid_rate'] = 0.0
            stats['error_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset validation statistics."""
        self.validation_stats = {
            'total_stored': 0,
            'valid_stored': 0,
            'invalid_stored': 0,
            'error_count': 0
        }
