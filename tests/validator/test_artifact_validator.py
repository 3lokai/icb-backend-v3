"""
Tests for artifact validator.
"""

import pytest
from pytest import mark
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.validator.artifact_validator import ArtifactValidator, ValidationResult
from src.validator.storage_reader import StorageReader
from .fixtures import (
    get_valid_artifact_fixture,
    get_invalid_artifact_fixtures,
    get_edge_case_fixtures
)


class TestArtifactValidator:
    """Test cases for ArtifactValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ArtifactValidator()
        self.valid_artifact = get_valid_artifact_fixture()
        self.invalid_artifacts = get_invalid_artifact_fixtures()
        self.edge_cases = get_edge_case_fixtures()
    
    @pytest.mark.asyncio

    
    async def test_validate_valid_artifact(self):
        """Test validation of valid artifact."""
        result = await self.validator.validate_artifact(self.valid_artifact)
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.artifact_data is not None
        assert result.artifact_id is not None
        assert result.validated_at is not None
    
    @pytest.mark.asyncio

    
    async def test_validate_missing_required_fields(self):
        """Test validation of artifact with missing required fields."""
        invalid_artifact = self.invalid_artifacts["missing_required_fields"]
        result = await self.validator.validate_artifact(invalid_artifact)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("Missing required field" in error for error in result.errors)
    
    @pytest.mark.asyncio

    
    async def test_validate_invalid_source_enum(self):
        """Test validation of artifact with invalid source enum."""
        invalid_artifact = self.invalid_artifacts["invalid_source_enum"]
        result = await self.validator.validate_artifact(invalid_artifact)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("Invalid enum value" in error for error in result.errors)
    
    @pytest.mark.asyncio

    
    async def test_validate_invalid_roaster_domain(self):
        """Test validation of artifact with invalid roaster domain."""
        invalid_artifact = self.invalid_artifacts["invalid_roaster_domain"]
        result = await self.validator.validate_artifact(invalid_artifact)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("roaster_domain" in error for error in result.errors)
    
    @pytest.mark.asyncio

    
    async def test_validate_invalid_timestamp(self):
        """Test validation of artifact with invalid timestamp."""
        invalid_artifact = self.invalid_artifacts["invalid_timestamp"]
        result = await self.validator.validate_artifact(invalid_artifact)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("scraped_at" in error for error in result.errors)
    
    @pytest.mark.asyncio

    
    async def test_validate_missing_product_fields(self):
        """Test validation of artifact with missing product fields."""
        invalid_artifact = self.invalid_artifacts["missing_product_required_fields"]
        result = await self.validator.validate_artifact(invalid_artifact)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("Missing required field" in error for error in result.errors)
    
    @pytest.mark.asyncio

    
    async def test_validate_invalid_variant_data(self):
        """Test validation of artifact with invalid variant data."""
        invalid_artifact = self.invalid_artifacts["invalid_variant_data"]
        result = await self.validator.validate_artifact(invalid_artifact)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("variants" in error for error in result.errors)
    
    @pytest.mark.asyncio

    
    async def test_validate_invalid_enum_values(self):
        """Test validation of artifact with invalid enum values."""
        invalid_artifact = self.invalid_artifacts["invalid_enum_values"]
        result = await self.validator.validate_artifact(invalid_artifact)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("Invalid enum value" in error for error in result.errors)
    
    @pytest.mark.asyncio

    
    async def test_validate_invalid_sensory_params(self):
        """Test validation of artifact with invalid sensory parameters."""
        invalid_artifact = self.invalid_artifacts["invalid_sensory_params"]
        result = await self.validator.validate_artifact(invalid_artifact)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("sensory_params" in error for error in result.errors)
    
    @pytest.mark.asyncio

    
    async def test_validate_null_values(self):
        """Test validation of artifact with null values."""
        edge_case = self.edge_cases["null_values"]
        result = await self.validator.validate_artifact(edge_case)
        
        # Null values should be handled gracefully
        assert result.is_valid is True
        assert result.errors == []
    
    @pytest.mark.asyncio

    
    async def test_validate_empty_arrays(self):
        """Test validation of artifact with empty arrays."""
        edge_case = self.edge_cases["empty_arrays"]
        result = await self.validator.validate_artifact(edge_case)
        
        # Empty arrays should be valid
        assert result.is_valid is True
        assert result.errors == []
    
    @pytest.mark.asyncio

    
    async def test_validate_type_coercion(self):
        """Test validation of artifact with type coercion."""
        edge_case = self.edge_cases["type_coercion"]
        result = await self.validator.validate_artifact(edge_case)
        
        # Type coercion should work for compatible types
        assert result.is_valid is True
        assert result.errors == []
    
    @pytest.mark.asyncio

    
    async def test_validate_batch(self):
        """Test batch validation of multiple artifacts."""
        artifacts = [
            self.valid_artifact,
            self.invalid_artifacts["missing_required_fields"],
            self.valid_artifact
        ]
        
        results = await self.validator.validate_batch(artifacts)
        
        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert results[2].is_valid is True
    
    @pytest.mark.asyncio

    
    async def test_validation_stats(self):
        """Test validation statistics tracking."""
        # Reset stats
        self.validator.reset_stats()
        
        # Validate some artifacts
        await self.validator.validate_artifact(self.valid_artifact)
        await self.validator.validate_artifact(self.invalid_artifacts["missing_required_fields"])
        await self.validator.validate_artifact(self.valid_artifact)
        
        stats = self.validator.get_validation_stats()
        
        assert stats['total_validated'] == 3
        assert stats['valid_count'] == 2
        assert stats['invalid_count'] == 1
        assert stats['valid_rate'] == 2/3
        assert stats['invalid_rate'] == 1/3
    
    @pytest.mark.asyncio

    
    async def test_artifact_id_extraction(self):
        """Test artifact ID extraction from various sources."""
        # Test with audit.artifact_id
        artifact_with_audit = self.valid_artifact.copy()
        artifact_with_audit['audit'] = {'artifact_id': 'test-artifact-123'}
        
        result = await self.validator.validate_artifact(artifact_with_audit)
        assert result.artifact_id == 'test-artifact-123'
        
        # Test with collector_meta.job_id
        artifact_with_job = self.valid_artifact.copy()
        artifact_with_job['collector_meta'] = {'job_id': 'job-456'}
        artifact_with_job['audit'] = None
        
        result = await self.validator.validate_artifact(artifact_with_job)
        assert result.artifact_id == 'job-456'
        
        # Test with generated ID
        artifact_minimal = {
            'source': 'shopify',
            'roaster_domain': 'example.com',
            'scraped_at': '2025-01-12T10:00:00Z',
            'product': {
                'platform_product_id': '123',
                'title': 'Test',
                'source_url': 'https://example.com',
                'variants': [{'platform_variant_id': 'v-1', 'price': '10.00'}]
            }
        }
        
        result = await self.validator.validate_artifact(artifact_minimal)
        assert result.artifact_id is not None
        assert 'shopify' in result.artifact_id
        assert 'example.com' in result.artifact_id


class TestArtifactValidatorWithStorage:
    """Test cases for ArtifactValidator with storage integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage_reader = Mock(spec=StorageReader)
        self.validator = ArtifactValidator(storage_reader=self.mock_storage_reader)
        self.valid_artifact = get_valid_artifact_fixture()
    
    @pytest.mark.asyncio

    
    async def test_validate_from_storage_success(self):
        """Test successful validation from storage."""
        # Mock storage reader to return valid artifact
        self.mock_storage_reader.read_artifact.return_value = self.valid_artifact
        
        result = await self.validator.validate_from_storage(
            roaster_id="test_roaster",
            platform="shopify",
            response_filename="test_response.json"
        )
        
        assert result.is_valid is True
        assert result.errors == []
        self.mock_storage_reader.read_artifact.assert_called_once_with(
            roaster_id="test_roaster",
            platform="shopify",
            response_filename="test_response.json"
        )
    
    @pytest.mark.asyncio

    
    async def test_validate_from_storage_not_found(self):
        """Test validation when artifact not found in storage."""
        # Mock storage reader to return None
        self.mock_storage_reader.read_artifact.return_value = None
        
        result = await self.validator.validate_from_storage(
            roaster_id="test_roaster",
            platform="shopify",
            response_filename="nonexistent.json"
        )
        
        assert result.is_valid is False
        assert "Failed to read artifact from storage" in result.errors
    
    @pytest.mark.asyncio

    
    async def test_validate_from_storage_error(self):
        """Test validation when storage read fails."""
        # Mock storage reader to raise exception
        self.mock_storage_reader.read_artifact.side_effect = Exception("Storage error")
        
        result = await self.validator.validate_from_storage(
            roaster_id="test_roaster",
            platform="shopify",
            response_filename="error_response.json"
        )
        
        assert result.is_valid is False
        assert "Storage read error" in result.errors[0]
