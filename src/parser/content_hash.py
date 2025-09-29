"""
Content hash generation service for change detection and artifact tracking.
"""

import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from structlog import get_logger

from ..config.hash_config import HashConfig

logger = get_logger(__name__)


class HashResult(BaseModel):
    """Result model for hash generation."""
    
    content_hash: str = Field(description="Content hash for change detection")
    raw_hash: str = Field(description="Raw payload hash for artifact tracking")
    algorithm: str = Field(description="Hash algorithm used")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Generation timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ContentHashService:
    """
    Service for generating content and raw payload hashes.
    
    Features:
    - Content hash generation for change detection
    - Raw payload hash generation for artifact tracking
    - Hash collision detection and handling
    - Batch processing optimization
    - Multiple hash algorithm support (SHA256, MD5)
    """
    
    def __init__(self, config: Optional[HashConfig] = None):
        """
        Initialize content hash service.
        
        Args:
            config: Hash configuration
        """
        self.config = config or HashConfig()
        self.logger = logger.bind(service="content_hash")
        
        # Service stats
        self.stats = {
            'total_processed': 0,
            'successful_hashes': 0,
            'failed_hashes': 0,
            'collision_detections': 0,
            'batch_operations': 0
        }
    
    def generate_hashes(self, artifact: Dict[str, Any]) -> HashResult:
        """
        Generate content and raw payload hashes for artifact.
        
        Args:
            artifact: Artifact data dictionary
            
        Returns:
            HashResult with generated hashes
        """
        if not artifact or not isinstance(artifact, dict):
            self.logger.warning("Invalid artifact provided for hash generation")
            return self._create_empty_result()
        
        self.logger.debug("Starting hash generation", artifact_keys=list(artifact.keys()))
        
        try:
            # Generate content hash for change detection
            content_hash = self._generate_content_hash(artifact)
            
            # Generate raw payload hash for artifact tracking
            raw_hash = self._generate_raw_hash(artifact)
            
            result = HashResult(
                content_hash=content_hash,
                raw_hash=raw_hash,
                algorithm=self.config.hash_algorithm
            )
            
            # Update stats
            self.stats['total_processed'] += 1
            self.stats['successful_hashes'] += 1
            
            self.logger.debug(
                "Hash generation completed",
                content_hash=content_hash[:16] + "...",  # Truncate for logging
                raw_hash=raw_hash[:16] + "...",
                algorithm=self.config.hash_algorithm
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to generate hashes", error=str(e))
            self.stats['total_processed'] += 1
            self.stats['failed_hashes'] += 1
            return self._create_empty_result()
    
    def generate_hashes_batch(self, artifacts: List[Dict[str, Any]]) -> List[HashResult]:
        """
        Generate hashes for multiple artifacts in batch.
        
        Optimized for processing 100+ artifacts with < 1 second response time.
        
        Args:
            artifacts: List of artifact data dictionaries
            
        Returns:
            List of HashResult objects
        """
        if not artifacts:
            return []
        
        batch_size = len(artifacts)
        self.logger.info("Starting batch hash generation", batch_size=batch_size)
        
        results = []
        for i, artifact in enumerate(artifacts):
            try:
                result = self.generate_hashes(artifact)
                results.append(result)
            except Exception as e:
                self.logger.error("Failed to process artifact in batch", index=i, error=str(e))
                results.append(self._create_empty_result())
        
        # Update batch stats
        self.stats['batch_operations'] += 1
        successful_hashes = sum(1 for r in results if r.content_hash and r.raw_hash)
        
        self.logger.info(
            "Batch hash generation completed",
            total_processed=batch_size,
            successful=successful_hashes,
            success_rate=successful_hashes / batch_size if batch_size > 0 else 0
        )
        
        return results
    
    def _generate_content_hash(self, artifact: Dict[str, Any]) -> str:
        """
        Generate hash of normalized content for change detection.
        
        Args:
            artifact: Artifact data dictionary
            
        Returns:
            Content hash string
        """
        # Extract normalized fields for hashing
        normalized_content = {}
        for field in self.config.content_fields:
            normalized_content[field] = artifact.get(field)
        
        # Convert to JSON string for hashing (sorted keys for consistency)
        content_string = json.dumps(normalized_content, sort_keys=True, default=str)
        
        # Generate hash
        return self._compute_hash(content_string)
    
    def _generate_raw_hash(self, artifact: Dict[str, Any]) -> str:
        """
        Generate hash of raw payload for artifact tracking.
        
        Args:
            artifact: Artifact data dictionary
            
        Returns:
            Raw payload hash string
        """
        # Use entire artifact as raw payload
        raw_string = json.dumps(artifact, sort_keys=True, default=str)
        
        # Generate hash
        return self._compute_hash(raw_string)
    
    def _compute_hash(self, data: str) -> str:
        """
        Compute hash using configured algorithm.
        
        Args:
            data: String data to hash
            
        Returns:
            Hash string
        """
        if self.config.hash_algorithm == 'sha256':
            return hashlib.sha256(data.encode('utf-8')).hexdigest()
        elif self.config.hash_algorithm == 'md5':
            return hashlib.md5(data.encode('utf-8')).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {self.config.hash_algorithm}")
    
    def _create_empty_result(self) -> HashResult:
        """Create empty hash result for error cases."""
        return HashResult(
            content_hash="",
            raw_hash="",
            algorithm=self.config.hash_algorithm
        )
    
    def detect_hash_collision(self, hash_value: str, existing_hashes: List[str]) -> bool:
        """
        Detect hash collision with existing hashes.
        
        Args:
            hash_value: Hash value to check
            existing_hashes: List of existing hash values
            
        Returns:
            True if collision detected
        """
        if not self.config.enable_collision_detection:
            return False
        
        collision = hash_value in existing_hashes
        if collision:
            self.stats['collision_detections'] += 1
            self.logger.warning("Hash collision detected", hash_value=hash_value[:16] + "...")
        
        return collision
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        stats = self.stats.copy()
        
        # Calculate success rate
        if stats['total_processed'] > 0:
            stats['success_rate'] = stats['successful_hashes'] / stats['total_processed']
            stats['failure_rate'] = stats['failed_hashes'] / stats['total_processed']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset service statistics."""
        self.stats = {
            'total_processed': 0,
            'successful_hashes': 0,
            'failed_hashes': 0,
            'collision_detections': 0,
            'batch_operations': 0
        }
