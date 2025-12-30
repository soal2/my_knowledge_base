"""
Agent State Definition

This module defines the state schema for the LangGraph agent,
including message history, context, and metadata.
"""

from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from dataclasses import dataclass, field
from datetime import datetime

from langgraph.graph.message import add_messages


def _get_role(msg: Any) -> Optional[str]:
    """Safely extract role from dict or LangChain message."""
    if isinstance(msg, dict):
        return msg.get('role')
    # LangChain messages expose `.type` or `.role`
    if hasattr(msg, 'role'):
        return getattr(msg, 'role')
    if hasattr(msg, 'type'):
        return getattr(msg, 'type')
    return None


def _get_content(msg: Any) -> str:
    """Safely extract content from dict or LangChain message."""
    if isinstance(msg, dict):
        return msg.get('content', '')
    if hasattr(msg, 'content'):
        return getattr(msg, 'content') or ''
    return ''


@dataclass
class ContextChunk:
    """Retrieved context chunk."""
    text: str
    source: str
    score: float
    page: Optional[int] = None


@dataclass
class Memory:
    """Long-term memory entry."""
    content: str
    date: str
    memory_type: str
    score: float = 0.0


class AgentState(TypedDict):
    """
    State schema for the Knowledge Base Agent.
    
    Attributes:
        messages: Conversation history (uses add_messages reducer)
        user_id: Current user ID for data isolation
        session_id: Current chat session ID
        
        # Query processing
        query: Current user query
        is_deep_thought: Whether to use extended reasoning
        
        # Retrieved context
        context_chunks: Retrieved document chunks
        context_text: Formatted context string
        memories: Retrieved long-term memories
        
        # Generation
        response: Generated response
        thinking_content: Reasoning process (for deep thought)
        
        # Metadata
        doc_ids: Optional document filter
        provider: LLM provider to use
        tokens_used: Total tokens used
        error: Error message if any
    """
    # Core conversation state
    messages: Annotated[List[Dict[str, Any]], add_messages]
    user_id: int
    session_id: int
    
    # Query processing
    query: str
    is_deep_thought: bool
    
    # Retrieved context
    context_chunks: List[Dict[str, Any]]
    context_text: str
    memories: List[Dict[str, Any]]
    
    # Generation
    response: str
    thinking_content: Optional[str]
    
    # Metadata
    doc_ids: Optional[List[int]]
    provider: str
    model: Optional[str]  # Specific model to use
    tokens_used: int
    error: Optional[str]


def create_initial_state(
    user_id: int,
    session_id: int,
    query: str,
    messages: List[Dict[str, Any]] = None,
    is_deep_thought: bool = False,
    doc_ids: List[int] = None,
    provider: str = "qwen",
    model: str = None
) -> AgentState:
    """
    Create initial agent state.
    
    Args:
        user_id: User ID
        session_id: Session ID
        query: User query
        messages: Previous messages (for context)
        is_deep_thought: Enable deep thinking mode
        doc_ids: Optional document filter
        provider: LLM provider
        model: Specific model to use
        
    Returns:
        Initial AgentState
    """
    return AgentState(
        messages=messages or [],
        user_id=user_id,
        session_id=session_id,
        query=query,
        is_deep_thought=is_deep_thought,
        context_chunks=[],
        context_text="",
        memories=[],
        response="",
        thinking_content=None,
        doc_ids=doc_ids,
        provider=provider,
        model=model,
        tokens_used=0,
        error=None
    )


# =============================================================================
# Sliding Window Context Management
# =============================================================================

class SlidingWindowManager:
    """
    Manages short-term context using sliding window.
    
    Keeps the most recent N messages for LLM context,
    while maintaining the full history for reference.
    """
    
    DEFAULT_WINDOW_SIZE = 10  # Number of message pairs to keep
    MAX_TOKENS_ESTIMATE = 4000  # Rough token limit for context
    
    def __init__(self, window_size: int = None):
        self.window_size = window_size or self.DEFAULT_WINDOW_SIZE
    
    def get_context_messages(
        self,
        messages: List[Dict[str, Any]],
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get messages for LLM context using sliding window.
        
        Args:
            messages: Full message history
            include_system: Whether to always include system message
            
        Returns:
            Windowed message list
        """
        if not messages:
            return []
        
        # Separate system messages
        system_msgs = [m for m in messages if _get_role(m) == 'system']
        other_msgs = [m for m in messages if _get_role(m) != 'system']
        
        # Take last N*2 messages (N conversation turns)
        window_msgs = other_msgs[-(self.window_size * 2):]
        
        # Combine with system message if requested
        if include_system and system_msgs:
            return [system_msgs[-1]] + window_msgs
        
        return window_msgs
    
    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Estimate token count for messages.
        
        Rough estimate: 1 token ≈ 4 characters (for English)
        """
        total_chars = sum(len(_get_content(m)) for m in messages)
        return total_chars // 4
    
    def fit_to_token_limit(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = None
    ) -> List[Dict[str, Any]]:
        """
        Trim messages to fit within token limit.
        
        Args:
            messages: Message list
            max_tokens: Maximum tokens (defaults to MAX_TOKENS_ESTIMATE)
            
        Returns:
            Trimmed message list
        """
        max_tokens = max_tokens or self.MAX_TOKENS_ESTIMATE
        
        while messages and self.estimate_tokens(messages) > max_tokens:
            # Remove oldest non-system message
            for i, msg in enumerate(messages):
                if _get_role(msg) != 'system':
                    messages.pop(i)
                    break
            else:
                # Only system messages left
                break
        
        return messages
