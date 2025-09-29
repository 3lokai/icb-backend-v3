"""
Tests for content hash generation service.
"""

import pytest
from src.parser.content_hash import ContentHashService, HashResult
from src.config.hash_config import HashConfig


class TestContentHashService:
    """Test cases for ContentHashService."""
    
    def test_generate_hashes_basic(self):
        """Test basic hash generation."""
        config = HashConfig()
        service = ContentHashService(config)
        
        artifact = {
            'title': 'Test Coffee',
            'description': 'A great coffee',
            'weight_g': 250,
            'roast_level': 'medium',
            'process': 'washed',
            'grind_type': 'whole_bean',
            'species': 'arabica'
        }
        
        result = service.generate_hashes(artifact)
        
        assert isinstance(result, HashResult)
        assert result.content_hash is not None
        assert result.raw_hash is not None
        assert result.algorithm == "sha256"
        assert len(result.content_hash) == 64  # SHA256 hex length
        assert len(result.raw_hash) == 64
    
    def test_generate_hashes_empty_artifact(self):
        """Test hash generation with empty artifact."""
        config = HashConfig()
        service = ContentHashService(config)
        
        artifact = {}
        result = service.generate_hashes(artifact)
        
        assert isinstance(result, HashResult)
        assert result.content_hash is not None
        assert result.raw_hash is not None
    
    def test_generate_hashes_batch(self):
        """Test batch hash generation."""
        config = HashConfig()
        service = ContentHashService(config)
        
        artifacts = [
            {'title': 'Coffee 1', 'description': 'First coffee'},
            {'title': 'Coffee 2', 'description': 'Second coffee'},
            {'title': 'Coffee 3', 'description': 'Third coffee'}
        ]
        
        results = service.generate_hashes_batch(artifacts)
        
        assert len(results) == 3
        assert all(isinstance(r, HashResult) for r in results)
        assert all(r.content_hash for r in results)
        assert all(r.raw_hash for r in results)
    
    def test_hash_consistency(self):
        """Test that identical artifacts produce identical hashes."""
        config = HashConfig()
        service = ContentHashService(config)
        
        artifact = {
            'title': 'Test Coffee',
            'description': 'A great coffee',
            'weight_g': 250
        }
        
        result1 = service.generate_hashes(artifact)
        result2 = service.generate_hashes(artifact)
        
        assert result1.content_hash == result2.content_hash
        assert result1.raw_hash == result2.raw_hash
    
    def test_hash_difference(self):
        """Test that different artifacts produce different hashes."""
        config = HashConfig()
        service = ContentHashService(config)
        
        artifact1 = {'title': 'Coffee 1', 'description': 'First coffee'}
        artifact2 = {'title': 'Coffee 2', 'description': 'Second coffee'}
        
        result1 = service.generate_hashes(artifact1)
        result2 = service.generate_hashes(artifact2)
        
        assert result1.content_hash != result2.content_hash
        assert result1.raw_hash != result2.raw_hash
    
    def test_collision_detection(self):
        """Test hash collision detection."""
        config = HashConfig()
        service = ContentHashService(config)
        
        # Generate hash for first artifact
        artifact1 = {'title': 'Coffee 1', 'description': 'First coffee'}
        result1 = service.generate_hashes(artifact1)
        
        # Check collision with same hash
        existing_hashes = [result1.content_hash]
        collision = service.detect_hash_collision(result1.content_hash, existing_hashes)
        assert collision is True
        
        # Check collision with different hash
        artifact2 = {'title': 'Coffee 2', 'description': 'Second coffee'}
        result2 = service.generate_hashes(artifact2)
        collision = service.detect_hash_collision(result2.content_hash, existing_hashes)
        assert collision is False
    
    def test_md5_algorithm(self):
        """Test MD5 hash algorithm."""
        config = HashConfig(hash_algorithm="md5")
        service = ContentHashService(config)
        
        artifact = {'title': 'Test Coffee', 'description': 'A great coffee'}
        result = service.generate_hashes(artifact)
        
        assert result.algorithm == "md5"
        assert len(result.content_hash) == 32  # MD5 hex length
        assert len(result.raw_hash) == 32
    
    def test_stats_tracking(self):
        """Test service statistics tracking."""
        config = HashConfig()
        service = ContentHashService(config)
        
        # Initial stats
        stats = service.get_stats()
        assert stats['total_processed'] == 0
        
        # Process some artifacts
        service.generate_hashes({'title': 'Coffee 1'})
        service.generate_hashes({'title': 'Coffee 2'})
        
        # Check updated stats
        stats = service.get_stats()
        assert stats['total_processed'] == 2
        assert stats['successful_hashes'] == 2
        assert stats['success_rate'] == 1.0
    
    def test_reset_stats(self):
        """Test statistics reset functionality."""
        config = HashConfig()
        service = ContentHashService(config)
        
        # Process some artifacts
        service.generate_hashes({'title': 'Coffee 1'})
        
        # Verify stats are populated
        stats = service.get_stats()
        assert stats['total_processed'] == 1
        
        # Reset stats
        service.reset_stats()
        
        # Verify stats are reset
        stats = service.get_stats()
        assert stats['total_processed'] == 0
        assert stats['successful_hashes'] == 0
