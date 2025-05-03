# AI Manager Configuration Guide

This document explains how to configure and use the AI Manager to switch between different AI providers in the application.

## Overview

The AI Manager is designed to be a flexible and hot-swappable interface to different AI providers including:

- OpenAI
- Ollama (local)
- DeepSeek

This allows you to easily switch between providers without changing your application code.

## Configuration File

The AI provider settings are defined in `providers.py`. You can modify this file to change settings for each provider or set the active provider.

### Setting the Active Provider

To change the active provider, modify the `ACTIVE_PROVIDER` setting in `providers.py`:

```python
# The currently active provider
ACTIVE_PROVIDER: AIProvider = AIProvider.OPENAI  # Change to OLLAMA or DEEPSEEK as needed
```

### Provider-Specific Configuration

Each provider has its own configuration options in the `AI_PROVIDER_CONFIGS` dictionary:

```python
AI_PROVIDER_CONFIGS: Dict[AIProvider, Dict[str, Any]] = {
    AIProvider.OPENAI: {
        "api_key": None,  # Set via environment variables or override here
        "model": "gpt-4o-mini",  # Change to desired model
        "base_url": None,  # Use default OpenAI URL or override for Azure
    },
    AIProvider.OLLAMA: {
        "base_url": "http://localhost:11434",  # Change if Ollama runs on a different port
        "model": "llama3",  # Change to available local model
    },
    AIProvider.DEEPSEEK: {
        "api_key": None,  # Set via environment variable or override here
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",  # Change if different API endpoint
    }
}
```

### Additional Settings

Additional generation parameters can be adjusted in the `PROVIDER_SETTINGS` dictionary:

```python
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
```

## Environment Variables

For API-based providers, you should set the appropriate API keys in your environment variables:

- `OPENAI_API_KEY` - For OpenAI
- `DEEPSEEK_API_KEY` - For DeepSeek

Example in `.env` file:
```
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
```

## Using the AI Manager in Code

The AI Manager is implemented as a singleton, so you can import and use it throughout your application:

```python
from app.utils.ai import ai_manager

# Create an assistant
assistant = await ai_manager.create_assistant(
    name="MyAssistant",
    instructions="You are a helpful assistant",
    tools=[]  # Optional tools definition
)

# Get a response
response = await ai_manager.get_response(
    user_message="Hello, how can you help me?",
    assistant_id=assistant["id"]
)

print(response["response"])
```

## Switching Providers at Runtime

You can also switch providers at runtime:

```python
from app.config.ai.providers import AIProvider
from app.utils.ai import ai_manager

# Switch to Ollama
ai_manager.set_provider(AIProvider.OLLAMA)

# Switch to OpenAI with custom settings
ai_manager.set_provider(
    AIProvider.OPENAI, 
    config_override={"model": "gpt-4"}
)
```

## Adding New Providers

To add a new provider:

1. Add the provider to the `AIProvider` enum in `providers.py`
2. Add configuration for the provider in `AI_PROVIDER_CONFIGS` 
3. Implement a new provider class that inherits from `BaseAIProvider`
4. Add the new provider class to the `_provider_map` in `AIManager`

## Troubleshooting

If you encounter issues:

1. Check that API keys are correctly set in environment variables
2. Verify that Ollama is running locally if using the Ollama provider
3. Check network connectivity for cloud-based providers
4. Review logs for any error messages from the providers 