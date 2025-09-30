"""Configuration for DeepSeek API integration."""

from dataclasses import dataclass, field
from typing import Dict
import os


@dataclass
class DeepSeekConfig:
    """Configuration for DeepSeek API integration"""
    
    api_key: str
    model: str = "deepseek-chat"  # or "deepseek-reasoner"
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Rate limiting (per roaster, since DeepSeek has no rate limits)
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "requests_per_day": 10000
    })
    
    # Cost tracking
    cost_per_1k_tokens: float = 0.00027  # Input tokens (cache miss)
    cost_per_1k_output_tokens: float = 0.00110  # Output tokens
    
    @classmethod
    def from_env(cls) -> 'DeepSeekConfig':
        """Create configuration from environment variables"""
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")
        
        return cls(
            api_key=api_key,
            model=os.getenv('DEEPSEEK_MODEL', 'deepseek-chat'),
            base_url=os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
            temperature=float(os.getenv('DEEPSEEK_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('DEEPSEEK_MAX_TOKENS', '1000')),
            timeout=int(os.getenv('DEEPSEEK_TIMEOUT', '30')),
        )
