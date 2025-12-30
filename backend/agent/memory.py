"""
Memory Manager

This module handles long-term memory operations:
1. Summarize conversation insights
2. Store in ChromaDB long_term_memory collection
3. Retrieve relevant memories for context
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from database.chroma_client import ChromaDBClient
from services.llm_service import LLMService, get_llm_service
from services.ingestion import IngestionService, get_ingestion_service

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages long-term memory for the knowledge base agent.
    
    Responsibilities:
    1. Summarize conversations into insights
    2. Store insights as embeddings in ChromaDB
    3. Retrieve relevant memories for context augmentation
    
    Memory Types:
    - insight: Key learnings from conversations
    - summary: Session summaries
    - preference: User preferences and patterns
    """
    
    # Summarization prompt
    SUMMARIZE_PROMPT = """Analyze this conversation and extract key insights.
Focus on:
1. Main topics discussed
2. Important conclusions or decisions
3. User's interests and research focus
4. Any action items or follow-ups

Conversation:
{conversation}

Provide a concise summary (2-3 sentences) capturing the most important insights."""

    def __init__(
        self,
        chroma_client: ChromaDBClient = None,
        llm_service: LLMService = None,
        ingestion_service: IngestionService = None
    ):
        self._chroma_client = chroma_client
        self._llm_service = llm_service
        self._ingestion_service = ingestion_service
    
    @property
    def chroma_client(self) -> ChromaDBClient:
        if self._chroma_client is None:
            self._chroma_client = ChromaDBClient()
        return self._chroma_client
    
    @property
    def llm_service(self) -> LLMService:
        if self._llm_service is None:
            self._llm_service = get_llm_service()
        return self._llm_service
    
    @property
    def ingestion_service(self) -> IngestionService:
        if self._ingestion_service is None:
            self._ingestion_service = get_ingestion_service()
        return self._ingestion_service
    
    def summarize_conversation(
        self,
        messages: List[Dict[str, Any]],
        provider: str = "qwen"
    ) -> Optional[str]:
        """
        Summarize a conversation into key insights.
        
        Args:
            messages: Conversation messages
            provider: LLM provider for summarization
            
        Returns:
            Summary string or None if failed
        """
        if not messages or len(messages) < 2:
            return None
        
        # Format conversation
        conversation_text = ""
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:500]  # Truncate long messages
            conversation_text += f"{role.upper()}: {content}\n\n"
        
        prompt = self.SUMMARIZE_PROMPT.format(conversation=conversation_text)
        
        try:
            response = self.llm_service.chat(
                messages=[{"role": "user", "content": prompt}],
                provider=provider,
                temperature=0.3,
                max_tokens=256
            )
            return response.content.strip()
        
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            return None
    
    def save_memory(
        self,
        user_id: int,
        session_id: int,
        content: str,
        memory_type: str = "insight"
    ) -> Optional[str]:
        """
        Save a memory entry to long-term storage.
        
        Args:
            user_id: User ID
            session_id: Session ID
            content: Memory content
            memory_type: Type of memory
            
        Returns:
            Memory ID or None if failed
        """
        try:
            # Generate embedding
            embedding = self.ingestion_service.get_embedding(content)
            
            # Store in ChromaDB
            memory_id = self.chroma_client.add_memory(
                user_id=user_id,
                session_id=session_id,
                content=content,
                embedding=embedding,
                memory_type=memory_type
            )
            
            logger.info(f"Saved memory {memory_id} for user {user_id}")
            return memory_id
        
        except Exception as e:
            logger.error(f"Failed to save memory: {str(e)}")
            return None
    
    def save_session_summary(
        self,
        user_id: int,
        session_id: int,
        messages: List[Dict[str, Any]],
        provider: str = "qwen"
    ) -> Optional[str]:
        """
        Summarize and save a session to long-term memory.
        
        This should be called when a session becomes inactive
        or reaches a certain length.
        
        Args:
            user_id: User ID
            session_id: Session ID
            messages: Session messages
            provider: LLM provider
            
        Returns:
            Memory ID or None
        """
        # Generate summary
        summary = self.summarize_conversation(messages, provider)
        
        if not summary:
            return None
        
        # Save as summary type
        return self.save_memory(
            user_id=user_id,
            session_id=session_id,
            content=summary,
            memory_type="summary"
        )
    
    def retrieve_memories(
        self,
        user_id: int,
        query: str,
        n_results: int = 3,
        memory_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for a query.
        
        Args:
            user_id: User ID
            query: Query to match
            n_results: Number of memories to retrieve
            memory_type: Optional type filter
            
        Returns:
            List of memory dictionaries
        """
        try:
            # Generate query embedding
            query_embedding = self.ingestion_service.get_embedding(query)
            
            # Query ChromaDB
            results = self.chroma_client.query_memories(
                user_id=user_id,
                query_embedding=query_embedding,
                n_results=n_results,
                memory_type=memory_type
            )
            
            if not results or not results.get('ids') or not results['ids'][0]:
                return []
            
            memories = []
            for i, (mem_id, content, distance, metadata) in enumerate(
                zip(
                    results['ids'][0],
                    results['documents'][0],
                    results['distances'][0],
                    results['metadatas'][0]
                )
            ):
                memories.append({
                    'id': mem_id,
                    'content': content,
                    'score': 1 - distance,
                    'session_id': metadata.get('session_id'),
                    'date': metadata.get('date'),
                    'memory_type': metadata.get('memory_type')
                })
            
            return memories
        
        except Exception as e:
            logger.error(f"Memory retrieval failed: {str(e)}")
            return []
    
    def format_memories_for_context(
        self,
        memories: List[Dict[str, Any]]
    ) -> str:
        """
        Format memories as context string for LLM.
        
        Args:
            memories: List of memory dictionaries
            
        Returns:
            Formatted context string
        """
        if not memories:
            return ""
        
        lines = ["--- Relevant Past Insights ---"]
        for mem in memories:
            date = mem.get('date', 'Unknown date')
            content = mem.get('content', '')
            lines.append(f"[{date}] {content}")
        
        return "\n".join(lines)
    
    def should_summarize(
        self,
        messages: List[Dict[str, Any]],
        threshold: int = 10
    ) -> bool:
        """
        Check if a session should be summarized.
        
        Args:
            messages: Session messages
            threshold: Message count threshold
            
        Returns:
            Whether to summarize
        """
        # Count user messages
        user_messages = [m for m in messages if m.get('role') == 'user']
        return len(user_messages) >= threshold
    
    def cleanup_old_memories(
        self,
        user_id: int,
        days_old: int = 90
    ) -> int:
        """
        Remove memories older than specified days.
        
        Args:
            user_id: User ID
            days_old: Age threshold in days
            
        Returns:
            Number of memories removed
        """
        # This would require date-based filtering in ChromaDB
        # For now, this is a placeholder
        logger.info(f"Memory cleanup requested for user {user_id}")
        return 0


# Singleton instance
_memory_manager = None


def get_memory_manager() -> MemoryManager:
    """Get or create the memory manager singleton."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
