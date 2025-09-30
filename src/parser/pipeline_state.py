"""
Pipeline state management for normalizer pipeline orchestration.

Features:
- Track pipeline execution state for error recovery
- Manage deterministic and LLM results
- Handle pipeline errors and warnings
- Support checkpointing for partial failures
"""

import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages."""
    INITIALIZED = "initialized"
    DETERMINISTIC_PARSING = "deterministic_parsing"
    LLM_FALLBACK = "llm_fallback"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineError(BaseModel):
    """Represents a pipeline error with recovery information."""
    
    stage: PipelineStage = Field(..., description="Stage where error occurred")
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    recoverable: bool = Field(default=True, description="Whether error is recoverable")
    parser_name: Optional[str] = Field(default=None, description="Parser that failed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()


class PipelineWarning(BaseModel):
    """Represents a pipeline warning."""
    
    stage: PipelineStage = Field(..., description="Stage where warning occurred")
    parser_name: Optional[str] = Field(default=None, description="Parser that generated warning")
    message: str = Field(..., description="Warning message")
    severity: str = Field(default="low", description="Warning severity (low, medium, high)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()


class ParserResult(BaseModel):
    """Represents a parser execution result."""
    
    parser_name: str = Field(..., description="Name of the parser")
    success: bool = Field(..., description="Whether parsing was successful")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="Parsed data")
    warnings: List[str] = Field(default_factory=list, description="Parser warnings")
    execution_time: float = Field(default=0.0, description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()


class LLMResult(BaseModel):
    """Represents an LLM fallback result."""
    
    field_name: str = Field(..., description="Field that was processed by LLM")
    success: bool = Field(..., description="Whether LLM processing was successful")
    confidence: float = Field(..., ge=0.0, le=1.0, description="LLM confidence score")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="LLM result data")
    warnings: List[str] = Field(default_factory=list, description="LLM warnings")
    execution_time: float = Field(default=0.0, description="LLM execution time in seconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()


class PipelineState(BaseModel):
    """Track pipeline execution state for error recovery."""
    
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique execution ID")
    stage: PipelineStage = Field(default=PipelineStage.INITIALIZED, description="Current pipeline stage")
    deterministic_results: Dict[str, ParserResult] = Field(default_factory=dict, description="Deterministic parser results")
    llm_results: Dict[str, LLMResult] = Field(default_factory=dict, description="LLM fallback results")
    errors: List[PipelineError] = Field(default_factory=list, description="Pipeline errors")
    warnings: List[PipelineWarning] = Field(default_factory=list, description="Pipeline warnings")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_error(self, error: PipelineError):
        """Add error to pipeline state."""
        self.errors.append(error)
        self.updated_at = datetime.now(timezone.utc)
        logger.warning("Pipeline error added", error=error.to_dict(), execution_id=self.execution_id)
    
    def add_warning(self, warning: PipelineWarning):
        """Add warning to pipeline state."""
        self.warnings.append(warning)
        self.updated_at = datetime.now(timezone.utc)
        logger.info("Pipeline warning added", warning=warning.to_dict(), execution_id=self.execution_id)
    
    def add_parser_result(self, parser_name: str, result: ParserResult):
        """Add deterministic parser result."""
        self.deterministic_results[parser_name] = result
        self.updated_at = datetime.now(timezone.utc)
        logger.debug("Parser result added", parser=parser_name, success=result.success, execution_id=self.execution_id)
    
    def add_llm_result(self, field_name: str, result: LLMResult):
        """Add LLM fallback result."""
        self.llm_results[field_name] = result
        self.updated_at = datetime.now(timezone.utc)
        logger.debug("LLM result added", field=field_name, success=result.success, execution_id=self.execution_id)
    
    def get_overall_confidence(self) -> float:
        """Calculate overall pipeline confidence."""
        if not self.deterministic_results and not self.llm_results:
            return 0.0
        
        all_results = list(self.deterministic_results.values()) + list(self.llm_results.values())
        if not all_results:
            return 0.0
        
        total_confidence = sum(result.confidence for result in all_results)
        return total_confidence / len(all_results)
    
    def get_deterministic_confidence(self) -> float:
        """Calculate deterministic parser confidence."""
        if not self.deterministic_results:
            return 0.0
        
        total_confidence = sum(result.confidence for result in self.deterministic_results.values())
        return total_confidence / len(self.deterministic_results)
    
    def get_llm_confidence(self) -> float:
        """Calculate LLM fallback confidence."""
        if not self.llm_results:
            return 0.0
        
        total_confidence = sum(result.confidence for result in self.llm_results.values())
        return total_confidence / len(self.llm_results)
    
    def has_errors(self) -> bool:
        """Check if pipeline has any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if pipeline has any warnings."""
        return len(self.warnings) > 0
    
    def is_completed(self) -> bool:
        """Check if pipeline is completed successfully."""
        return self.stage == PipelineStage.COMPLETED and not self.has_errors()
    
    def needs_llm_fallback(self, threshold: float = 0.7) -> bool:
        """Check if pipeline needs LLM fallback based on confidence threshold."""
        deterministic_confidence = self.get_deterministic_confidence()
        return deterministic_confidence < threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'execution_id': self.execution_id,
            'stage': self.stage.value,
            'deterministic_results': {k: v.to_dict() for k, v in self.deterministic_results.items()},
            'llm_results': {k: v.to_dict() for k, v in self.llm_results.items()},
            'errors': [error.to_dict() for error in self.errors],
            'warnings': [warning.to_dict() for warning in self.warnings],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineState':
        """Create PipelineState from dictionary."""
        # Convert stage string back to enum
        if isinstance(data.get('stage'), str):
            data['stage'] = PipelineStage(data['stage'])
        
        # Convert deterministic results
        if 'deterministic_results' in data:
            deterministic_results = {}
            for k, v in data['deterministic_results'].items():
                deterministic_results[k] = ParserResult(**v)
            data['deterministic_results'] = deterministic_results
        
        # Convert LLM results
        if 'llm_results' in data:
            llm_results = {}
            for k, v in data['llm_results'].items():
                llm_results[k] = LLMResult(**v)
            data['llm_results'] = llm_results
        
        # Convert errors
        if 'errors' in data:
            data['errors'] = [PipelineError(**error) for error in data['errors']]
        
        # Convert warnings
        if 'warnings' in data:
            data['warnings'] = [PipelineWarning(**warning) for warning in data['warnings']]
        
        return cls(**data)
