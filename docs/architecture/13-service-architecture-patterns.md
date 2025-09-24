# 13. Service Architecture Patterns

## 13.1 Configuration Management

### Pydantic Configuration Models
All services use Pydantic `BaseModel` for configuration with validation:

```python
# Example: ImageKit Configuration
class ImageKitConfig(BaseModel):
    public_key: str = Field(..., description="ImageKit public key")
    private_key: str = Field(..., description="ImageKit private key")
    url_endpoint: str = Field(..., description="ImageKit URL endpoint")
    
    @field_validator('public_key')
    @classmethod
    def validate_public_key(cls, v):
        if not v.startswith('public_'):
            raise ValueError("Public key must start with 'public_'")
        return v
```

### Configuration Location
- **Primary**: `src/config/` module for all configuration classes
- **Pattern**: One configuration file per service domain
- **Validation**: Field validation with custom validators
- **Serialization**: `to_dict()` and `from_dict()` methods for persistence

### Configuration Integration
- **ValidatorConfig**: Central configuration with service composition
- **Service-specific configs**: Composed into main ValidatorConfig
- **Environment**: Support for environment-based configuration overrides

## 13.2 Service Composition Patterns

### ValidatorIntegrationService as Composition Root
The `ValidatorIntegrationService` serves as the composition root for all services:

```python
class ValidatorIntegrationService:
    def __init__(self, config: ValidatorConfig, supabase_client=None):
        # Core services
        self.storage_reader = StorageReader(base_storage_path=self.config.storage_path)
        self.validator = ArtifactValidator(storage_reader=self.storage_reader)
        self.rpc_client = RPCClient(supabase_client=supabase_client)
        
        # Image processing services (F.1, F.2)
        if self.config.enable_image_deduplication:
            self.image_deduplication_service = ImageDeduplicationService(self.rpc_client)
        
        if self.config.enable_imagekit_upload and self.config.imagekit_config:
            self.imagekit_service = ImageKitService(self.config.imagekit_config)
            self.imagekit_integration = ImageKitIntegrationService(...)
        
        # Artifact mapper with service composition
        self.artifact_mapper = ArtifactMapper(integration_service=self)
```

### Dependency Injection Pattern
All services follow constructor-based dependency injection:

```python
# Service accepts dependencies in constructor
class ImageDeduplicationService:
    def __init__(self, rpc_client: RPCClient):
        self.rpc_client = rpc_client

# Integration service composes dependencies
class ImageKitIntegrationService:
    def __init__(self, rpc_client: RPCClient, imagekit_config: ImageKitConfig, ...):
        self.rpc_client = rpc_client
        self.imagekit_service = ImageKitService(imagekit_config)
        self.deduplication_service = ImageDeduplicationService(rpc_client)
```

## 13.3 Error Handling Patterns

### Custom Exception Classes
Each service domain defines its own exception hierarchy:

```python
class ImageDeduplicationError(Exception):
    """Base exception for image deduplication errors."""
    pass

class ImageKitUploadError(Exception):
    """Exception raised for ImageKit upload errors."""
    pass
```

### Structured Logging
All services use `structlog` for consistent logging:

```python
from structlog import get_logger
logger = get_logger(__name__)

# Usage in services
logger.info("Image deduplication service initialized")
logger.warning("Failed to initialize image deduplication service", error=str(e))
```

### Error Recovery Patterns
- **Retry Logic**: Exponential backoff with jitter
- **Fallback Mechanisms**: Graceful degradation when services unavailable
- **Circuit Breaker**: Prevent cascading failures
- **Health Checks**: Service availability monitoring

## 13.4 Testing Patterns

### Service Testing
- **Mock Dependencies**: Use `MagicMock` for external dependencies
- **Fixture-based Setup**: Pytest fixtures for common test scenarios
- **Integration Tests**: Test service composition and interaction
- **Performance Tests**: Benchmark critical paths

### Configuration Testing
- **Validation Tests**: Verify Pydantic validation rules
- **Serialization Tests**: Test `to_dict()` and `from_dict()` methods
- **Environment Tests**: Test configuration overrides

### Test Organization
```
tests/
├── images/                    # F.1, F.2 image processing tests
│   ├── test_deduplication_service.py
│   ├── test_imagekit_service.py
│   └── test_imagekit_integration.py
├── validator/                 # A.1-A.5 validator tests
└── integration/              # End-to-end integration tests
```

## 13.5 Service Integration Patterns

### ArtifactMapper Integration
The `ArtifactMapper` accepts an `integration_service` parameter for service composition:

```python
class ArtifactMapper:
    def __init__(self, integration_service=None, ...):
        if integration_service:
            # Use services from integration service
            self.deduplication_service = integration_service.image_deduplication_service
            self.imagekit_integration = integration_service.imagekit_integration
        else:
            # Initialize services individually (legacy support)
            # ... individual service initialization
```

## 13.6 Parser Service Patterns

### Parser Service Architecture
Parser services use Pydantic BaseModel for result objects:

```python
# Parser Result Objects (Pydantic BaseModel)
class WeightResult(BaseModel):
    grams: int = Field(..., ge=0, description="Weight in grams")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    original_format: str = Field(..., description="Original weight format")
    parsing_warnings: List[str] = Field(default_factory=list, description="Parsing warnings")
    conversion_notes: str = Field("", description="Conversion notes")
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
```

### Parser Service Integration
Parser services are composed through `ValidatorIntegrationService`:

```python
# Parser Service Composition
class ValidatorIntegrationService:
    def __init__(self, config: ValidatorConfig):
        # Compose parser services
        if config.enable_weight_parsing:
            self.weight_parser = WeightParser()
        if config.enable_roast_parsing:
            self.roast_parser = RoastLevelParser()
        if config.enable_process_parsing:
            self.process_parser = ProcessMethodParser()
        
        # Pass to ArtifactMapper
        self.artifact_mapper = ArtifactMapper(integration_service=self)
```

### Service Lifecycle
1. **Initialization**: Services created in dependency order
2. **Configuration**: Services configured with validated settings
3. **Health Checks**: Services verify their dependencies
4. **Operation**: Services process requests with error handling
5. **Cleanup**: Services gracefully shutdown on termination

## 13.6 Performance Patterns

### Caching Strategies
- **Hash Caching**: Cache computed hashes for deduplication
- **Configuration Caching**: Cache validated configuration objects
- **Result Caching**: Cache expensive computation results

### Batch Processing
- **Batch Operations**: Process multiple items efficiently
- **Concurrency Control**: Limit concurrent operations
- **Progress Tracking**: Monitor batch processing progress

### Monitoring and Metrics
- **Service Statistics**: Track service performance metrics
- **Error Rates**: Monitor service error rates
- **Performance Benchmarks**: Regular performance testing

## 13.7 Security Patterns

### Input Validation
- **Pydantic Validation**: All inputs validated with Pydantic models
- **Type Safety**: Strong typing throughout service layer
- **Sanitization**: Input sanitization for security

### Secret Management
- **Configuration Validation**: Validate API keys and secrets
- **Environment Variables**: Secure secret storage
- **Access Control**: Proper access control for sensitive operations

## 13.8 Migration and Versioning

### Configuration Versioning
- **Schema Evolution**: Support for configuration schema changes
- **Backward Compatibility**: Maintain compatibility with older configurations
- **Migration Scripts**: Automated configuration migration

### Service Versioning
- **API Versioning**: Version service APIs for compatibility
- **Feature Flags**: Enable/disable features via configuration
- **Gradual Rollout**: Support for gradual feature rollouts

## 13.9 Best Practices

### Code Organization
- **Single Responsibility**: Each service has a single, well-defined responsibility
- **Dependency Inversion**: Depend on abstractions, not concretions
- **Interface Segregation**: Small, focused interfaces
- **Open/Closed Principle**: Open for extension, closed for modification

### Documentation
- **Service Documentation**: Clear documentation for each service
- **API Documentation**: Document service APIs and interfaces
- **Configuration Documentation**: Document all configuration options
- **Example Usage**: Provide usage examples for each service

### Maintenance
- **Regular Updates**: Keep dependencies up to date
- **Security Patches**: Apply security patches promptly
- **Performance Monitoring**: Monitor service performance
- **Error Analysis**: Regular analysis of service errors
