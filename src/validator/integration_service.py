"""
Integration service for validator - coordinates validation with A.2 fetcher pipeline.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from structlog import get_logger

from .artifact_validator import ArtifactValidator
from .storage_reader import StorageReader
from .validation_pipeline import ValidationPipeline
from .database_integration import DatabaseIntegration
from .config import ValidatorConfig

logger = get_logger(__name__)


class ValidatorIntegrationService:
    """
    Integration service for validator with A.2 fetcher pipeline.
    
    Features:
    - Coordinates validation with A.2 storage system
    - Manages validation pipeline execution
    - Handles database integration for results
    - Provides monitoring and metrics
    """
    
    def __init__(
        self,
        config: Optional[ValidatorConfig] = None,
        supabase_client=None
    ):
        """
        Initialize validator integration service.
        
        Args:
            config: Validator configuration
            supabase_client: Supabase client for database operations
        """
        self.config = config or ValidatorConfig()
        self.supabase_client = supabase_client
        
        # Initialize components
        self.storage_reader = StorageReader(base_storage_path=self.config.storage_path)
        self.validator = ArtifactValidator(storage_reader=self.storage_reader)
        self.validation_pipeline = ValidationPipeline(
            storage_reader=self.storage_reader,
            validator=self.validator
        )
        self.database_integration = DatabaseIntegration(supabase_client=supabase_client)
        
        # Service stats
        self.service_stats = {
            'total_processed': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'database_errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def process_roaster_artifacts(
        self,
        roaster_id: str,
        platform: str,
        scrape_run_id: str,
        response_filenames: List[str]
    ) -> Dict[str, Any]:
        """
        Process artifacts for a specific roaster through validation pipeline.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type
            scrape_run_id: Scrape run identifier
            response_filenames: List of response filenames to process
            
        Returns:
            Dictionary with processing results
        """
        logger.info(
            "Starting artifact processing for roaster",
            roaster_id=roaster_id,
            platform=platform,
            scrape_run_id=scrape_run_id,
            artifact_count=len(response_filenames)
        )
        
        self.service_stats['start_time'] = datetime.now(timezone.utc)
        
        try:
            # Process artifacts through validation pipeline
            validation_results = self.validation_pipeline.process_storage_artifacts(
                roaster_id=roaster_id,
                platform=platform,
                response_filenames=response_filenames
            )
            
            # Store validation results in database
            artifact_ids = self.database_integration.store_batch_validation_results(
                validation_results=validation_results,
                scrape_run_id=scrape_run_id,
                roaster_id=roaster_id,
                platform=platform,
                response_filenames=response_filenames
            )
            
            # Update service stats
            self.service_stats['total_processed'] += len(response_filenames)
            self.service_stats['successful_validations'] += sum(
                1 for result in validation_results if result.is_valid
            )
            self.service_stats['failed_validations'] += sum(
                1 for result in validation_results if not result.is_valid
            )
            self.service_stats['database_errors'] += sum(
                1 for aid in artifact_ids if aid is None
            )
            
            self.service_stats['end_time'] = datetime.now(timezone.utc)
            
            # Prepare results
            results = {
                'roaster_id': roaster_id,
                'platform': platform,
                'scrape_run_id': scrape_run_id,
                'total_artifacts': len(response_filenames),
                'valid_artifacts': sum(1 for result in validation_results if result.is_valid),
                'invalid_artifacts': sum(1 for result in validation_results if not result.is_valid),
                'artifact_ids': artifact_ids,
                'validation_results': validation_results,
                'processing_time_seconds': (
                    self.service_stats['end_time'] - self.service_stats['start_time']
                ).total_seconds() if self.service_stats['end_time'] else None
            }
            
            logger.info(
                "Completed artifact processing for roaster",
                roaster_id=roaster_id,
                platform=platform,
                scrape_run_id=scrape_run_id,
                total_artifacts=results['total_artifacts'],
                valid_artifacts=results['valid_artifacts'],
                invalid_artifacts=results['invalid_artifacts'],
                processing_time_seconds=results['processing_time_seconds']
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Failed to process artifacts for roaster",
                roaster_id=roaster_id,
                platform=platform,
                scrape_run_id=scrape_run_id,
                error=str(e)
            )
            
            self.service_stats['end_time'] = datetime.now(timezone.utc)
            
            return {
                'roaster_id': roaster_id,
                'platform': platform,
                'scrape_run_id': scrape_run_id,
                'error': str(e),
                'success': False
            }
    
    def process_artifact_batch(
        self,
        artifacts: List[Dict[str, Any]],
        scrape_run_id: str,
        roaster_id: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Process a batch of artifacts through validation pipeline.
        
        Args:
            artifacts: List of artifact data to validate
            scrape_run_id: Scrape run identifier
            roaster_id: Roaster identifier
            platform: Platform type
            
        Returns:
            Dictionary with processing results
        """
        logger.info(
            "Starting batch artifact processing",
            roaster_id=roaster_id,
            platform=platform,
            scrape_run_id=scrape_run_id,
            artifact_count=len(artifacts)
        )
        
        self.service_stats['start_time'] = datetime.now(timezone.utc)
        
        try:
            # Process artifacts through validation pipeline
            validation_results = self.validation_pipeline.process_artifact_batch(artifacts)
            
            # Generate response filenames for database storage
            response_filenames = [
                f"{roaster_id}_{platform}_{i}_batch.json"
                for i in range(len(artifacts))
            ]
            
            # Store validation results in database
            artifact_ids = self.database_integration.store_batch_validation_results(
                validation_results=validation_results,
                scrape_run_id=scrape_run_id,
                roaster_id=roaster_id,
                platform=platform,
                response_filenames=response_filenames
            )
            
            # Update service stats
            self.service_stats['total_processed'] += len(artifacts)
            self.service_stats['successful_validations'] += sum(
                1 for result in validation_results if result.is_valid
            )
            self.service_stats['failed_validations'] += sum(
                1 for result in validation_results if not result.is_valid
            )
            self.service_stats['database_errors'] += sum(
                1 for aid in artifact_ids if aid is None
            )
            
            self.service_stats['end_time'] = datetime.now(timezone.utc)
            
            # Prepare results
            results = {
                'roaster_id': roaster_id,
                'platform': platform,
                'scrape_run_id': scrape_run_id,
                'total_artifacts': len(artifacts),
                'valid_artifacts': sum(1 for result in validation_results if result.is_valid),
                'invalid_artifacts': sum(1 for result in validation_results if not result.is_valid),
                'artifact_ids': artifact_ids,
                'validation_results': validation_results,
                'processing_time_seconds': (
                    self.service_stats['end_time'] - self.service_stats['start_time']
                ).total_seconds() if self.service_stats['end_time'] else None
            }
            
            logger.info(
                "Completed batch artifact processing",
                roaster_id=roaster_id,
                platform=platform,
                scrape_run_id=scrape_run_id,
                total_artifacts=results['total_artifacts'],
                valid_artifacts=results['valid_artifacts'],
                invalid_artifacts=results['invalid_artifacts'],
                processing_time_seconds=results['processing_time_seconds']
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Failed to process batch artifacts",
                roaster_id=roaster_id,
                platform=platform,
                scrape_run_id=scrape_run_id,
                error=str(e)
            )
            
            self.service_stats['end_time'] = datetime.now(timezone.utc)
            
            return {
                'roaster_id': roaster_id,
                'platform': platform,
                'scrape_run_id': scrape_run_id,
                'error': str(e),
                'success': False
            }
    
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
            validation_status: Filter by validation status
            roaster_id: Filter by roaster ID
            limit: Maximum number of results
            
        Returns:
            List of validation result dictionaries
        """
        return self.database_integration.get_validation_results(
            scrape_run_id=scrape_run_id,
            validation_status=validation_status,
            roaster_id=roaster_id,
            limit=limit
        )
    
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
        return self.database_integration.update_validation_status(
            artifact_id=artifact_id,
            new_status=new_status,
            manual_review_notes=manual_review_notes
        )
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        stats = self.service_stats.copy()
        
        # Add component stats
        stats['validator_stats'] = self.validator.get_validation_stats()
        stats['pipeline_stats'] = self.validation_pipeline.get_pipeline_stats()
        stats['database_stats'] = self.database_integration.get_validation_stats()
        
        # Calculate success rate
        if stats['total_processed'] > 0:
            stats['success_rate'] = stats['successful_validations'] / stats['total_processed']
            stats['failure_rate'] = stats['failed_validations'] / stats['total_processed']
            stats['database_error_rate'] = stats['database_errors'] / stats['total_processed']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['database_error_rate'] = 0.0
        
        return stats
    
    def reset_service_stats(self):
        """Reset service statistics."""
        self.service_stats = {
            'total_processed': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'database_errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Reset component stats
        self.validator.reset_stats()
        self.validation_pipeline.reset_pipeline_stats()
        self.database_integration.reset_stats()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.
        
        Returns:
            Dictionary with health check results
        """
        health_status = {
            'overall_status': 'healthy',
            'components': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Check storage reader
            storage_stats = self.storage_reader.get_storage_stats()
            health_status['components']['storage_reader'] = {
                'status': 'healthy',
                'total_files': storage_stats['total_files'],
                'storage_path': storage_stats['storage_path']
            }
        except Exception as e:
            health_status['components']['storage_reader'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'
        
        try:
            # Check validator
            validator_stats = self.validator.get_validation_stats()
            health_status['components']['validator'] = {
                'status': 'healthy',
                'total_validated': validator_stats['total_validated']
            }
        except Exception as e:
            health_status['components']['validator'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'
        
        try:
            # Check database integration
            database_stats = self.database_integration.get_validation_stats()
            health_status['components']['database_integration'] = {
                'status': 'healthy',
                'total_stored': database_stats['total_stored']
            }
        except Exception as e:
            health_status['components']['database_integration'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'
        
        return health_status
