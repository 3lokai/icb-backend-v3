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
from .rpc_client import RPCClient
from .artifact_mapper import ArtifactMapper
from .raw_artifact_persistence import RawArtifactPersistence
from ..config.validator_config import ValidatorConfig
from ..config.imagekit_config import ImageKitConfig
from ..images.deduplication_service import ImageDeduplicationService
from ..images.imagekit_service import ImageKitService
from ..images.imagekit_integration import ImageKitIntegrationService
from ..parser.weight_parser import WeightParser
from ..parser.roast_parser import RoastLevelParser
from ..parser.process_parser import ProcessMethodParser
from ..parser.tag_normalization import TagNormalizationService
from ..parser.notes_extraction import NotesExtractionService

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
        self.rpc_client = RPCClient(supabase_client=supabase_client)
        self.raw_artifact_persistence = RawArtifactPersistence(
            db_integration=self.database_integration,
            rpc_client=self.rpc_client
        )
        
        # Initialize image processing services
        if self.config.enable_image_deduplication:
            self.image_deduplication_service = ImageDeduplicationService(self.rpc_client)
        else:
            self.image_deduplication_service = None
        
        if self.config.enable_imagekit_upload and self.config.imagekit_config:
            self.imagekit_service = ImageKitService(self.config.imagekit_config)
            self.imagekit_integration = ImageKitIntegrationService(
                rpc_client=self.rpc_client,
                imagekit_config=self.config.imagekit_config,
                enable_deduplication=self.config.enable_image_deduplication,
                enable_imagekit=self.config.enable_imagekit_upload
            )
        else:
            self.imagekit_service = None
            self.imagekit_integration = None
        
        # Initialize weight parser service
        if self.config.enable_weight_parsing:
            self.weight_parser = WeightParser()
        else:
            self.weight_parser = None
        
        # Initialize roast parser service
        if self.config.enable_roast_parsing:
            self.roast_parser = RoastLevelParser()
        else:
            self.roast_parser = None
        
        # Initialize process parser service
        if self.config.enable_process_parsing:
            self.process_parser = ProcessMethodParser()
        else:
            self.process_parser = None
        
        # Initialize tag normalization service
        if self.config.enable_tag_normalization:
            self.tag_normalization_service = TagNormalizationService()
        else:
            self.tag_normalization_service = None
        
        # Initialize notes extraction service
        if self.config.enable_notes_extraction:
            self.notes_extraction_service = NotesExtractionService()
        else:
            self.notes_extraction_service = None
        
        # Initialize artifact mapper after image services
        self.artifact_mapper = ArtifactMapper(integration_service=self)
        
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
            
            # Persist raw artifacts for valid results
            raw_persistence_results = self._persist_raw_artifacts(
                validation_results=validation_results,
                roaster_id=roaster_id,
                platform=platform
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
    
    def _persist_raw_artifacts(
        self,
        validation_results: List[Any],
        roaster_id: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Persist raw artifacts for valid validation results.
        
        Args:
            validation_results: List of validation results
            roaster_id: Roaster identifier
            platform: Platform type
            
        Returns:
            Dictionary with raw persistence results
        """
        logger.info(
            "Starting raw artifact persistence",
            roaster_id=roaster_id,
            platform=platform,
            artifact_count=len(validation_results)
        )
        
        persistence_results = {
            'total_artifacts': len(validation_results),
            'successful_persistence': 0,
            'failed_persistence': 0,
            'persistence_errors': []
        }
        
        for result in validation_results:
            if not result.is_valid:
                # Skip invalid artifacts
                continue
                
            try:
                # Reconstruct ArtifactModel from artifact_data
                from .models import ArtifactModel
                artifact = ArtifactModel(**result.artifact_data)
                
                # Verify hash integrity before persistence
                if not self.raw_artifact_persistence.verify_hash_integrity(artifact):
                    logger.warning(
                        "Hash integrity check failed for artifact",
                        artifact_id=artifact.audit.artifact_id
                    )
                    persistence_results['failed_persistence'] += 1
                    persistence_results['persistence_errors'].append(
                        f"Hash integrity check failed for {artifact.audit.artifact_id}"
                    )
                    continue
                
                # Persist raw artifact
                success, error_msg = self.raw_artifact_persistence.persist_raw_artifact(artifact)
                
                if success:
                    persistence_results['successful_persistence'] += 1
                    logger.info(
                        "Successfully persisted raw artifact",
                        artifact_id=artifact.audit.artifact_id
                    )
                else:
                    persistence_results['failed_persistence'] += 1
                    persistence_results['persistence_errors'].append(
                        f"Failed to persist {artifact.audit.artifact_id}: {error_msg}"
                    )
                    logger.error(
                        "Failed to persist raw artifact",
                        artifact_id=artifact.audit.artifact_id,
                        error=error_msg
                    )
                    
            except Exception as e:
                persistence_results['failed_persistence'] += 1
                persistence_results['persistence_errors'].append(
                    f"Unexpected error persisting {result.artifact_id}: {str(e)}"
                )
                logger.error(
                    "Unexpected error persisting raw artifact",
                    artifact_id=result.artifact_id,
                    error=str(e)
                )
        
        logger.info(
            "Completed raw artifact persistence",
            roaster_id=roaster_id,
            platform=platform,
            successful=persistence_results['successful_persistence'],
            failed=persistence_results['failed_persistence']
        )
        
        return persistence_results
    
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
        stats['rpc_stats'] = self.rpc_client.get_rpc_stats()
        stats['mapper_stats'] = self.artifact_mapper.get_mapping_stats()
        
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
        self.rpc_client.reset_stats()
        self.artifact_mapper.reset_stats()
    
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
    
    def transform_and_upsert_artifacts(
        self,
        validation_results: List[Any],
        roaster_id: str,
        metadata_only: bool = False
    ) -> Dict[str, Any]:
        """
        Transform validated artifacts to RPC payloads and upsert to database.
        
        Args:
            validation_results: List of validation results with valid artifacts
            roaster_id: Roaster ID for the artifacts
            metadata_only: Whether this is a metadata-only update
            
        Returns:
            Dictionary with transformation and upsert results
        """
        logger.info(
            "Starting artifact transformation and upsert",
            roaster_id=roaster_id,
            artifact_count=len(validation_results),
            metadata_only=metadata_only
        )
        
        transformation_results = {
            'roaster_id': roaster_id,
            'metadata_only': metadata_only,
            'total_artifacts': len(validation_results),
            'successful_transformations': 0,
            'failed_transformations': 0,
            'successful_upserts': 0,
            'failed_upserts': 0,
            'coffee_ids': [],
            'variant_ids': [],
            'price_ids': [],
            'image_ids': [],
            'errors': []
        }
        
        for validation_result in validation_results:
            try:
                if not validation_result.is_valid:
                    logger.warning(
                        "Skipping invalid artifact for transformation",
                        artifact_id=getattr(validation_result, 'artifact_id', 'unknown')
                    )
                    transformation_results['failed_transformations'] += 1
                    continue
                
                # Transform artifact to RPC payloads
                rpc_payloads = self.artifact_mapper.map_artifact_to_rpc_payloads(
                    artifact=validation_result.artifact_data,
                    roaster_id=roaster_id,
                    metadata_only=metadata_only
                )
                
                transformation_results['successful_transformations'] += 1
                
                # Upsert coffee record
                coffee_id = self.rpc_client.upsert_coffee(**rpc_payloads['coffee'])
                transformation_results['coffee_ids'].append(coffee_id)
                transformation_results['successful_upserts'] += 1
                
                # Upsert variants
                for variant_payload in rpc_payloads['variants']:
                    variant_payload['p_coffee_id'] = coffee_id
                    variant_id = self.rpc_client.upsert_variant(**variant_payload)
                    transformation_results['variant_ids'].append(variant_id)
                    transformation_results['successful_upserts'] += 1
                
                # Insert prices - match by variant order
                variant_ids = transformation_results['variant_ids']
                for i, price_payload in enumerate(rpc_payloads['prices']):
                    if i < len(variant_ids):
                        price_payload['variant_id'] = variant_ids[i]
                        price_id = self.rpc_client.insert_price(**price_payload)
                        transformation_results['price_ids'].append(price_id)
                        transformation_results['successful_upserts'] += 1
                    else:
                        logger.warning(
                            "Price payload index exceeds variant count",
                            price_index=i,
                            variant_count=len(variant_ids)
                        )
                
                # Upsert images (only if not metadata-only)
                if not metadata_only:
                    for image_payload in rpc_payloads['images']:
                        image_payload['p_coffee_id'] = coffee_id
                        image_id = self.rpc_client.upsert_coffee_image(**image_payload)
                        transformation_results['image_ids'].append(image_id)
                        transformation_results['successful_upserts'] += 1
                
                logger.info(
                    "Successfully transformed and upserted artifact",
                    artifact_id=getattr(validation_result, 'artifact_id', 'unknown'),
                    coffee_id=coffee_id,
                    variants_count=len(rpc_payloads['variants']),
                    prices_count=len(rpc_payloads['prices']),
                    images_count=len(rpc_payloads['images'])
                )
                
            except Exception as e:
                logger.error(
                    "Failed to transform and upsert artifact",
                    artifact_id=getattr(validation_result, 'artifact_id', 'unknown'),
                    error=str(e)
                )
                
                transformation_results['failed_transformations'] += 1
                transformation_results['failed_upserts'] += 1
                transformation_results['errors'].append({
                    'artifact_id': getattr(validation_result, 'artifact_id', 'unknown'),
                    'error': str(e)
                })
        
        logger.info(
            "Completed artifact transformation and upsert",
            roaster_id=roaster_id,
            total_artifacts=transformation_results['total_artifacts'],
            successful_transformations=transformation_results['successful_transformations'],
            failed_transformations=transformation_results['failed_transformations'],
            successful_upserts=transformation_results['successful_upserts'],
            failed_upserts=transformation_results['failed_upserts']
        )
        
        return transformation_results
    
    def process_artifacts_with_rpc_upsert(
        self,
        roaster_id: str,
        platform: str,
        scrape_run_id: str,
        response_filenames: List[str],
        metadata_only: bool = False
    ) -> Dict[str, Any]:
        """
        Process artifacts through validation pipeline and upsert to database via RPC.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type
            scrape_run_id: Scrape run identifier
            response_filenames: List of response filenames to process
            metadata_only: Whether this is a metadata-only update
            
        Returns:
            Dictionary with processing results including RPC upsert results
        """
        logger.info(
            "Starting artifact processing with RPC upsert",
            roaster_id=roaster_id,
            platform=platform,
            scrape_run_id=scrape_run_id,
            artifact_count=len(response_filenames),
            metadata_only=metadata_only
        )
        
        # Process artifacts through validation pipeline
        validation_results = self.validation_pipeline.process_storage_artifacts(
            roaster_id=roaster_id,
            platform=platform,
            response_filenames=response_filenames
        )
        
        # Filter to only valid artifacts for RPC transformation
        valid_artifacts = [result for result in validation_results if result.is_valid]
        
        if not valid_artifacts:
            logger.warning(
                "No valid artifacts found for RPC transformation",
                roaster_id=roaster_id,
                platform=platform,
                total_artifacts=len(validation_results)
            )
            
            return {
                'roaster_id': roaster_id,
                'platform': platform,
                'scrape_run_id': scrape_run_id,
                'total_artifacts': len(response_filenames),
                'valid_artifacts': 0,
                'invalid_artifacts': len(validation_results),
                'rpc_transformation': {
                    'successful_transformations': 0,
                    'failed_transformations': 0,
                    'successful_upserts': 0,
                    'failed_upserts': 0
                },
                'success': False,
                'error': 'No valid artifacts found'
            }
        
        # Transform and upsert valid artifacts
        rpc_results = self.transform_and_upsert_artifacts(
            validation_results=valid_artifacts,
            roaster_id=roaster_id,
            metadata_only=metadata_only
        )
        
        # Store validation results in database (for audit trail)
        artifact_ids = self.database_integration.store_batch_validation_results(
            validation_results=validation_results,
            scrape_run_id=scrape_run_id,
            roaster_id=roaster_id,
            platform=platform,
            response_filenames=response_filenames
        )
        
        # Update service stats
        self.service_stats['total_processed'] += len(response_filenames)
        self.service_stats['successful_validations'] += len(valid_artifacts)
        self.service_stats['failed_validations'] += len(validation_results) - len(valid_artifacts)
        
        # Prepare comprehensive results
        results = {
            'roaster_id': roaster_id,
            'platform': platform,
            'scrape_run_id': scrape_run_id,
            'total_artifacts': len(response_filenames),
            'valid_artifacts': len(valid_artifacts),
            'invalid_artifacts': len(validation_results) - len(valid_artifacts),
            'artifact_ids': artifact_ids,
            'validation_results': validation_results,
            'rpc_transformation': rpc_results,
            'processing_time_seconds': (
                self.service_stats['end_time'] - self.service_stats['start_time']
            ).total_seconds() if self.service_stats['end_time'] else None,
            'success': True
        }
        
        logger.info(
            "Completed artifact processing with RPC upsert",
            roaster_id=roaster_id,
            platform=platform,
            scrape_run_id=scrape_run_id,
            total_artifacts=results['total_artifacts'],
            valid_artifacts=results['valid_artifacts'],
            invalid_artifacts=results['invalid_artifacts'],
            successful_upserts=rpc_results['successful_upserts'],
            failed_upserts=rpc_results['failed_upserts']
        )
        
        return results
