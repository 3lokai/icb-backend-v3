"""
Configuration for artifact validator.
"""

from typing import Dict, Any, Optional
from pathlib import Path


class ValidatorConfig:
    """Configuration for artifact validator."""
    
    def __init__(
        self,
        storage_path: str = "data/fetcher",
        invalid_artifacts_path: str = "data/validator/invalid_artifacts",
        enable_strict_validation: bool = True,
        enable_error_persistence: bool = True,
        max_validation_errors: int = 100,
        validation_timeout_seconds: int = 30
    ):
        """
        Initialize validator configuration.
        
        Args:
            storage_path: Path to A.2 storage directory
            invalid_artifacts_path: Path for storing invalid artifacts
            enable_strict_validation: Enable strict Pydantic validation
            enable_error_persistence: Enable persistence of invalid artifacts
            max_validation_errors: Maximum validation errors to track
            validation_timeout_seconds: Timeout for validation operations
        """
        self.storage_path = Path(storage_path)
        self.invalid_artifacts_path = Path(invalid_artifacts_path)
        self.enable_strict_validation = enable_strict_validation
        self.enable_error_persistence = enable_error_persistence
        self.max_validation_errors = max_validation_errors
        self.validation_timeout_seconds = validation_timeout_seconds
        
        # Create directories if they don't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.invalid_artifacts_path.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'storage_path': str(self.storage_path),
            'invalid_artifacts_path': str(self.invalid_artifacts_path),
            'enable_strict_validation': self.enable_strict_validation,
            'enable_error_persistence': self.enable_error_persistence,
            'max_validation_errors': self.max_validation_errors,
            'validation_timeout_seconds': self.validation_timeout_seconds
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ValidatorConfig':
        """Create configuration from dictionary."""
        return cls(
            storage_path=config_dict.get('storage_path', 'data/fetcher'),
            invalid_artifacts_path=config_dict.get('invalid_artifacts_path', 'data/validator/invalid_artifacts'),
            enable_strict_validation=config_dict.get('enable_strict_validation', True),
            enable_error_persistence=config_dict.get('enable_error_persistence', True),
            max_validation_errors=config_dict.get('max_validation_errors', 100),
            validation_timeout_seconds=config_dict.get('validation_timeout_seconds', 30)
        )
    
    def validate_config(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
        """
        try:
            # Check if storage path exists or can be created
            if not self.storage_path.exists():
                self.storage_path.mkdir(parents=True, exist_ok=True)
            
            # Check if invalid artifacts path exists or can be created
            if not self.invalid_artifacts_path.exists():
                self.invalid_artifacts_path.mkdir(parents=True, exist_ok=True)
            
            # Validate numeric values
            if self.max_validation_errors <= 0:
                return False
            
            if self.validation_timeout_seconds <= 0:
                return False
            
            return True
            
        except Exception:
            return False
