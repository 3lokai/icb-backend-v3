"""
Tests for validation pipeline.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timezone

from src.validator.validation_pipeline import ValidationPipeline
from src.validator.artifact_validator import ArtifactValidator, ValidationResult
from src.validator.storage_reader import StorageReader
from .fixtures import get_valid_artifact_fixture, get_invalid_artifact_fixtures


class TestValidationPipeline:
    """Test cases for ValidationPipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage_reader = Mock(spec=StorageReader)
        self.mock_validator = Mock(spec=ArtifactValidator)
        self.pipeline = ValidationPipeline(
            storage_reader=self.mock_storage_reader,
            validator=self.mock_validator
        )
        
        self.valid_artifact = get_valid_artifact_fixture()
        self.invalid_artifacts = get_invalid_artifact_fixtures()
    
    def test_process_storage_artifacts_success(self):
        """Test successful processing of storage artifacts."""
        # Mock validator to return valid results
        valid_result = ValidationResult(
            is_valid=True,
            artifact_data=self.valid_artifact,
            artifact_id="test-artifact-1"
        )
        
        self.mock_validator.validate_from_storage.return_value = valid_result
        
        # Mock storage reader
        self.mock_storage_reader.read_artifact.return_value = self.valid_artifact
        
        results = self.pipeline.process_storage_artifacts(
            roaster_id="test_roaster",
            platform="shopify",
            response_filenames=["test1.json", "test2.json"]
        )
        
        assert len(results) == 2
        assert all(result.is_valid for result in results)
        assert self.pipeline.pipeline_stats['total_processed'] == 2
        assert self.pipeline.pipeline_stats['valid_count'] == 2
        assert self.pipeline.pipeline_stats['invalid_count'] == 0
    
    def test_process_storage_artifacts_with_invalid(self):
        """Test processing storage artifacts with invalid results."""
        # Mock validator to return mixed results
        valid_result = ValidationResult(
            is_valid=True,
            artifact_data=self.valid_artifact,
            artifact_id="test-artifact-1"
        )
        
        invalid_result = ValidationResult(
            is_valid=False,
            artifact_data={},
            errors=["Validation error"],
            artifact_id="test-artifact-2"
        )
        
        self.mock_validator.validate_from_storage.side_effect = [valid_result, invalid_result]
        
        results = self.pipeline.process_storage_artifacts(
            roaster_id="test_roaster",
            platform="shopify",
            response_filenames=["test1.json", "test2.json"]
        )
        
        assert len(results) == 2
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert self.pipeline.pipeline_stats['total_processed'] == 2
        assert self.pipeline.pipeline_stats['valid_count'] == 1
        assert self.pipeline.pipeline_stats['invalid_count'] == 1
    
    def test_process_storage_artifacts_with_errors(self):
        """Test processing storage artifacts with pipeline errors."""
        # Mock validator to raise exception
        self.mock_validator.validate_from_storage.side_effect = Exception("Validation error")
        
        results = self.pipeline.process_storage_artifacts(
            roaster_id="test_roaster",
            platform="shopify",
            response_filenames=["test1.json"]
        )
        
        assert len(results) == 1
        assert results[0].is_valid is False
        assert "Pipeline error" in results[0].errors[0]
        assert self.pipeline.pipeline_stats['error_count'] == 1
    
    def test_process_artifact_batch(self):
        """Test processing a batch of artifacts."""
        # Mock validator to return mixed results
        valid_result = ValidationResult(
            is_valid=True,
            artifact_data=self.valid_artifact,
            artifact_id="test-artifact-1"
        )
        
        invalid_result = ValidationResult(
            is_valid=False,
            artifact_data={},
            errors=["Validation error"],
            artifact_id="test-artifact-2"
        )
        
        self.mock_validator.validate_batch.return_value = [valid_result, invalid_result]
        
        artifacts = [self.valid_artifact, self.invalid_artifacts["missing_required_fields"]]
        results = self.pipeline.process_artifact_batch(artifacts)
        
        assert len(results) == 2
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert self.pipeline.pipeline_stats['total_processed'] == 2
        assert self.pipeline.pipeline_stats['valid_count'] == 1
        assert self.pipeline.pipeline_stats['invalid_count'] == 1
    
    def test_persist_invalid_artifact(self):
        """Test persistence of invalid artifacts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create pipeline with temp directory
            pipeline = ValidationPipeline()
            
            # Create invalid result
            invalid_result = ValidationResult(
                is_valid=False,
                artifact_data={"test": "data"},
                errors=["Validation error"],
                artifact_id="test-artifact-1"
            )
            
            # Mock the invalid artifacts directory
            with patch('src.validator.validation_pipeline.Path') as mock_path_class:
                mock_invalid_dir = Mock()
                mock_invalid_dir.mkdir.return_value = None
                mock_invalid_dir.__truediv__ = Mock(return_value=mock_invalid_dir)
                mock_path_class.return_value = mock_invalid_dir
                
                # Mock file operations
                with patch('builtins.open', mock_open()) as mock_file:
                    pipeline._persist_invalid_artifact(invalid_result)
                    
                    # Verify file was written
                    mock_file.assert_called_once()
                    mock_invalid_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    def test_get_pipeline_stats(self):
        """Test getting pipeline statistics."""
        # Set up some stats
        self.pipeline.pipeline_stats['total_processed'] = 10
        self.pipeline.pipeline_stats['valid_count'] = 8
        self.pipeline.pipeline_stats['invalid_count'] = 2
        self.pipeline.pipeline_stats['error_count'] = 0
        self.pipeline.pipeline_stats['start_time'] = datetime.now(timezone.utc)
        self.pipeline.pipeline_stats['end_time'] = datetime.now(timezone.utc)
        
        # Mock validator stats
        self.mock_validator.get_validation_stats.return_value = {
            'total_validated': 10,
            'valid_count': 8,
            'invalid_count': 2,
            'valid_rate': 0.8,
            'invalid_rate': 0.2
        }
        
        stats = self.pipeline.get_pipeline_stats()
        
        assert stats['total_processed'] == 10
        assert stats['valid_count'] == 8
        assert stats['invalid_count'] == 2
        assert stats['success_rate'] == 0.8
        assert stats['error_rate'] == 0.0
        assert 'validator_stats' in stats
        assert 'processing_time_seconds' in stats
    
    def test_reset_pipeline_stats(self):
        """Test resetting pipeline statistics."""
        # Set up some stats
        self.pipeline.pipeline_stats['total_processed'] = 10
        self.pipeline.pipeline_stats['valid_count'] = 8
        self.pipeline.pipeline_stats['invalid_count'] = 2
        
        # Reset stats
        self.pipeline.reset_pipeline_stats()
        
        assert self.pipeline.pipeline_stats['total_processed'] == 0
        assert self.pipeline.pipeline_stats['valid_count'] == 0
        assert self.pipeline.pipeline_stats['invalid_count'] == 0
        assert self.pipeline.pipeline_stats['error_count'] == 0
        
        # Verify validator stats were also reset
        self.mock_validator.reset_stats.assert_called_once()
    
    def test_pipeline_with_real_components(self):
        """Test pipeline with real validator and storage reader components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create real components
            storage_reader = StorageReader(base_storage_path=temp_dir)
            validator = ArtifactValidator(storage_reader=storage_reader)
            pipeline = ValidationPipeline(
                storage_reader=storage_reader,
                validator=validator
            )
            
            # Create test artifacts
            artifacts = [
                self.valid_artifact,
                self.invalid_artifacts["missing_required_fields"]
            ]
            
            # Process batch
            results = pipeline.process_artifact_batch(artifacts)
            
            assert len(results) == 2
            assert results[0].is_valid is True
            assert results[1].is_valid is False
            
            # Check stats
            stats = pipeline.get_pipeline_stats()
            assert stats['total_processed'] == 2
            assert stats['valid_count'] == 1
            assert stats['invalid_count'] == 1
            assert stats['success_rate'] == 0.5
