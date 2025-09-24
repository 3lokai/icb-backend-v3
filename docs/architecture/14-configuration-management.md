# 14. Configuration Management

## 14.1 Configuration Architecture

### Central Configuration Pattern
The system uses a centralized configuration approach with `ValidatorConfig` as the main configuration class:

**ValidatorConfig (Pydantic BaseModel):**
```python
class ValidatorConfig(BaseModel):
    # Core configuration
    storage_path: str = Field(..., description="Base storage path for artifacts")
    enable_image_deduplication: bool = Field(True, description="Enable image deduplication")
    enable_imagekit_upload: bool = Field(True, description="Enable ImageKit upload")
    
    # Service-specific configurations
    imagekit_config: Optional[ImageKitConfig] = Field(None, description="ImageKit configuration")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidatorConfig':
        """Deserialize configuration from dictionary."""
        return cls(**data)
```

### Service-Specific Configurations
Each service domain has its own configuration class:

```python
# ImageKit Configuration
class ImageKitConfig(BaseModel):
    public_key: str = Field(..., description="ImageKit public key")
    private_key: str = Field(..., description="ImageKit private key")
    url_endpoint: str = Field(..., description="ImageKit URL endpoint")
    folder: str = Field("/coffee-images/", description="Default folder for uploads")
    enabled: bool = Field(True, description="Enable/disable ImageKit upload")
    
    @field_validator('public_key')
    @classmethod
    def validate_public_key(cls, v):
        if not v.startswith('public_'):
            raise ValueError("Public key must start with 'public_'")
        return v
```

### Parser Configuration
Parser services (C.1, C.2) use Pydantic models and centralized configuration:
```python
# Parser Configuration
class ValidatorConfig(BaseModel):
    # ... existing fields ...
    
    # Parser configuration
    enable_weight_parsing: bool = Field(True, description="Enable weight parsing")
    enable_roast_parsing: bool = Field(True, description="Enable roast level parsing")
    enable_process_parsing: bool = Field(True, description="Enable process method parsing")
    
    # Weight parser specific settings
    weight_confidence_threshold: float = Field(0.8, description="Minimum confidence for weight parsing")
    weight_fallback_unit: str = Field("g", description="Fallback unit for ambiguous weights")
    
    # Roast parser specific settings
    roast_confidence_threshold: float = Field(0.7, description="Minimum confidence for roast parsing")
    
    # Process parser specific settings
    process_confidence_threshold: float = Field(0.7, description="Minimum confidence for process parsing")
```

**Parser Result Models:**
```python
class WeightResult(BaseModel):
    grams: int = Field(..., ge=0, description="Weight in grams")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    original_format: str = Field(..., description="Original weight format")
    parsing_warnings: List[str] = Field(default_factory=list, description="Parsing warnings")
    conversion_notes: str = Field("", description="Conversion notes")

class RoastResult(BaseModel):
    roast_level: str = Field(..., description="Parsed roast level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    original_text: str = Field(..., description="Original roast text")
    parsing_warnings: List[str] = Field(default_factory=list, description="Parsing warnings")

class ProcessResult(BaseModel):
    process_method: str = Field(..., description="Parsed process method")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    original_text: str = Field(..., description="Original process text")
    parsing_warnings: List[str] = Field(default_factory=list, description="Parsing warnings")
```

## 14.2 Configuration Validation

### Pydantic Field Validation
All configuration fields use Pydantic validation:

```python
class ImageKitConfig(BaseModel):
    public_key: str = Field(
        ..., 
        min_length=1, 
        description="ImageKit public key"
    )
    private_key: str = Field(
        ..., 
        min_length=1, 
        description="ImageKit private key"
    )
    url_endpoint: str = Field(
        ..., 
        description="ImageKit URL endpoint (e.g., https://ik.imagekit.io/your_id)"
    )
```

### Custom Validators
Custom validators ensure configuration integrity:

```python
@field_validator('public_key')
@classmethod
def validate_public_key(cls, v):
    if not v.startswith('public_'):
        raise ValueError("Public key must start with 'public_'")
    return v

@field_validator('private_key')
@classmethod
def validate_private_key(cls, v):
    if not v.startswith('private_'):
        raise ValueError("Private key must start with 'private_'")
    return v
```

## 14.3 Configuration Serialization

### Dictionary Serialization
All configuration classes support dictionary serialization:

```python
# Serialize to dictionary
config_dict = validator_config.to_dict()

# Deserialize from dictionary
restored_config = ValidatorConfig.from_dict(config_dict)
```

### Nested Configuration Handling
Complex configurations with nested objects are properly serialized:

```python
# Serialize nested ImageKit configuration
config_dict = validator_config.to_dict()
imagekit_data = config_dict.get('imagekit_config', {})

# Deserialize nested configuration
if imagekit_data:
    imagekit_config = ImageKitConfig.from_dict(imagekit_data)
    validator_config.imagekit_config = imagekit_config
```

## 14.4 Configuration Location and Organization

### File Structure
```
src/config/
├── __init__.py
├── validator_config.py      # Main ValidatorConfig
├── imagekit_config.py      # ImageKit-specific config
└── [future service configs] # Additional service configs
```

### Import Patterns
```python
# Main configuration
from src.config.validator_config import ValidatorConfig

# Service-specific configurations
from src.config.imagekit_config import ImageKitConfig, ImageKitResult
```

## 14.5 Environment Configuration

### Environment Variable Support
Configuration classes support environment variable overrides:

```python
class ValidatorConfig(BaseModel):
    storage_path: str = Field(
        default_factory=lambda: os.getenv('STORAGE_PATH', '/tmp/artifacts')
    )
    enable_image_deduplication: bool = Field(
        default_factory=lambda: os.getenv('ENABLE_IMAGE_DEDUP', 'true').lower() == 'true'
    )
```

### Configuration Profiles
Support for different configuration profiles:

```python
@classmethod
def development_profile(cls) -> 'ValidatorConfig':
    """Development configuration profile."""
    return cls(
        storage_path="/tmp/dev_artifacts",
        enable_image_deduplication=True,
        enable_imagekit_upload=False  # Disabled in development
    )

@classmethod
def production_profile(cls) -> 'ValidatorConfig':
    """Production configuration profile."""
    return cls(
        storage_path="/var/artifacts",
        enable_image_deduplication=True,
        enable_imagekit_upload=True
    )
```

## 14.6 Configuration Testing

### Configuration Validation Tests
```python
def test_imagekit_config_validation():
    """Test ImageKit configuration validation."""
    # Valid configuration
    config = ImageKitConfig(
        public_key="public_test_key",
        private_key="private_test_key",
        url_endpoint="https://ik.imagekit.io/test"
    )
    assert config.public_key == "public_test_key"
    
    # Invalid configuration
    with pytest.raises(ValidationError):
        ImageKitConfig(
            public_key="invalid_key",  # Should start with 'public_'
            private_key="private_test_key",
            url_endpoint="https://ik.imagekit.io/test"
        )
```

### Serialization Tests
```python
def test_config_serialization():
    """Test configuration serialization and deserialization."""
    # Create configuration
    imagekit_config = ImageKitConfig(
        public_key="public_test_key",
        private_key="private_test_key",
        url_endpoint="https://ik.imagekit.io/test"
    )
    
    validator_config = ValidatorConfig(
        storage_path="/tmp/test",
        enable_image_deduplication=True,
        enable_imagekit_upload=True,
        imagekit_config=imagekit_config
    )
    
    # Serialize
    config_dict = validator_config.to_dict()
    assert 'imagekit_config' in config_dict
    
    # Deserialize
    restored_config = ValidatorConfig.from_dict(config_dict)
    assert restored_config.enable_image_deduplication is True
    assert restored_config.imagekit_config is not None
```

## 14.7 Configuration Best Practices

### Design Principles
1. **Single Source of Truth**: One configuration class per service domain
2. **Validation First**: All configuration validated at creation time
3. **Type Safety**: Strong typing with Pydantic models
4. **Documentation**: Clear field descriptions and validation rules
5. **Serialization**: Support for persistence and restoration

### Naming Conventions
- **Configuration Classes**: `{Service}Config` (e.g., `ImageKitConfig`)
- **Field Names**: `snake_case` for consistency
- **Validation Methods**: `validate_{field_name}` for custom validators
- **Profile Methods**: `{environment}_profile()` for configuration profiles

### Error Handling
- **Validation Errors**: Clear error messages for invalid configuration
- **Missing Fields**: Required fields with clear error messages
- **Type Errors**: Automatic type conversion where possible
- **Custom Validation**: Domain-specific validation rules

## 14.8 Migration and Evolution

### Configuration Schema Evolution
- **Backward Compatibility**: Support for older configuration formats
- **Migration Scripts**: Automated configuration migration
- **Version Tracking**: Configuration version tracking
- **Deprecation**: Graceful deprecation of old configuration options

### Configuration Updates
- **Hot Reloading**: Support for configuration updates without restart
- **Validation**: Re-validate configuration on updates
- **Rollback**: Support for configuration rollback
- **Audit Trail**: Track configuration changes

## 14.9 Security Considerations

### Secret Management
- **API Keys**: Secure storage of API keys and secrets
- **Environment Variables**: Use environment variables for sensitive data
- **Validation**: Validate secret formats and requirements
- **Access Control**: Proper access control for configuration access

### Configuration Security
- **Input Sanitization**: Sanitize configuration inputs
- **Validation**: Validate all configuration values
- **Audit Logging**: Log configuration access and changes
- **Encryption**: Encrypt sensitive configuration data
