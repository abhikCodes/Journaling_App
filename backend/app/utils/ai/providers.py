"""
AI Provider Interface and implementations.
This module defines a common interface for AI providers and concrete implementations
for different services like OpenAI, Ollama, and DeepSeek.
"""

import os
import json
import httpx
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from openai import OpenAI
from app.config import settings
from app.config.ai import AIProvider, AI_PROVIDER_CONFIGS, PROVIDER_SETTINGS

# Configure logger
logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """Base interface for all AI providers"""
    
    @abstractmethod
    async def create_assistant(self, name: str, instructions: str, tools: List[Dict] = None) -> Dict[str, Any]:
        """Create an assistant with the specified name, instructions and tools"""
        pass
    
    @abstractmethod
    async def create_thread(self) -> str:
        """Create a new thread and return the thread ID"""
        pass
    
    @abstractmethod
    async def add_message(self, thread_id: str, message: str, role: str = "user") -> None:
        """Add a message to the thread"""
        pass
    
    @abstractmethod
    async def run_assistant(self, thread_id: str, assistant_id: str, 
                           tool_callbacks: Dict[str, callable] = None) -> str:
        """Run the assistant on the thread and return the response"""
        pass
        
    @abstractmethod
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate an image from a prompt and return the URL"""
        pass


class OpenAIProvider(BaseAIProvider):
    """OpenAI implementation of the BaseAIProvider interface"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with optional config overrides"""
        self.config = AI_PROVIDER_CONFIGS[AIProvider.OPENAI].copy()
        self.settings = PROVIDER_SETTINGS[AIProvider.OPENAI].copy()
        
        if config:
            self.config.update(config)
            
        # Use environment variable if not specified in config
        if not self.config["api_key"]:
            self.config["api_key"] = os.getenv("OPENAI_API_KEY")
            
        self.client = OpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["base_url"]
        )
    
    async def create_assistant(self, name: str, instructions: str, tools: List[Dict] = None) -> Dict[str, Any]:
        """Create an OpenAI assistant"""
        assistant = self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            model=self.config["model"],
            tools=tools or []
        )
        return {
            "id": assistant.id,
            "name": assistant.name,
            "model": assistant.model
        }
    
    async def create_thread(self) -> str:
        """Create a new OpenAI thread"""
        thread = self.client.beta.threads.create()
        return thread.id
    
    async def add_message(self, thread_id: str, message: str, role: str = "user") -> None:
        """Add a message to the OpenAI thread"""
        self.client.beta.threads.messages.create(
            thread_id=thread_id, 
            role=role, 
            content=message
        )
    
    async def run_assistant(self, thread_id: str, assistant_id: str, 
                           tool_callbacks: Dict[str, callable] = None) -> str:
        """Run the OpenAI assistant on the thread and return the response"""
        tool_callbacks = tool_callbacks or {}
        
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id, 
            assistant_id=assistant_id
        )
        
        while run.status in ["in_progress", "queued", "requires_action"]:
            run = self.client.beta.threads.runs.retrieve(
                run_id=run.id, 
                thread_id=thread_id
            )
            
            if run.status == "requires_action":
                tool_outputs = []
                
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    function_name = tool_call.function.name
                    
                    if function_name in tool_callbacks:
                        args = json.loads(tool_call.function.arguments)
                        result = await tool_callbacks[function_name](**args)
                        tool_outputs.append({
                            "tool_call_id": tool_call.id, 
                            "output": json.dumps(result)
                        })
                
                if tool_outputs:
                    self.client.beta.threads.runs.submit_tool_outputs(
                        run_id=run.id, 
                        thread_id=thread_id, 
                        tool_outputs=tool_outputs
                    )
        
        messages = self.client.beta.threads.messages.list(thread_id=thread_id).data
        assistant_msgs = [msg for msg in messages if msg.role == 'assistant']
        assistant_msgs.sort(key=lambda m: m.created_at, reverse=True)
        
        if not assistant_msgs:
            return "I'm sorry, I couldn't process your request. Please try again."
        
        latest = assistant_msgs[0]
        reply = "".join(block.text.value for block in latest.content 
                        if hasattr(block, "text") and hasattr(block.text, "value"))
        
        return reply

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate an image using OpenAI DALL-E"""
        try:
            logger.info(f"OpenAI provider generating image with prompt: {prompt[:100]}...")
            logger.info(f"Using model: dall-e-3, size: {size}")
            
            # Use dall-e-3 instead of gpt-image-1 since organization may not be verified for gpt-image-1
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )
            
            # Return the URL of the generated image
            if response.data and len(response.data) > 0:
                image_url = response.data[0].url
                logger.info(f"OpenAI successfully generated image")
                logger.info(f"Image URL: {image_url[:100]}..." if len(image_url) > 100 else f"Image URL: {image_url}")
                return image_url
                
            logger.warning("OpenAI returned empty response data")
            logger.warning(f"Full response: {response}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating image with OpenAI: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            return None


class OllamaProvider(BaseAIProvider):
    """Ollama implementation of the BaseAIProvider interface"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with optional config overrides"""
        self.config = AI_PROVIDER_CONFIGS[AIProvider.OLLAMA].copy()
        self.settings = PROVIDER_SETTINGS[AIProvider.OLLAMA].copy()
        
        if config:
            self.config.update(config)
            
        # Store assistants and threads locally since Ollama doesn't have equivalents
        self.assistants = {}
        self.threads = {}
    
    async def create_assistant(self, name: str, instructions: str, tools: List[Dict] = None) -> Dict[str, Any]:
        """Create a local assistant representation for Ollama"""
        assistant_id = f"assistant_{len(self.assistants) + 1}"
        assistant = {
            "id": assistant_id,
            "name": name,
            "instructions": instructions,
            "model": self.config["model"],
            "tools": tools or []
        }
        self.assistants[assistant_id] = assistant
        return {
            "id": assistant_id,
            "name": name,
            "model": self.config["model"]
        }
    
    async def create_thread(self) -> str:
        """Create a local thread for Ollama"""
        thread_id = f"thread_{len(self.threads) + 1}"
        self.threads[thread_id] = {"messages": []}
        return thread_id
    
    async def add_message(self, thread_id: str, message: str, role: str = "user") -> None:
        """Add a message to the local thread"""
        if thread_id not in self.threads:
            self.threads[thread_id] = {"messages": []}
        
        self.threads[thread_id]["messages"].append({
            "role": role,
            "content": message
        })
    
    async def run_assistant(self, thread_id: str, assistant_id: str, 
                           tool_callbacks: Dict[str, callable] = None) -> str:
        """Run Ollama on the thread messages and return the response"""
        tool_callbacks = tool_callbacks or {}
        
        if thread_id not in self.threads or assistant_id not in self.assistants:
            return "Error: Invalid thread or assistant ID"
        
        assistant = self.assistants[assistant_id]
        thread = self.threads[thread_id]
        
        # Format the conversation history with system instructions
        conversation = [{
            "role": "system",
            "content": assistant["instructions"]
        }]
        conversation.extend(thread["messages"])
        
        # Extract available tools for function calling
        function_descriptions = []
        if assistant.get("tools"):
            for tool in assistant["tools"]:
                if tool.get("type") == "function" and tool.get("function"):
                    function_descriptions.append(tool["function"])
                    
        async with httpx.AsyncClient() as client:
            # Prepare the request to Ollama
            payload = {
                "model": self.config["model"],
                "messages": conversation,
                "stream": self.config.get("stream", False)
            }
            
            # Call Ollama API
            response = await client.post(
                f"{self.config['base_url']}/api/chat",
                json=payload,
                timeout=120.0  # Increased timeout for larger responses
            )
            
            if response.status_code != 200:
                try:
                    error_detail = response.json()
                    return f"Error: Ollama API returned status code {response.status_code}. Details: {error_detail}"
                except:
                    return f"Error: Ollama API returned status code {response.status_code}. Response: {response.text[:200]}"
            
            result = response.json()
            
            # Add the assistant's response to the thread
            content = ""
            if "message" in result and "content" in result["message"]:
                content = result["message"]["content"]
            
            thread["messages"].append({
                "role": "assistant",
                "content": content
            })
            
            return content

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate an image using Ollama (fallback to OpenAI if needed)"""
        logger.info("Ollama does not support native image generation. Using OpenAI instead.")
        
        # Use OpenAI as a fallback
        try:
            # Create a temporary OpenAI provider just for this request
            openai_provider = OpenAIProvider()
            return await openai_provider.generate_image(prompt, size)
        except Exception as e:
            logger.error(f"Error using OpenAI for image generation: {str(e)}")
            return None


class GrokProvider(BaseAIProvider):
    """Grok implementation of the BaseAIProvider interface"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with optional config overrides"""
        self.config = AI_PROVIDER_CONFIGS.get(AIProvider.GROK, {}).copy()
        self.settings = PROVIDER_SETTINGS.get(AIProvider.GROK, {}).copy()
        
        if config:
            self.config.update(config)
            
        # Use environment variable if not specified in config
        if not self.config.get("api_key"):
            self.config["api_key"] = os.getenv("GROK_API_KEY")
            
        self.api_key = self.config["api_key"]
        self.base_url = self.config.get("base_url", "https://api.grok.ai/v1")
        
        # Store assistants and threads locally since Grok's API is different
        self.assistants = {}
        self.threads = {}
    
    async def create_assistant(self, name: str, instructions: str, tools: List[Dict] = None) -> Dict[str, Any]:
        """Create a local assistant representation for Grok"""
        assistant_id = f"assistant_{len(self.assistants) + 1}"
        assistant = {
            "id": assistant_id,
            "name": name,
            "instructions": instructions,
            "model": self.config.get("model", "grok-1"),
            "tools": tools or []
        }
        self.assistants[assistant_id] = assistant
        return {
            "id": assistant_id,
            "name": name,
            "model": self.config.get("model", "grok-1")
        }
    
    async def create_thread(self) -> str:
        """Create a local thread for Grok"""
        thread_id = f"thread_{len(self.threads) + 1}"
        self.threads[thread_id] = {"messages": []}
        return thread_id
    
    async def add_message(self, thread_id: str, message: str, role: str = "user") -> None:
        """Add a message to the local thread"""
        if thread_id not in self.threads:
            self.threads[thread_id] = {"messages": []}
        
        self.threads[thread_id]["messages"].append({
            "role": role,
            "content": message
        })
    
    async def run_assistant(self, thread_id: str, assistant_id: str, 
                           tool_callbacks: Dict[str, callable] = None) -> str:
        """Run Grok on the thread messages and return the response"""
        tool_callbacks = tool_callbacks or {}
        
        if thread_id not in self.threads or assistant_id not in self.assistants:
            return "Error: Invalid thread or assistant ID"
        
        assistant = self.assistants[assistant_id]
        thread = self.threads[thread_id]
        
        # Format the conversation history with system instructions
        conversation = [{
            "role": "system",
            "content": assistant["instructions"]
        }]
        conversation.extend(thread["messages"])
        
        # Extract available tools for function calling
        function_descriptions = []
        if assistant.get("tools"):
            for tool in assistant["tools"]:
                if tool.get("type") == "function" and tool.get("function"):
                    function_descriptions.append(tool["function"])
        
        try:
            async with httpx.AsyncClient() as client:
                # Prepare the request to Grok
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.config.get("model", "grok-1"),
                    "messages": conversation,
                    "temperature": self.config.get("temperature", 0.7),
                    "max_tokens": self.config.get("max_tokens", 1000)
                }
                
                # Add tools if available
                if function_descriptions:
                    payload["tools"] = [{"type": "function", "function": func} for func in function_descriptions]
                
                # Call Grok API
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                
                if response.status_code != 200:
                    try:
                        error_detail = response.json()
                        return f"Error: Grok API returned status code {response.status_code}. Details: {error_detail}"
                    except:
                        return f"Error: Grok API returned status code {response.status_code}. Response: {response.text[:200]}"
                
                result = response.json()
                
                # Extract the response content
                content = ""
                if result.get("choices") and len(result["choices"]) > 0:
                    assistant_message = result["choices"][0].get("message", {})
                    content = assistant_message.get("content", "")
                
                # Handle function calls if present
                if assistant_message.get("tool_calls") and tool_callbacks:
                    for tool_call in assistant_message["tool_calls"]:
                        if tool_call.get("type") == "function":
                            function_name = tool_call["function"].get("name")
                            if function_name in tool_callbacks:
                                try:
                                    args = json.loads(tool_call["function"].get("arguments", "{}"))
                                    result = await tool_callbacks[function_name](**args)
                                    # Add function response to the thread
                                    self.threads[thread_id]["messages"].append({
                                        "role": "tool",
                                        "tool_call_id": tool_call["id"],
                                        "content": json.dumps(result)
                                    })
                                except Exception as e:
                                    print(f"Error executing tool callback: {str(e)}")
                
                # Add the assistant's response to the thread
                thread["messages"].append({
                    "role": "assistant",
                    "content": content
                })
                
                return content
                
        except Exception as e:
            error_msg = f"Error with Grok API: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate an image using Grok's image generation API"""
        try:
            logger.info(f"Grok provider generating image with prompt: {prompt[:100]}...")
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Parse size to get dimensions
                width, height = map(int, size.split('x'))
                
                payload = {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "n": 1,
                    "quality": "standard"
                }
                
                # Call Grok API for image generation
                response = await client.post(
                    f"{self.base_url}/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Error: Grok API returned status code {response.status_code}.")
                    return None
                
                result = response.json()
                
                # Extract the image URL
                if result.get("data") and len(result["data"]) > 0:
                    image_url = result["data"][0].get("url")
                    logger.info(f"Grok successfully generated image")
                    logger.info(f"Image URL: {image_url[:100]}..." if len(image_url) > 100 else f"Image URL: {image_url}")
                    return image_url
                return None
                
        except Exception as e:
            logger.error(f"Error generating image with Grok: {str(e)}")
            return None


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek implementation of the BaseAIProvider interface"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with optional config overrides"""
        self.config = AI_PROVIDER_CONFIGS[AIProvider.DEEPSEEK].copy()
        self.settings = PROVIDER_SETTINGS[AIProvider.DEEPSEEK].copy()
        
        if config:
            self.config.update(config)
            
        # Use environment variable if not specified in config
        if not self.config["api_key"]:
            self.config["api_key"] = os.getenv("DEEPSEEK_API_KEY")
            
        # Store assistants and threads locally
        self.assistants = {}
        self.threads = {}
    
    async def create_assistant(self, name: str, instructions: str, tools: List[Dict] = None) -> Dict[str, Any]:
        """Create a local assistant representation for DeepSeek"""
        assistant_id = f"assistant_{len(self.assistants) + 1}"
        assistant = {
            "id": assistant_id,
            "name": name,
            "instructions": instructions,
            "model": self.config["model"],
            "tools": tools or []
        }
        self.assistants[assistant_id] = assistant
        return {
            "id": assistant_id,
            "name": name,
            "model": self.config["model"]
        }
    
    async def create_thread(self) -> str:
        """Create a local thread for DeepSeek"""
        thread_id = f"thread_{len(self.threads) + 1}"
        self.threads[thread_id] = {"messages": []}
        return thread_id
    
    async def add_message(self, thread_id: str, message: str, role: str = "user") -> None:
        """Add a message to the local thread"""
        if thread_id not in self.threads:
            self.threads[thread_id] = {"messages": []}
        
        self.threads[thread_id]["messages"].append({
            "role": role,
            "content": message
        })
    
    async def run_assistant(self, thread_id: str, assistant_id: str, 
                           tool_callbacks: Dict[str, callable] = None) -> str:
        """Run DeepSeek on the thread messages and return the response"""
        tool_callbacks = tool_callbacks or {}
        
        if thread_id not in self.threads or assistant_id not in self.assistants:
            return "Error: Invalid thread or assistant ID"
        
        assistant = self.assistants[assistant_id]
        thread = self.threads[thread_id]
        
        # Format the conversation history with system instructions
        conversation = [{
            "role": "system",
            "content": assistant["instructions"]
        }]
        conversation.extend(thread["messages"])
        
        # Extract available tools for function calling
        function_descriptions = []
        if assistant.get("tools"):
            for tool in assistant["tools"]:
                if tool.get("type") == "function" and tool.get("function"):
                    function_descriptions.append(tool["function"])
                    
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            
            # Prepare the request to DeepSeek
            payload = {
                "model": self.config["model"],
                "messages": conversation,
                "temperature": self.settings.get("temperature", 0.7),
                "max_tokens": self.settings.get("max_tokens", 1000)
            }
            
            # Add tool information if available
            if function_descriptions:
                payload["tools"] = function_descriptions
                payload["tool_choice"] = "auto"
                
            # Call DeepSeek API
            response = await client.post(
                f"{self.config['base_url']}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0  # Increased timeout for larger responses
            )
            
            if response.status_code != 200:
                return f"Error: DeepSeek API returned status code {response.status_code}"
            
            result = response.json()
            
            # Process function calls if present
            if "tool_calls" in result.get("choices", [{}])[0].get("message", {}):
                tool_calls = result["choices"][0]["message"]["tool_calls"]
                tool_results = []
                
                for tool_call in tool_calls:
                    function_name = tool_call["function"]["name"]
                    if function_name in tool_callbacks:
                        args = json.loads(tool_call["function"]["arguments"])
                        tool_result = await tool_callbacks[function_name](**args)
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": json.dumps(tool_result)
                        })
                
                if tool_results:
                    # Make a follow-up request with the tool results
                    follow_up_messages = conversation + [
                        result["choices"][0]["message"]
                    ] + tool_results
                    
                    payload["messages"] = follow_up_messages
                    response = await client.post(
                        f"{self.config['base_url']}/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=120.0  # Increased timeout for follow-up requests
                    )
                    
                    if response.status_code != 200:
                        return f"Error: DeepSeek follow-up API call returned status code {response.status_code}"
                    
                    result = response.json()
            
            # Get content from response
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Add the assistant's response to the thread
            thread["messages"].append({
                "role": "assistant",
                "content": content
            })
            
            return content

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate an image with DeepSeek (not implemented)"""
        # DeepSeek currently doesn't support image generation
        logger.info("Image generation not supported by DeepSeek provider")
        
        # Use OpenAI as a fallback
        try:
            logger.info("Falling back to OpenAI for image generation")
            openai_provider = OpenAIProvider()
            return await openai_provider.generate_image(prompt, size)
        except Exception as e:
            logger.error(f"Error falling back to OpenAI for image generation: {str(e)}")
            return None 