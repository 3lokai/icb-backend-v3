"""
Artifact validator service for validating scraped artifacts against Pydantic models.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

from structlog import get_logger
from pydantic import ValidationError

from .models import ArtifactModel
from .storage_reader import StorageReader
from ..parser.coffee_classification_parser import CoffeeClassificationParser

logger = get_logger(__name__)


class ValidationResult:
    """Validation result container."""
    
    def __init__(
        self,
        is_valid: bool,
        artifact_data: Dict[str, Any],
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        artifact_id: Optional[str] = None
    ):
        self.is_valid = is_valid
        self.artifact_data = artifact_data
        self.errors = errors or []
        self.warnings = warnings or []
        self.artifact_id = artifact_id
        self.validated_at = datetime.now(timezone.utc)


class ArtifactValidator:
    """
    Validates artifacts against Pydantic models with detailed error reporting.
    
    Features:
    - Strict schema validation using Pydantic v2 models
    - Detailed error reporting with context
    - Support for nested object validation
    - Error persistence for manual review
    - Integration with A.2 storage system
    """
    
    def __init__(self, storage_reader: Optional[StorageReader] = None, llm_service: Optional[Any] = None):
        """
        Initialize artifact validator.
        
        Args:
            storage_reader: Storage reader for A.2 integration
            llm_service: Optional LLM service for classification fallback
        """
        self.storage_reader = storage_reader or StorageReader()
        self.classification_parser = CoffeeClassificationParser(llm_service=llm_service)
        self.validation_stats = {
            'total_validated': 0,
            'valid_count': 0,
            'invalid_count': 0,
            'error_types': {},
            'classification_stats': {
                'coffee_count': 0,
                'equipment_count': 0,
                'classification_methods': {}
            }
        }
    
    async def validate_artifact(self, artifact_data: Dict[str, Any], metadata_only: bool = False) -> ValidationResult:
        """
        Validate a single artifact against the canonical schema.
        
        Args:
            artifact_data: Raw artifact data to validate
            metadata_only: If True, skip classification (for price-only runs)
            
        Returns:
            ValidationResult with validation status and details
        """
        try:
            # Validate using Pydantic model
            validated_artifact = ArtifactModel(**artifact_data)
            
            # Extract artifact ID for tracking
            artifact_id = self._extract_artifact_id(artifact_data)
            
            # Perform coffee classification (skip for price-only runs)
            if not metadata_only:
                classification_result = await self._classify_product(artifact_data, validated_artifact)
                if classification_result:
                    # Update the validated artifact with classification
                    if not validated_artifact.normalization:
                        from .models import NormalizationModel
                        validated_artifact.normalization = NormalizationModel()
                    validated_artifact.normalization.is_coffee = classification_result.is_coffee
                    
                    # Update classification stats
                    self._update_classification_stats(classification_result)
            
            logger.info(
                "Artifact validation successful",
                artifact_id=artifact_id,
                source=artifact_data.get('source'),
                roaster_domain=artifact_data.get('roaster_domain'),
                is_coffee=validated_artifact.normalization.is_coffee if validated_artifact.normalization else None
            )
            
            self.validation_stats['total_validated'] += 1
            self.validation_stats['valid_count'] += 1
            
            return ValidationResult(
                is_valid=True,
                artifact_data=validated_artifact.model_dump(),
                artifact_id=artifact_id
            )
            
        except ValidationError as e:
            # Extract detailed validation errors
            errors = self._format_validation_errors(e)
            
            artifact_id = self._extract_artifact_id(artifact_data)
            
            logger.error(
                "Artifact validation failed",
                artifact_id=artifact_id,
                error_count=len(errors),
                errors=errors[:3],  # Log first 3 errors
                source=artifact_data.get('source'),
                roaster_domain=artifact_data.get('roaster_domain')
            )
            
            self.validation_stats['total_validated'] += 1
            self.validation_stats['invalid_count'] += 1
            
            # Track error types for analytics
            for error in errors:
                error_type = error.split(':')[0] if ':' in error else 'unknown'
                self.validation_stats['error_types'][error_type] = \
                    self.validation_stats['error_types'].get(error_type, 0) + 1
            
            return ValidationResult(
                is_valid=False,
                artifact_data=artifact_data,
                errors=errors,
                artifact_id=artifact_id
            )
            
        except Exception as e:
            # Handle unexpected errors
            artifact_id = self._extract_artifact_id(artifact_data)
            
            logger.error(
                "Unexpected validation error",
                artifact_id=artifact_id,
                error=str(e),
                source=artifact_data.get('source'),
                roaster_domain=artifact_data.get('roaster_domain')
            )
            
            self.validation_stats['total_validated'] += 1
            self.validation_stats['invalid_count'] += 1
            
            return ValidationResult(
                is_valid=False,
                artifact_data=artifact_data,
                errors=[f"Unexpected error: {str(e)}"],
                artifact_id=artifact_id
            )
    
    async def validate_from_storage(
        self,
        roaster_id: str,
        platform: str,
        response_filename: str
    ) -> ValidationResult:
        """
        Validate artifact from A.2 storage system.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type
            response_filename: Response filename from storage
            
        Returns:
            ValidationResult with validation status
        """
        try:
            # Read artifact data from storage
            artifact_data = self.storage_reader.read_artifact(
                roaster_id=roaster_id,
                platform=platform,
                response_filename=response_filename
            )
            
            if not artifact_data:
                return ValidationResult(
                    is_valid=False,
                    artifact_data={},
                    errors=["Failed to read artifact from storage"]
                )
            
            # Validate the artifact
            return await self.validate_artifact(artifact_data)
            
        except Exception as e:
            logger.error(
                "Failed to validate artifact from storage",
                roaster_id=roaster_id,
                platform=platform,
                response_filename=response_filename,
                error=str(e)
            )
            
            return ValidationResult(
                is_valid=False,
                artifact_data={},
                errors=[f"Storage read error: {str(e)}"]
            )
    
    async def validate_batch(self, artifacts: List[Dict[str, Any]], metadata_only: bool = False) -> List[ValidationResult]:
        """
        Validate multiple artifacts in batch.
        
        Args:
            artifacts: List of artifact data to validate
            metadata_only: If True, skip classification (for price-only runs)
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        
        for artifact_data in artifacts:
            result = await self.validate_artifact(artifact_data, metadata_only=metadata_only)
            results.append(result)
        
        logger.info(
            "Batch validation completed",
            total_artifacts=len(artifacts),
            valid_count=sum(1 for r in results if r.is_valid),
            invalid_count=sum(1 for r in results if not r.is_valid),
            metadata_only=metadata_only,
            classification_stats=self.validation_stats['classification_stats']
        )
        
        return results
    
    async def _classify_product(self, artifact_data: Dict[str, Any], validated_artifact: ArtifactModel) -> Optional[Any]:
        """
        Classify product as coffee or equipment.
        
        Args:
            artifact_data: Raw artifact data
            validated_artifact: Validated artifact model
            
        Returns:
            ClassificationResult or None if classification fails
        """
        try:
            # Extract product data for classification
            product_data = artifact_data.get('product', {})
            source = artifact_data.get('source', 'unknown').lower()
            
            # Map source to platform for classification
            platform = 'shopify' if source == 'shopify' else 'woo'
            
            # Perform classification
            classification_result = await self.classification_parser.classify_product(product_data, platform)
            
            logger.info(
                "Product classification completed",
                is_coffee=classification_result.is_coffee,
                confidence=classification_result.confidence,
                method=classification_result.method,
                reasoning=classification_result.reasoning
            )
            
            return classification_result
            
        except Exception as e:
            logger.error(
                "Product classification failed",
                error=str(e),
                artifact_id=self._extract_artifact_id(artifact_data)
            )
            return None
    
    def _update_classification_stats(self, classification_result: Any):
        """Update classification statistics."""
        try:
            if classification_result.is_coffee:
                self.validation_stats['classification_stats']['coffee_count'] += 1
            else:
                self.validation_stats['classification_stats']['equipment_count'] += 1
            
            # Track classification methods
            method = classification_result.method
            self.validation_stats['classification_stats']['classification_methods'][method] = \
                self.validation_stats['classification_stats']['classification_methods'].get(method, 0) + 1
                
        except Exception as e:
            logger.error(f"Failed to update classification stats: {e}")
    
    def _extract_artifact_id(self, artifact_data: Dict[str, Any]) -> Optional[str]:
        """Extract artifact ID from artifact data."""
        # Try audit.artifact_id first
        audit = artifact_data.get('audit', {})
        if isinstance(audit, dict) and 'artifact_id' in audit:
            return audit['artifact_id']
        
        # Try collector_meta.job_id as fallback
        collector_meta = artifact_data.get('collector_meta', {})
        if isinstance(collector_meta, dict) and 'job_id' in collector_meta:
            return collector_meta['job_id']
        
        # Generate ID from available data
        source = artifact_data.get('source', 'unknown')
        roaster_domain = artifact_data.get('roaster_domain', 'unknown')
        timestamp = artifact_data.get('scraped_at', 'unknown')
        
        return f"{source}_{roaster_domain}_{timestamp}"
    
    def _format_validation_errors(self, validation_error: ValidationError) -> List[str]:
        """
        Format Pydantic validation errors into readable messages.
        
        Args:
            validation_error: Pydantic ValidationError
            
        Returns:
            List of formatted error messages
        """
        errors = []
        
        for error in validation_error.errors():
            field_path = " -> ".join(str(loc) for loc in error['loc'])
            error_type = error['type']
            error_msg = error['msg']
            
            # Format based on error type
            if error_type == 'missing':
                errors.append(f"Missing required field: {field_path}")
            elif error_type == 'type_error':
                expected_type = error.get('ctx', {}).get('expected_type', 'unknown')
                errors.append(f"Invalid type for {field_path}: expected {expected_type}")
            elif error_type == 'value_error':
                errors.append(f"Invalid value for {field_path}: {error_msg}")
            elif error_type == 'enum':
                allowed_values = error.get('ctx', {}).get('enum_values', [])
                errors.append(f"Invalid enum value for {field_path}: must be one of {allowed_values}")
            else:
                errors.append(f"Validation error in {field_path}: {error_msg}")
        
        return errors
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics.
        
        Returns:
            Dictionary with validation statistics
        """
        stats = self.validation_stats.copy()
        
        if stats['total_validated'] > 0:
            stats['valid_rate'] = stats['valid_count'] / stats['total_validated']
            stats['invalid_rate'] = stats['invalid_count'] / stats['total_validated']
        else:
            stats['valid_rate'] = 0.0
            stats['invalid_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset validation statistics."""
        self.validation_stats = {
            'total_validated': 0,
            'valid_count': 0,
            'invalid_count': 0,
            'error_types': {}
        }
