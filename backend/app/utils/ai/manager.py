"""
AI Manager for hot-swapping between different AI providers.
This module provides a unified interface for working with various AI providers.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Callable, Awaitable
from app.config.ai import AIProvider, AI_PROVIDER_CONFIGS, ACTIVE_PROVIDER
from app.utils.ai.providers import (
    BaseAIProvider, OpenAIProvider, OllamaProvider, DeepSeekProvider, GrokProvider
)
from app.utils.ai.logger import log_ai_interaction

# Configure logger
logger = logging.getLogger(__name__)

class AIManager:
    """
    AI Manager that provides a unified interface for different AI providers.
    This allows hot-swapping between providers like OpenAI, Ollama, and DeepSeek.
    """
    
    _instance = None
    _provider_map = {
        AIProvider.OPENAI: OpenAIProvider,
        AIProvider.OLLAMA: OllamaProvider,
        AIProvider.DEEPSEEK: DeepSeekProvider,
        AIProvider.GROK: GrokProvider
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
        
        # Log the request
        logger.info(f"Creating assistant with name: {name}")
        logger.info(f"Instructions: {instructions[:100]}..." if len(instructions) > 100 else f"Instructions: {instructions}")
        if tools:
            logger.info(f"Tools: {json.dumps(tools)}")
        
        # Log the assistant creation in the AI interactions log
        log_ai_interaction(
            provider=str(self.active_provider_type),
            prompt_type="assistant_creation",
            prompt=instructions,
            response="ASSISTANT CREATION - NO DIRECT RESPONSE",
            metadata={
                "assistant_name": name,
                "has_tools": bool(tools)
            }
        )
        
        assistant = await self._active_provider.create_assistant(
            name=name, 
            instructions=instructions,
            tools=tools
        )
        
        # Log the response
        logger.info(f"Assistant created with ID: {assistant['id']}")
        
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
        
        # Log request details
        logger.info(f">>> SENDING TO AI AGENT <<<")
        logger.info(f"User message: {user_message}")
        logger.info(f"Using assistant ID: {assistant_id}")
        logger.info(f"Thread ID: {thread_id or 'New thread will be created'}")
        logger.info(f"Provider: {self.active_provider_type}")
        
        # Create a new thread if not provided
        if not thread_id:
            thread_id = await self._active_provider.create_thread()
            logger.info(f"Created new thread with ID: {thread_id}")
        
        # Add the user message to the thread
        await self._active_provider.add_message(thread_id, user_message)
        
        # Run the assistant
        response = await self._active_provider.run_assistant(
            thread_id=thread_id,
            assistant_id=assistant_id,
            tool_callbacks=tool_callbacks
        )
        
        # Log the response
        logger.info(f">>> RECEIVED FROM AI AGENT <<<")
        logger.info(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
        
        # Log in AI interactions log
        log_ai_interaction(
            provider=str(self.active_provider_type),
            prompt_type="assistant_conversation",
            prompt=user_message,
            response=response,
            metadata={
                "assistant_id": assistant_id,
                "thread_id": thread_id,
                "used_tools": bool(tool_callbacks)
            }
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
        
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate an image using the active provider
        
        Args:
            prompt: The prompt to generate an image for
            size: The size of the image to generate (default: 1024x1024)
            
        Returns:
            URL to the generated image or None if generation failed
        """
        if not self._active_provider:
            raise RuntimeError("No active AI provider set")
        
        # Log the image generation request
        logger.info(f">>> SENDING IMAGE GENERATION REQUEST <<<")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Size: {size}")
        logger.info(f"Provider: {self.active_provider_type}")
        
        image_url = await self._active_provider.generate_image(prompt=prompt, size=size)
        
        # Log the response
        if image_url:
            logger.info(f">>> IMAGE GENERATION SUCCESSFUL <<<")
            logger.info(f"Image URL: {image_url[:100]}..." if len(image_url) > 100 else f"Image URL: {image_url}")
            
            # Log in AI interactions log
            log_ai_interaction(
                provider=str(self.active_provider_type),
                prompt_type="image_generation",
                prompt=prompt,
                response=f"Image generated: {image_url[:100]}..." if len(image_url) > 100 else f"Image generated: {image_url}",
                metadata={"size": size}
            )
        else:
            logger.error(">>> IMAGE GENERATION FAILED <<<")
            
            # Log failure in AI interactions log
            log_ai_interaction(
                provider=str(self.active_provider_type),
                prompt_type="image_generation",
                prompt=prompt,
                response="IMAGE GENERATION FAILED",
                metadata={"size": size, "failed": True}
            )
            
        return image_url


# Create a global instance for convenient import
ai_manager = AIManager() 