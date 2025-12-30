"""
Agent Package

This package contains the LangGraph-based agent implementation:
- state.py: AgentState TypedDict and SlidingWindowManager
- memory.py: MemoryManager for long-term memory
- graph.py: Main LangGraph workflow
"""

from .state import AgentState, SlidingWindowManager, create_initial_state
from .memory import MemoryManager, get_memory_manager
from .graph import KnowledgeBaseAgent, create_agent, get_agent

__all__ = [
    'AgentState',
    'SlidingWindowManager',
    'create_initial_state',
    'MemoryManager',
    'get_memory_manager',
    'KnowledgeBaseAgent',
    'create_agent',
    'get_agent'
]
