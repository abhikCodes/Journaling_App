"""
AI Manager for hot-swapping between different AI providers.
This module provides a unified interface for working with various AI providers.
"""

import os
from typing import Dict, Any, List, Optional, Callable, Awaitable
from app.config.ai import AIProvider, AI_PROVIDER_CONFIGS, ACTIVE_PROVIDER
from app.utils.ai.providers import (
    BaseAIProvider, OpenAIProvider, OllamaProvider, DeepSeekProvider
)


class AIManager:
    """
    AI Manager that provides a unified interface for different AI providers.
    This allows hot-swapping between providers like OpenAI, Ollama, and DeepSeek.
    """
    
    _instance = None
    _provider_map = {
        AIProvider.OPENAI: OpenAIProvider,
        AIProvider.OLLAMA: OllamaProvider,
        AIProvider.DEEPSEEK: DeepSeekProvider
    }
    _active_provider: BaseAIProvider = None
    _active_assistant_id: Optional[str] = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(AIManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the manager with the configured provider"""
        self.set_provider(ACTIVE_PROVIDER)
    
    def set_provider(self, provider_name: AIProvider, config_override: Dict[str, Any] = None) -> None:
        """
        Set the active AI provider
        
        Args:
            provider_name: The name of the provider to use (from AIProvider enum)
            config_override: Optional configuration overrides for the provider
        """
        if provider_name not in self._provider_map:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = self._provider_map[provider_name]
        self._active_provider = provider_class(config=config_override)
        
        # Reset the active assistant
        self._active_assistant_id = None
    
    async def create_assistant(self, name: str, instructions: str, 
                              tools: List[Dict] = None) -> Dict[str, Any]:
        """
        Create an assistant with the active provider
        
        Args:
            name: The name of the assistant
            instructions: The instructions for the assistant
            tools: Optional list of tools available to the assistant
            
        Returns:
            Dict containing assistant details including ID
        """
        if not self._active_provider:
            raise RuntimeError("No active AI provider set")
        
        assistant = await self._active_provider.create_assistant(
            name=name, 
            instructions=instructions,
            tools=tools
        )
        
        # Store the assistant ID for convenience
        self._active_assistant_id = assistant["id"]
        
        return assistant
    
    async def get_response(self, 
                          user_message: str, 
                          thread_id: Optional[str] = None,
                          assistant_id: Optional[str] = None,
                          tool_callbacks: Dict[str, Callable[..., Awaitable]] = None) -> Dict[str, Any]:
        """
        Get a response from the assistant
        
        Args:
            user_message: The user's message
            thread_id: Optional thread ID (creates a new thread if None)
            assistant_id: Optional assistant ID (uses active assistant if None)
            tool_callbacks: Optional dict mapping tool names to callback functions
            
        Returns:
            Dict containing response and thread_id
        """
        if not self._active_provider:
            raise RuntimeError("No active AI provider set")
        
        # Use active assistant if not specified
        if not assistant_id:
            assistant_id = self._active_assistant_id
            if not assistant_id:
                raise ValueError("No assistant ID provided and no active assistant")
        
        # Create a new thread if not provided
        if not thread_id:
            thread_id = await self._active_provider.create_thread()
        
        # Add the user message to the thread
        await self._active_provider.add_message(thread_id, user_message)
        
        # Run the assistant
        response = await self._active_provider.run_assistant(
            thread_id=thread_id,
            assistant_id=assistant_id,
            tool_callbacks=tool_callbacks
        )
        
        return {
            "response": response,
            "thread_id": thread_id
        }
    
    @property
    def active_provider_type(self) -> AIProvider:
        """Get the type of the current active provider"""
        for provider_type, provider_class in self._provider_map.items():
            if isinstance(self._active_provider, provider_class):
                return provider_type
        return None
    
    @property
    def active_assistant_id(self) -> Optional[str]:
        """Get the ID of the active assistant, if any"""
        return self._active_assistant_id
    
    def set_active_assistant_id(self, assistant_id: str) -> None:
        """Set the active assistant ID"""
        self._active_assistant_id = assistant_id


# Create a global instance for convenient import
ai_manager = AIManager() 