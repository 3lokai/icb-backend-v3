"""
Integration tests for raw artifact persistence with A.4 RPC upsert flow.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from src.validator.integration_service import ValidatorIntegrationService
from src.validator.models import ArtifactModel, AuditModel, NormalizationModel, CollectorSignalsModel, ProductModel, VariantModel
from src.validator.validation_pipeline import ValidationResult


class TestIntegrationPersistence:
    """Integration tests for raw artifact persistence."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return Mock()
    
    @pytest.fixture
    def integration_service(self, mock_supabase_client):
        """Create integration service with mocked dependencies."""
        with patch('src.validator.integration_service.StorageReader'), \
             patch('src.validator.integration_service.ArtifactValidator'), \
             patch('src.validator.integration_service.ValidationPipeline'), \
             patch('src.validator.integration_service.DatabaseIntegration'), \
             patch('src.validator.integration_service.RPCClient'), \
             patch('src.validator.integration_service.ArtifactMapper'), \
             patch('src.validator.integration_service.RawArtifactPersistence'):
            
            service = ValidatorIntegrationService(supabase_client=mock_supabase_client)
            return service
    
    @pytest.fixture
    def sample_validation_results(self):
        """Create sample validation results for testing."""
        artifact1 = ArtifactModel(
            source="shopify",
            roaster_domain="example.com",
            scraped_at="2025-01-12T10:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="123",
                title="Test Coffee 1",
                source_url="https://example.com/coffee1",
                variants=[
                    VariantModel(
                        platform_variant_id="var-123",
                        price="15.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="content-hash-123",
                raw_payload_hash="raw-hash-456"
            ),
            collector_signals=CollectorSignalsModel(
                response_status=200,
                download_time_ms=100
            ),
            audit=AuditModel(
                artifact_id="artifact-123",
                created_at="2025-01-12T10:00:00Z",
                collected_by="test-collector"
            )
        )
        
        artifact2 = ArtifactModel(
            source="woocommerce",
            roaster_domain="example2.com",
            scraped_at="2025-01-12T11:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="456",
                title="Test Coffee 2",
                source_url="https://example.com/coffee2",
                variants=[
                    VariantModel(
                        platform_variant_id="var-456",
                        price="19.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="content-hash-789",
                raw_payload_hash="raw-hash-012"
            ),
            collector_signals=CollectorSignalsModel(
                response_status=200,
                download_time_ms=150
            ),
            audit=AuditModel(
                artifact_id="artifact-456",
                created_at="2025-01-12T11:00:00Z",
                collected_by="test-collector"
            )
        )
        
        return [
            ValidationResult(
                is_valid=True,
                artifact_data=artifact1.model_dump(),
                errors=[],
                warnings=[],
                artifact_id="artifact-123"
            ),
            ValidationResult(
                is_valid=True,
                artifact_data=artifact2.model_dump(),
                errors=[],
                warnings=[],
                artifact_id="artifact-456"
            )
        ]
    
    def test_persist_raw_artifacts_success(self, integration_service, sample_validation_results):
        """Test successful raw artifact persistence for valid results."""
        # Mock the raw artifact persistence service
        mock_persistence = integration_service.raw_artifact_persistence
        mock_persistence.verify_hash_integrity.return_value = True
        mock_persistence.persist_raw_artifact.return_value = (True, None)
        
        # Call the private method
        results = integration_service._persist_raw_artifacts(
            validation_results=sample_validation_results,
            roaster_id="test-roaster",
            platform="shopify"
        )
        
        # Verify results
        assert results['total_artifacts'] == 2
        assert results['successful_persistence'] == 2
        assert results['failed_persistence'] == 0
        assert len(results['persistence_errors']) == 0
        
        # Verify methods were called
        assert mock_persistence.verify_hash_integrity.call_count == 2
        assert mock_persistence.persist_raw_artifact.call_count == 2
    
    def test_persist_raw_artifacts_with_invalid_artifacts(self, integration_service):
        """Test raw artifact persistence with invalid artifacts."""
        # Create validation results with invalid artifacts
        invalid_artifact = ArtifactModel(
            source="shopify",
            roaster_domain="example.com",
            scraped_at="2025-01-12T10:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="123",
                title="Test Coffee",
                source_url="https://example.com/coffee",
                variants=[
                    VariantModel(
                        platform_variant_id="var-123",
                        price="15.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="content-hash-123",
                raw_payload_hash="raw-hash-456"
            ),
            collector_signals=None,
            audit=AuditModel(
                artifact_id="artifact-123",
                created_at="2025-01-12T10:00:00Z",
                collected_by="test-collector"
            )
        )
        
        validation_results = [
            ValidationResult(
                is_valid=False,  # Invalid artifact
                artifact_data=invalid_artifact.model_dump(),
                errors=["Missing required field"],
                warnings=[],
                artifact_id="artifact-123"
            )
        ]
        
        # Mock the raw artifact persistence service
        mock_persistence = integration_service.raw_artifact_persistence
        
        # Call the private method
        results = integration_service._persist_raw_artifacts(
            validation_results=validation_results,
            roaster_id="test-roaster",
            platform="shopify"
        )
        
        # Verify results - invalid artifacts should be skipped
        assert results['total_artifacts'] == 1
        assert results['successful_persistence'] == 0
        assert results['failed_persistence'] == 0
        assert len(results['persistence_errors']) == 0
        
        # Verify methods were not called for invalid artifacts
        mock_persistence.verify_hash_integrity.assert_not_called()
        mock_persistence.persist_raw_artifact.assert_not_called()
    
    def test_persist_raw_artifacts_hash_integrity_failure(self, integration_service, sample_validation_results):
        """Test raw artifact persistence with hash integrity failures."""
        # Mock the raw artifact persistence service
        mock_persistence = integration_service.raw_artifact_persistence
        mock_persistence.verify_hash_integrity.return_value = False  # Hash integrity failure
        
        # Call the private method
        results = integration_service._persist_raw_artifacts(
            validation_results=sample_validation_results,
            roaster_id="test-roaster",
            platform="shopify"
        )
        
        # Verify results
        assert results['total_artifacts'] == 2
        assert results['successful_persistence'] == 0
        assert results['failed_persistence'] == 2
        assert len(results['persistence_errors']) == 2
        assert "Hash integrity check failed" in results['persistence_errors'][0]
        
        # Verify methods were called
        assert mock_persistence.verify_hash_integrity.call_count == 2
        mock_persistence.persist_raw_artifact.assert_not_called()  # Should not be called due to hash failure
    
    def test_persist_raw_artifacts_persistence_failure(self, integration_service, sample_validation_results):
        """Test raw artifact persistence with persistence failures."""
        # Mock the raw artifact persistence service
        mock_persistence = integration_service.raw_artifact_persistence
        mock_persistence.verify_hash_integrity.return_value = True
        mock_persistence.persist_raw_artifact.return_value = (False, "Database error")
        
        # Call the private method
        results = integration_service._persist_raw_artifacts(
            validation_results=sample_validation_results,
            roaster_id="test-roaster",
            platform="shopify"
        )
        
        # Verify results
        assert results['total_artifacts'] == 2
        assert results['successful_persistence'] == 0
        assert results['failed_persistence'] == 2
        assert len(results['persistence_errors']) == 2
        assert "Failed to persist" in results['persistence_errors'][0]
        assert "Database error" in results['persistence_errors'][0]
    
    def test_persist_raw_artifacts_exception_handling(self, integration_service, sample_validation_results):
        """Test raw artifact persistence with exception handling."""
        # Mock the raw artifact persistence service to raise exception
        mock_persistence = integration_service.raw_artifact_persistence
        mock_persistence.verify_hash_integrity.side_effect = Exception("Unexpected error")
        
        # Call the private method
        results = integration_service._persist_raw_artifacts(
            validation_results=sample_validation_results,
            roaster_id="test-roaster",
            platform="shopify"
        )
        
        # Verify results
        assert results['total_artifacts'] == 2
        assert results['successful_persistence'] == 0
        assert results['failed_persistence'] == 2
        assert len(results['persistence_errors']) == 2
        assert "Unexpected error persisting" in results['persistence_errors'][0]
    
    def test_persist_raw_artifacts_mixed_results(self, integration_service):
        """Test raw artifact persistence with mixed success/failure results."""
        # Create one valid and one invalid artifact
        valid_artifact = ArtifactModel(
            source="shopify",
            roaster_domain="example.com",
            scraped_at="2025-01-12T10:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="123",
                title="Test Coffee",
                source_url="https://example.com/coffee",
                variants=[
                    VariantModel(
                        platform_variant_id="var-123",
                        price="15.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="content-hash-123",
                raw_payload_hash="raw-hash-456"
            ),
            collector_signals=None,
            audit=AuditModel(
                artifact_id="artifact-123",
                created_at="2025-01-12T10:00:00Z",
                collected_by="test-collector"
            )
        )
        
        invalid_artifact = ArtifactModel(
            source="woocommerce",
            roaster_domain="example2.com",
            scraped_at="2025-01-12T11:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="456",
                title="Test Coffee 2",
                source_url="https://example.com/coffee2",
                variants=[
                    VariantModel(
                        platform_variant_id="var-456",
                        price="19.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="content-hash-789",
                raw_payload_hash="raw-hash-012"
            ),
            collector_signals=None,
            audit=AuditModel(
                artifact_id="artifact-456",
                created_at="2025-01-12T11:00:00Z",
                collected_by="test-collector"
            )
        )
        
        validation_results = [
            ValidationResult(
                is_valid=True,
                artifact_data=valid_artifact.model_dump(),
                errors=[],
                warnings=[],
                artifact_id="artifact-123"
            ),
            ValidationResult(
                is_valid=False,  # Invalid artifact
                artifact_data=invalid_artifact.model_dump(),
                errors=["Missing required field"],
                warnings=[],
                artifact_id="artifact-456"
            )
        ]
        
        # Mock the raw artifact persistence service
        mock_persistence = integration_service.raw_artifact_persistence
        mock_persistence.verify_hash_integrity.return_value = True
        mock_persistence.persist_raw_artifact.return_value = (True, None)
        
        # Call the private method
        results = integration_service._persist_raw_artifacts(
            validation_results=validation_results,
            roaster_id="test-roaster",
            platform="shopify"
        )
        
        # Verify results - only valid artifacts should be processed
        assert results['total_artifacts'] == 2
        assert results['successful_persistence'] == 1  # Only valid artifact
        assert results['failed_persistence'] == 0
        assert len(results['persistence_errors']) == 0
        
        # Verify methods were called only for valid artifact
        assert mock_persistence.verify_hash_integrity.call_count == 1
        assert mock_persistence.persist_raw_artifact.call_count == 1

