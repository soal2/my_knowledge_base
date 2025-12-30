"""
LLM Service

This module provides a unified interface for different LLM providers:
- Qwen (via DashScope API)
- DeepSeek (via OpenAI-compatible API)

Features:
- Provider abstraction
- Streaming support
- Token counting
- Error handling
"""

import os
import logging
from typing import List, Dict, Any, Optional, Generator, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

import requests

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    QWEN = "qwen"
    DEEPSEEK = "deepseek"


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    thinking_content: Optional[str] = None  # For deep thinking mode
    tokens_used: int = 0
    model: str = ""
    finish_reason: str = ""


@dataclass 
class Message:
    """Chat message."""
    role: str  # 'user', 'assistant', 'system'
    content: str


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Send chat completion request."""
        pass
    
    @abstractmethod
    def chat_with_deep_thought(
        self,
        messages: List[Message],
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Send chat with extended reasoning (deep thought mode)."""
        pass


class QwenClient(BaseLLMClient):
    """
    Qwen LLM client using DashScope API.
    
    Supports:
    - qwen-turbo
    - qwen-plus
    - qwen-max
    """
    
    BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    
    def __init__(self, api_key: str, model: str = "qwen-plus"):
        self.api_key = api_key
        self.model = model
    
    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Send chat completion to Qwen."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {"role": m.role, "content": m.content}
                    for m in messages
                ]
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "result_format": "message"
            }
        }
        
        if stream:
            payload["parameters"]["incremental_output"] = True
            return self._stream_response(headers, payload)
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            output = data.get("output", {})
            choices = output.get("choices", [{}])
            message = choices[0].get("message", {}) if choices else {}
            usage = data.get("usage", {})
            
            return LLMResponse(
                content=message.get("content", ""),
                tokens_used=usage.get("total_tokens", 0),
                model=self.model,
                finish_reason=output.get("finish_reason", "")
            )
        
        except Exception as e:
            logger.error(f"Qwen API error: {str(e)}")
            raise
    
    def _stream_response(
        self,
        headers: Dict,
        payload: Dict
    ) -> Generator[str, None, None]:
        """Stream response from Qwen."""
        headers["X-DashScope-SSE"] = "enable"
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=120
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data:'):
                        import json
                        data = json.loads(line[5:])
                        output = data.get("output", {})
                        choices = output.get("choices", [{}])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            if content:
                                yield content
        
        except Exception as e:
            logger.error(f"Qwen streaming error: {str(e)}")
            raise
    
    def chat_with_deep_thought(
        self,
        messages: List[Message],
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Extended reasoning mode for complex queries.
        
        Uses a chain-of-thought prompt to encourage detailed reasoning.
        """
        # Prepend system message for deep thinking
        system_msg = Message(
            role="system",
            content=(
                "You are a research assistant with deep analytical capabilities. "
                "For this query, think step by step:\n"
                "1. First, analyze the question carefully\n"
                "2. Consider multiple perspectives and approaches\n"
                "3. Reason through each aspect systematically\n"
                "4. Synthesize your findings into a comprehensive answer\n"
                "Show your reasoning process before giving the final answer."
            )
        )
        
        enhanced_messages = [system_msg] + messages
        
        response = self.chat(
            messages=enhanced_messages,
            temperature=0.3,  # Lower temperature for more focused reasoning
            max_tokens=max_tokens
        )
        
        # Try to extract thinking vs answer
        content = response.content
        thinking = None
        
        if "Final Answer:" in content:
            parts = content.split("Final Answer:", 1)
            thinking = parts[0].strip()
            content = parts[1].strip()
        elif "Therefore:" in content:
            parts = content.split("Therefore:", 1)
            thinking = parts[0].strip()
            content = "Therefore: " + parts[1].strip()
        
        response.thinking_content = thinking
        response.content = content
        
        return response


class DeepSeekClient(BaseLLMClient):
    """
    DeepSeek LLM client using OpenAI-compatible API.
    
    Supports:
    - deepseek-chat
    - deepseek-coder
    - deepseek-reasoner (for deep thinking)
    """
    
    BASE_URL = "https://api.deepseek.com/v1/chat/completions"
    
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model
    
    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Send chat completion to DeepSeek."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        if stream:
            return self._stream_response(headers, payload)
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            usage = data.get("usage", {})
            
            return LLMResponse(
                content=message.get("content", ""),
                tokens_used=usage.get("total_tokens", 0),
                model=self.model,
                finish_reason=choice.get("finish_reason", "")
            )
        
        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            raise
    
    def _stream_response(
        self,
        headers: Dict,
        payload: Dict
    ) -> Generator[str, None, None]:
        """Stream response from DeepSeek."""
        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=120
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data:') and line != 'data: [DONE]':
                        import json
                        data = json.loads(line[5:])
                        choices = data.get("choices", [{}])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
        
        except Exception as e:
            logger.error(f"DeepSeek streaming error: {str(e)}")
            raise
    
    def chat_with_deep_thought(
        self,
        messages: List[Message],
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Extended reasoning mode using DeepSeek-Reasoner.
        
        DeepSeek-Reasoner is specifically designed for complex reasoning tasks.
        """
        # Use reasoning model if available
        original_model = self.model
        self.model = "deepseek-reasoner"
        
        try:
            # Add reasoning instruction
            enhanced_messages = messages.copy()
            if enhanced_messages and enhanced_messages[0].role != "system":
                enhanced_messages.insert(0, Message(
                    role="system",
                    content="Think deeply and reason step by step. Show your reasoning process."
                ))
            
            response = self.chat(
                messages=enhanced_messages,
                temperature=0.2,
                max_tokens=max_tokens
            )
            
            return response
        
        finally:
            self.model = original_model


class LLMService:
    """
    Unified LLM service supporting multiple providers.
    
    Usage:
        service = LLMService()
        service.set_api_key('qwen', 'your-api-key')
        response = service.chat(messages, provider='qwen', model='qwen-plus')
    """
    
    # Default models per provider
    DEFAULT_MODELS = {
        'qwen': 'qwen-plus',
        'deepseek': 'deepseek-chat',
        'openai': 'gpt-4o-mini',
        'anthropic': 'claude-3-5-sonnet-20241022'
    }
    
    def __init__(self):
        self._clients: Dict[str, BaseLLMClient] = {}
        self._api_keys: Dict[str, str] = {}
    
    def set_api_key(self, provider: str, api_key: str, model: str = None):
        """Set API key for a provider with optional model."""
        provider = provider.lower()
        self._api_keys[provider] = api_key
        
        # Use default model if not specified
        model = model or self.DEFAULT_MODELS.get(provider, 'default')
        
        # Create or update client
        if provider == 'qwen':
            self._clients[provider] = QwenClient(api_key, model=model)
        elif provider == 'deepseek':
            self._clients[provider] = DeepSeekClient(api_key, model=model)
    
    def get_client(self, provider: str, model: str = None) -> BaseLLMClient:
        """Get client for a provider, optionally with a specific model."""
        provider = provider.lower()
        
        if provider not in self._clients:
            if provider not in self._api_keys:
                raise ValueError(f"API key not set for provider: {provider}")
            self.set_api_key(provider, self._api_keys[provider])
        
        client = self._clients[provider]
        
        # Update model if specified
        if model:
            client.model = model
        
        return client
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        provider: str = "qwen",
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """
        Send chat completion to specified provider.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            provider: LLM provider ('qwen' or 'deepseek')
            model: Specific model to use (e.g., 'qwen-plus', 'deepseek-chat')
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stream: Whether to stream response
            
        Returns:
            LLMResponse or generator for streaming
        """
        client = self.get_client(provider, model)
        
        msg_objects = [
            Message(role=m['role'], content=m['content'])
            for m in messages
        ]
        
        return client.chat(
            messages=msg_objects,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
    
    def chat_with_deep_thought(
        self,
        messages: List[Dict[str, str]],
        provider: str = "deepseek",
        model: str = None,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Chat with extended reasoning (deep thought mode).
        
        Args:
            messages: List of message dicts
            provider: LLM provider (deepseek recommended)
            model: Specific model to use
            max_tokens: Maximum tokens
            
        Returns:
            LLMResponse with thinking_content
        """
        client = self.get_client(provider, model)
        
        msg_objects = [
            Message(role=m['role'], content=m['content'])
            for m in messages
        ]
        
        return client.chat_with_deep_thought(
            messages=msg_objects,
            max_tokens=max_tokens
        )
    
    def generate_with_context(
        self,
        query: str,
        context: str,
        system_prompt: str = None,
        provider: str = "qwen",
        temperature: float = 0.7
    ) -> LLMResponse:
        """
        Generate response using RAG context.
        
        Args:
            query: User query
            context: Retrieved context
            system_prompt: Optional system prompt
            provider: LLM provider
            temperature: Sampling temperature
            
        Returns:
            LLMResponse
        """
        default_system = (
            "You are a helpful research assistant. Answer the user's question "
            "based on the provided context. If the context doesn't contain "
            "relevant information, say so and provide what help you can."
        )
        
        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ]
        
        return self.chat(
            messages=messages,
            provider=provider,
            temperature=temperature
        )


# Singleton instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
