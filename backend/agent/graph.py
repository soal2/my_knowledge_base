"""
LangGraph Knowledge Base Agent

This module implements the main agent workflow using LangGraph StateGraph:

Workflow:
1. retrieve_context: Get relevant documents and memories
2. route: Decide between standard RAG or deep thinking
3. generate_standard: Standard RAG generation
4. generate_deep_thought: Extended reasoning for complex queries
5. save_memory: Optionally save insights to long-term memory

Context Management:
- Short-term: Sliding window over recent messages
- Long-term: Async summarization and retrieval from ChromaDB
"""

import logging
from typing import Dict, Any, Optional, List, Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState, SlidingWindowManager, create_initial_state
from agent.memory import MemoryManager, get_memory_manager
from services.retrieval import RetrievalService, get_retrieval_service
from services.llm_service import LLMService, get_llm_service
from database.models import ChatMessage, ChatSession, MessageRole, db

logger = logging.getLogger(__name__)


# Helper to safely extract role/content from LangChain or dict messages
def _get_role(msg: Any) -> Optional[str]:
    if isinstance(msg, dict):
        return msg.get('role')
    if hasattr(msg, 'role'):
        return getattr(msg, 'role')
    if hasattr(msg, 'type'):
        return getattr(msg, 'type')
    return None


def _get_content(msg: Any) -> str:
    if isinstance(msg, dict):
        return msg.get('content', '')
    if hasattr(msg, 'content'):
        return getattr(msg, 'content') or ''
    return ''


def _normalize_message(msg: Any) -> Dict[str, str]:
    """Return a plain dict {role, content} for downstream use."""
    role = _get_role(msg)
    # Map LangChain 'ai' to OpenAI 'assistant'
    if role == 'ai':
        role = 'assistant'
    return {
        'role': role or 'user',
        'content': _get_content(msg)
    }


# =============================================================================
# Node Functions
# =============================================================================

def retrieve_context(state: AgentState) -> Dict[str, Any]:
    """
    Retrieve relevant documents and memories for the query.
    
    This node:
    1. Searches the knowledge base for relevant chunks
    2. Retrieves relevant long-term memories
    3. Formats context for the LLM
    """
    logger.info(f"Retrieving context for query: {state['query'][:50]}...")
    
    retrieval_service = get_retrieval_service()
    memory_manager = get_memory_manager()
    
    try:
        # Retrieve document chunks
        doc_ids = state.get('doc_ids')
        result = retrieval_service.hybrid_retrieve(
            query=state['query'],
            user_id=state['user_id'],
            top_k=5,
            doc_ids=doc_ids if doc_ids else [],
            include_memories=True
        )
        
        return {
            'context_chunks': result['documents'],
            'context_text': result['context'],
            'memories': result['memories']
        }
    
    except Exception as e:
        logger.error(f"Context retrieval error: {str(e)}")
        return {
            'context_chunks': [],
            'context_text': "",
            'memories': [],
            'error': f"Retrieval error: {str(e)}"
        }


def route_generation(state: AgentState) -> Literal["generate_standard", "generate_deep_thought"]:
    """
    Route to appropriate generation node based on is_deep_thought flag.
    
    Routing Logic:
    - If is_deep_thought is True: Route to deep thinking node
    - Otherwise: Route to standard RAG generation
    """
    if state.get('is_deep_thought', False):
        logger.info("Routing to deep thought generation")
        return "generate_deep_thought"
    else:
        logger.info("Routing to standard generation")
        return "generate_standard"


def generate_standard(state: AgentState) -> Dict[str, Any]:
    """
    Standard RAG generation node.
    
    Uses retrieved context to generate a focused response.
    """
    logger.info("Generating standard RAG response")
    
    llm_service = get_llm_service()
    sliding_window = SlidingWindowManager()
    
    # Build prompt with context
    system_prompt = """You are a knowledgeable research assistant for a personal knowledge base.
Your role is to help users understand their uploaded academic papers and documents.

Guidelines:
1. Base your answers on the provided context from the user's documents
2. Be precise and cite sources when possible
3. If the context doesn't contain enough information, say so clearly
4. Provide helpful suggestions for further exploration"""

    # Get sliding window of messages
    context_messages = sliding_window.get_context_messages(state['messages'])
    
    # Build messages for LLM
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add context if available
    if state['context_text']:
        context_msg = f"Relevant context from your documents:\n\n{state['context_text']}"
        messages.append({"role": "system", "content": context_msg})
    
    # Add conversation history
    for msg in context_messages:
        role = _get_role(msg)
        if role in ['user', 'assistant', 'ai']:
            normalized = _normalize_message(msg)
            messages.append(normalized)
    
    # Add current query
    messages.append({"role": "user", "content": state['query']})
    
    try:
        response = llm_service.chat(
            messages=messages,
            provider=state.get('provider', 'qwen'),
            model=state.get('model'),
            temperature=0.7,
            max_tokens=2048
        )
        
        return {
            'response': response.content,
            'tokens_used': state.get('tokens_used', 0) + response.tokens_used,
            'messages': [
                {"role": "user", "content": state['query']},
                {"role": "assistant", "content": response.content}
            ]
        }
    
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        return {
            'response': f"I apologize, but I encountered an error: {str(e)}",
            'error': str(e)
        }


def generate_deep_thought(state: AgentState) -> Dict[str, Any]:
    """
    Deep thinking generation node.
    
    Uses extended reasoning for complex queries:
    1. Chain-of-thought prompting
    2. Step-by-step analysis
    3. Multi-perspective consideration
    """
    logger.info("Generating deep thought response")
    
    llm_service = get_llm_service()
    sliding_window = SlidingWindowManager()
    
    # Enhanced system prompt for deep thinking
    system_prompt = """You are an expert research analyst with deep analytical capabilities.
For this complex query, you must:

1. **Analyze**: Break down the question into its core components
2. **Research**: Examine the provided context thoroughly
3. **Reason**: Consider multiple perspectives and approaches
4. **Synthesize**: Integrate your analysis into a comprehensive answer
5. **Conclude**: Provide clear conclusions with supporting evidence

Show your reasoning process step by step before giving the final answer.
Mark your final conclusion with "**Conclusion:**" """

    # Get context messages
    context_messages = sliding_window.get_context_messages(state['messages'])
    
    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add document context
    if state['context_text']:
        context_msg = f"=== Research Context ===\n\n{state['context_text']}\n=== End Context ==="
        messages.append({"role": "system", "content": context_msg})
    
    # Add memory context if available
    if state['memories']:
        memory_context = "\n=== Relevant Past Insights ===\n"
        for mem in state['memories']:
            memory_context += f"• {mem.get('content', '')}\n"
        memory_context += "=== End Insights ===\n"
        messages.append({"role": "system", "content": memory_context})
    
    # Add conversation history
    for msg in context_messages:
        role = _get_role(msg)
        if role in ['user', 'assistant', 'ai']:
            messages.append(_normalize_message(msg))
    
    # Add current query with emphasis
    messages.append({
        "role": "user",
        "content": f"Please analyze this question deeply:\n\n{state['query']}"
    })
    
    try:
        # Use deep thought mode
        response = llm_service.chat_with_deep_thought(
            messages=messages,
            provider=state.get('provider', 'deepseek'),
            model=state.get('model'),
            max_tokens=4096
        )
        
        return {
            'response': response.content,
            'thinking_content': response.thinking_content,
            'tokens_used': state.get('tokens_used', 0) + response.tokens_used,
            'messages': [
                {"role": "user", "content": state['query']},
                {"role": "assistant", "content": response.content}
            ]
        }
    
    except Exception as e:
        logger.error(f"Deep thought generation error: {str(e)}")
        return {
            'response': f"I apologize, but I encountered an error during analysis: {str(e)}",
            'error': str(e)
        }


def check_save_memory(state: AgentState) -> Literal["save_memory", "end"]:
    """
    Check if we should save insights to long-term memory.
    
    Criteria:
    - Deep thought responses often generate insights
    - Every N messages, summarize the conversation
    """
    # Save after deep thought
    if state.get('is_deep_thought') and state.get('response'):
        return "save_memory"
    
    # Check if we should summarize (every 10 user messages)
    user_messages = [m for m in state['messages'] if _get_role(m) == 'user']
    if len(user_messages) > 0 and len(user_messages) % 10 == 0:
        return "save_memory"
    
    return "end"


def save_memory(state: AgentState) -> Dict[str, Any]:
    """
    Save insights to long-term memory.
    
    For deep thought responses, extracts and saves key insights.
    For regular conversations, creates periodic summaries.
    """
    logger.info("Saving insights to long-term memory")
    
    memory_manager = get_memory_manager()
    
    try:
        if state.get('is_deep_thought'):
            # For deep thought, save a condensed insight
            content = f"Deep analysis on: {state['query'][:100]}... Key insight: {state['response'][:200]}..."
            
            memory_manager.save_memory(
                user_id=state['user_id'],
                session_id=state['session_id'],
                content=content,
                memory_type="insight"
            )
        else:
            # Periodic conversation summary
            # Normalize messages for summarization
            normalized_msgs = [_normalize_message(m) for m in state['messages']]
            memory_manager.save_session_summary(
                user_id=state['user_id'],
                session_id=state['session_id'],
                messages=normalized_msgs,
                provider=state.get('provider', 'qwen')
            )
        
        return {}  # No state changes needed
    
    except Exception as e:
        logger.error(f"Memory save error: {str(e)}")
        return {}  # Don't fail the workflow for memory errors


# =============================================================================
# Graph Construction
# =============================================================================

def build_agent_graph() -> StateGraph:
    """
    Build the LangGraph agent workflow.
    
    Graph Structure:
    
        START
          │
          ▼
    ┌─────────────────┐
    │ retrieve_context│
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │     route       │ (conditional)
    └────────┬────────┘
             │
        ┌────┴────┐
        │         │
        ▼         ▼
    ┌───────┐ ┌──────────────┐
    │standard│ │ deep_thought │
    └───┬───┘ └──────┬───────┘
        │            │
        └────┬───────┘
             │
             ▼
    ┌─────────────────┐
    │  check_memory   │ (conditional)
    └────────┬────────┘
             │
        ┌────┴────┐
        │         │
        ▼         ▼
    ┌───────┐   ┌───┐
    │ save  │   │END│
    └───┬───┘   └───┘
        │
        ▼
      ┌───┐
      │END│
      └───┘
    """
    # Create graph builder
    builder = StateGraph(AgentState)
    
    # Add nodes
    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("generate_standard", generate_standard)
    builder.add_node("generate_deep_thought", generate_deep_thought)
    builder.add_node("save_memory", save_memory)
    
    # Add edges
    builder.add_edge(START, "retrieve_context")
    
    # Conditional routing after retrieval
    builder.add_conditional_edges(
        "retrieve_context",
        route_generation,
        {
            "generate_standard": "generate_standard",
            "generate_deep_thought": "generate_deep_thought"
        }
    )
    
    # After generation, check if we should save memory
    builder.add_conditional_edges(
        "generate_standard",
        check_save_memory,
        {
            "save_memory": "save_memory",
            "end": END
        }
    )
    
    builder.add_conditional_edges(
        "generate_deep_thought",
        check_save_memory,
        {
            "save_memory": "save_memory",
            "end": END
        }
    )
    
    # Memory save leads to end
    builder.add_edge("save_memory", END)
    
    return builder


# =============================================================================
# Agent Class
# =============================================================================

class KnowledgeBaseAgent:
    """
    High-level agent interface for the Knowledge Base system.
    
    Wraps the LangGraph workflow with convenient methods
    for chat, history management, and configuration.
    """
    
    def __init__(self, use_checkpointing: bool = True):
        """
        Initialize the agent.
        
        Args:
            use_checkpointing: Enable state persistence
        """
        self.graph_builder = build_agent_graph()
        
        # Compile with optional checkpointing
        if use_checkpointing:
            self.checkpointer = MemorySaver()
            self.graph = self.graph_builder.compile(checkpointer=self.checkpointer)
        else:
            self.graph = self.graph_builder.compile()
        
        self.llm_service = get_llm_service()
    
    def configure_llm(self, provider: str, api_key: str):
        """Set API key for LLM provider."""
        self.llm_service.set_api_key(provider, api_key)
    
    def chat(
        self,
        user_id: int,
        session_id: int,
        query: str,
        messages: Optional[List[Dict[str, Any]]] = None,
        is_deep_thought: bool = False,
        doc_ids: Optional[List[int]] = None,
        provider: str = "qwen",
        model: str = None
    ) -> Dict[str, Any]:
        """
        Process a chat message through the agent.
        
        Args:
            user_id: User ID
            session_id: Session ID
            query: User query
            messages: Previous messages for context
            is_deep_thought: Enable deep thinking mode
            doc_ids: Optional document filter
            provider: LLM provider
            model: Specific model to use
            
        Returns:
            Dict with 'response', 'thinking_content', 'tokens_used'
        """
        # Create initial state
        initial_state = create_initial_state(
            user_id=user_id,
            session_id=session_id,
            query=query,
            messages=messages or [],
            is_deep_thought=is_deep_thought,
            doc_ids=doc_ids,
            provider=provider,
            model=model
        )
        
        # Configure thread for checkpointing
        config = {
            "configurable": {
                "thread_id": f"user_{user_id}_session_{session_id}"
            }
        }
        
        # Run the graph
        try:
            result = self.graph.invoke(initial_state, config=config)
            
            return {
                'response': result.get('response', ''),
                'thinking_content': result.get('thinking_content'),
                'tokens_used': result.get('tokens_used', 0),
                'context_chunks': result.get('context_chunks', []),
                'error': result.get('error')
            }
        
        except Exception as e:
            logger.error(f"Agent error: {str(e)}")
            return {
                'response': f"I encountered an error: {str(e)}",
                'thinking_content': None,
                'tokens_used': 0,
                'error': str(e)
            }
    
    async def chat_stream(
        self,
        user_id: int,
        session_id: int,
        query: str,
        messages: Optional[List[Dict[str, Any]]] = None,
        is_deep_thought: bool = False,
        doc_ids: Optional[List[int]] = None,
        provider: str = "qwen",
        model: str = None
    ):
        """
        Stream chat response (for real-time UI updates).
        
        Yields chunks of the response as they're generated.
        """
        # For streaming, we'd need to modify the graph to support
        # streaming outputs. This is a simplified version.
        result = self.chat(
            user_id=user_id,
            session_id=session_id,
            query=query,
            messages=messages,
            is_deep_thought=is_deep_thought,
            doc_ids=doc_ids,
            provider=provider,
            model=model
        )
        
        # Simulate streaming by yielding response
        yield result
    
    def save_to_database(
        self,
        session_id: int,
        query: str,
        response: str,
        is_deep_thought: bool = False,
        thinking_content: Optional[str] = None,
        tokens_used: int = 0
    ):
        """
        Save the conversation turn to the database.
        
        Args:
            session_id: Chat session ID
            query: User query
            response: Agent response
            is_deep_thought: Whether deep thinking was used
            thinking_content: Reasoning process
            tokens_used: Tokens consumed
        """
        try:
            # Save user message
            user_msg = ChatMessage(
                session_id=session_id,
                role=MessageRole.USER,
                content=query
            )
            db.session.add(user_msg)
            
            # Save assistant message
            ai_msg = ChatMessage(
                session_id=session_id,
                role=MessageRole.AI,
                content=response,
                is_deep_thought=is_deep_thought,
                thinking_content=thinking_content,
                tokens_used=tokens_used
            )
            db.session.add(ai_msg)
            
            # Update session last_active
            session = ChatSession.query.get(session_id)
            if session:
                from datetime import datetime
                session.last_active_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Database save error: {str(e)}")
            db.session.rollback()


# =============================================================================
# Factory Function
# =============================================================================

_agent_instance = None


def create_agent(use_checkpointing: bool = True) -> KnowledgeBaseAgent:
    """
    Create or get the agent instance.
    
    Args:
        use_checkpointing: Enable state persistence
        
    Returns:
        KnowledgeBaseAgent instance
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = KnowledgeBaseAgent(use_checkpointing=use_checkpointing)
    return _agent_instance


def get_agent() -> KnowledgeBaseAgent:
    """Get the existing agent instance or create one."""
    return create_agent()
