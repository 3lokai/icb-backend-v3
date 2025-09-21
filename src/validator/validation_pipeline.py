"""
Validation pipeline for processing artifacts through validation workflow.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from structlog import get_logger

from .artifact_validator import ArtifactValidator, ValidationResult
from .storage_reader import StorageReader

logger = get_logger(__name__)


class ValidationPipeline:
    """
    Validation pipeline for processing artifacts through validation workflow.
    
    Features:
    - Batch processing of artifacts
    - Integration with A.2 storage system
    - Error persistence for manual review
    - Validation metrics and monitoring
    """
    
    def __init__(
        self,
        storage_reader: Optional[StorageReader] = None,
        validator: Optional[ArtifactValidator] = None
    ):
        """
        Initialize validation pipeline.
        
        Args:
            storage_reader: Storage reader for A.2 integration
            validator: Artifact validator instance
        """
        self.storage_reader = storage_reader or StorageReader()
        self.validator = validator or ArtifactValidator(self.storage_reader)
        self.pipeline_stats = {
            'total_processed': 0,
            'valid_count': 0,
            'invalid_count': 0,
            'error_count': 0,
            'start_time': None,
            'end_time': None
        }
    
    def process_storage_artifacts(
        self,
        roaster_id: str,
        platform: str,
        response_filenames: List[str]
    ) -> List[ValidationResult]:
        """
        Process artifacts from A.2 storage through validation pipeline.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type
            response_filenames: List of response filenames to process
            
        Returns:
            List of validation results
        """
        logger.info(
            "Starting validation pipeline",
            roaster_id=roaster_id,
            platform=platform,
            artifact_count=len(response_filenames)
        )
        
        self.pipeline_stats['start_time'] = datetime.now(timezone.utc)
        results = []
        
        for filename in response_filenames:
            try:
                # Validate artifact from storage
                result = self.validator.validate_from_storage(
                    roaster_id=roaster_id,
                    platform=platform,
                    response_filename=filename
                )
                
                results.append(result)
                self.pipeline_stats['total_processed'] += 1
                
                if result.is_valid:
                    self.pipeline_stats['valid_count'] += 1
                else:
                    self.pipeline_stats['invalid_count'] += 1
                    # Persist invalid artifacts for manual review
                    self._persist_invalid_artifact(result)
                
            except Exception as e:
                logger.error(
                    "Failed to process artifact",
                    roaster_id=roaster_id,
                    platform=platform,
                    filename=filename,
                    error=str(e)
                )
                
                self.pipeline_stats['error_count'] += 1
                
                # Create error result
                error_result = ValidationResult(
                    is_valid=False,
                    artifact_data={},
                    errors=[f"Pipeline error: {str(e)}"],
                    artifact_id=f"{roaster_id}_{platform}_{filename}"
                )
                results.append(error_result)
        
        self.pipeline_stats['end_time'] = datetime.now(timezone.utc)
        
        logger.info(
            "Validation pipeline completed",
            roaster_id=roaster_id,
            platform=platform,
            total_processed=self.pipeline_stats['total_processed'],
            valid_count=self.pipeline_stats['valid_count'],
            invalid_count=self.pipeline_stats['invalid_count'],
            error_count=self.pipeline_stats['error_count']
        )
        
        return results
    
    def process_artifact_batch(self, artifacts: List[Dict[str, Any]]) -> List[ValidationResult]:
        """
        Process a batch of artifacts through validation pipeline.
        
        Args:
            artifacts: List of artifact data to validate
            
        Returns:
            List of validation results
        """
        logger.info(
            "Starting batch validation pipeline",
            artifact_count=len(artifacts)
        )
        
        self.pipeline_stats['start_time'] = datetime.now(timezone.utc)
        
        # Validate batch using validator
        results = self.validator.validate_batch(artifacts)
        
        # Update pipeline stats
        self.pipeline_stats['total_processed'] = len(artifacts)
        self.pipeline_stats['valid_count'] = sum(1 for r in results if r.is_valid)
        self.pipeline_stats['invalid_count'] = sum(1 for r in results if not r.is_valid)
        
        # Persist invalid artifacts
        for result in results:
            if not result.is_valid:
                self._persist_invalid_artifact(result)
        
        self.pipeline_stats['end_time'] = datetime.now(timezone.utc)
        
        logger.info(
            "Batch validation pipeline completed",
            total_processed=self.pipeline_stats['total_processed'],
            valid_count=self.pipeline_stats['valid_count'],
            invalid_count=self.pipeline_stats['invalid_count']
        )
        
        return results
    
    def _persist_invalid_artifact(self, result: ValidationResult):
        """
        Persist invalid artifact for manual review.
        
        Args:
            result: Validation result with invalid artifact
        """
        try:
            # Create invalid artifacts directory
            invalid_dir = Path("data/validator/invalid_artifacts")
            invalid_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename for invalid artifact
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"invalid_{result.artifact_id}_{timestamp}.json"
            file_path = invalid_dir / filename
            
            # Prepare data for persistence
            invalid_data = {
                'artifact_id': result.artifact_id,
                'validated_at': result.validated_at.isoformat(),
                'validation_errors': result.errors,
                'validation_warnings': result.warnings,
                'artifact_data': result.artifact_data
            }
            
            # Write invalid artifact data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(invalid_data, f, indent=2, ensure_ascii=False)
            
            logger.info(
                "Persisted invalid artifact for manual review",
                artifact_id=result.artifact_id,
                error_count=len(result.errors),
                file_path=str(file_path)
            )
            
        except Exception as e:
            logger.error(
                "Failed to persist invalid artifact",
                artifact_id=result.artifact_id,
                error=str(e)
            )
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            Dictionary with pipeline statistics
        """
        stats = self.pipeline_stats.copy()
        
        # Add validator stats
        validator_stats = self.validator.get_validation_stats()
        stats['validator_stats'] = validator_stats
        
        # Calculate processing time
        if stats['start_time'] and stats['end_time']:
            processing_time = (stats['end_time'] - stats['start_time']).total_seconds()
            stats['processing_time_seconds'] = processing_time
        else:
            stats['processing_time_seconds'] = None
        
        # Calculate success rate
        if stats['total_processed'] > 0:
            stats['success_rate'] = stats['valid_count'] / stats['total_processed']
            stats['error_rate'] = stats['error_count'] / stats['total_processed']
        else:
            stats['success_rate'] = 0.0
            stats['error_rate'] = 0.0
        
        return stats
    
    def reset_pipeline_stats(self):
        """Reset pipeline statistics."""
        self.pipeline_stats = {
            'total_processed': 0,
            'valid_count': 0,
            'invalid_count': 0,
            'error_count': 0,
            'start_time': None,
            'end_time': None
        }
        self.validator.reset_stats()
