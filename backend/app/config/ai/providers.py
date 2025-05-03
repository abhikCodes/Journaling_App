"""
Configuration file for AI providers.
This file defines settings for various AI providers that can be hot-swapped.
"""

from enum import Enum
from typing import Dict, Any, Optional


class AIProvider(str, Enum):
    """Enum of supported AI providers"""
    OPENAI = "openai"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"


# Default configuration for each provider
AI_PROVIDER_CONFIGS: Dict[AIProvider, Dict[str, Any]] = {
    AIProvider.OPENAI: {
        "api_key": None,  # Set via environment variables or override here
        "model": "gpt-4o-mini",
        "base_url": None,  # Use default OpenAI URL
    },
    AIProvider.OLLAMA: {
        "base_url": "http://localhost:11434",
        "model": "llama3",
    },
    AIProvider.DEEPSEEK: {
        "api_key": None,
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
    }
}

# The currently active provider
ACTIVE_PROVIDER: AIProvider = AIProvider.OPENAI

# Instruction templates for each provider (if they require different formatting)
INSTRUCTION_TEMPLATES: Dict[AIProvider, str] = {
    AIProvider.OPENAI: "{instructions}",
    AIProvider.OLLAMA: "{instructions}",
    AIProvider.DEEPSEEK: "{instructions}"
}

# Any additional provider-specific settings
PROVIDER_SETTINGS: Dict[AIProvider, Dict[str, Any]] = {
    AIProvider.OPENAI: {
        "temperature": 0.7,
        "max_tokens": 1000,
    },
    AIProvider.OLLAMA: {
        "temperature": 0.7,
        "max_tokens": 1000,
    },
    AIProvider.DEEPSEEK: {
        "temperature": 0.7,
        "max_tokens": 1000,
    }
} 