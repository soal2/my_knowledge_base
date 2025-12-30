"""
ChromaDB Client for Vector Database Operations

This module provides a Singleton pattern implementation for ChromaDB client
initialization and collection management. It handles two primary collections:

1. knowledge_base: Stores parsed document chunks with embeddings
   - Metadata: {user_id, doc_id, source, page, chunk_index}
   
2. long_term_memory: Stores summarized insights from conversations
   - Metadata: {user_id, session_id, date, memory_type}

All operations enforce user_id isolation for data privacy.
"""

import os
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime

import chromadb
from chromadb.config import Settings


class ChromaDBClient:
    """
    Singleton ChromaDB client for vector database operations.
    
    This class ensures only one ChromaDB client instance exists throughout
    the application lifecycle, providing thread-safe access to collections.
    
    Collections:
        - knowledge_base: Document chunks from parsed papers/reports
        - long_term_memory: Summarized insights from chat sessions
    
    Usage:
        client = ChromaDBClient()
        kb_collection = client.get_knowledge_base_collection()
        memory_collection = client.get_memory_collection()
    """
    
    _instance: Optional['ChromaDBClient'] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False
    
    # Collection names
    KNOWLEDGE_BASE_COLLECTION = "knowledge_base"
    LONG_TERM_MEMORY_COLLECTION = "long_term_memory"
    
    def __new__(cls, persist_directory: str = None) -> 'ChromaDBClient':
        """
        Create or return the singleton instance.
        
        Args:
            persist_directory: Directory for ChromaDB persistence.
                              Defaults to './data/chroma_db'
        """
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, persist_directory: str = None) -> None:
        """
        Initialize the ChromaDB client and collections.
        
        Args:
            persist_directory: Directory for ChromaDB persistence.
                              Defaults to './data/chroma_db'
        """
        # Prevent re-initialization
        if ChromaDBClient._initialized:
            return
            
        with ChromaDBClient._lock:
            if ChromaDBClient._initialized:
                return
                
            self._persist_directory = persist_directory or os.getenv(
                'CHROMA_PERSIST_DIR', 
                './data/chroma_db'
            )
            
            # Ensure directory exists
            os.makedirs(self._persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client with persistence
            self._client = chromadb.PersistentClient(
                path=self._persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize collections
            self._init_collections()
            
            ChromaDBClient._initialized = True
    
    def _init_collections(self) -> None:
        """Initialize or get existing collections."""
        # Knowledge Base Collection
        # Stores document chunks with semantic embeddings
        self._knowledge_base = self._client.get_or_create_collection(
            name=self.KNOWLEDGE_BASE_COLLECTION,
            metadata={
                "description": "Parsed document chunks from academic papers and reports",
                "hnsw:space": "cosine"  # Use cosine similarity
            }
        )
        
        # Long-term Memory Collection
        # Stores summarized insights from conversations
        self._long_term_memory = self._client.get_or_create_collection(
            name=self.LONG_TERM_MEMORY_COLLECTION,
            metadata={
                "description": "Summarized insights from past conversations",
                "hnsw:space": "cosine"
            }
        )
    
    @property
    def client(self) -> chromadb.ClientAPI:
        """Get the underlying ChromaDB client."""
        return self._client
    
    def get_knowledge_base_collection(self) -> chromadb.Collection:
        """Get the knowledge base collection."""
        return self._knowledge_base
    
    def get_memory_collection(self) -> chromadb.Collection:
        """Get the long-term memory collection."""
        return self._long_term_memory
    
    # ========================================================================
    # Knowledge Base Operations
    # ========================================================================
    
    def add_document_chunks(
        self,
        user_id: int,
        doc_id: int,
        chunks: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]] = None,
        source: str = None
    ) -> List[str]:
        """
        Add document chunks to the knowledge base.
        
        Args:
            user_id: User ID for data isolation
            doc_id: Document ID from FileDocument table
            chunks: List of text chunks
            embeddings: List of embedding vectors
            metadatas: Optional list of additional metadata per chunk
            source: Source filename
            
        Returns:
            List of generated chunk IDs
        """
        chunk_ids = []
        full_metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"user_{user_id}_doc_{doc_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            
            # Build metadata with user isolation
            meta = {
                "user_id": user_id,
                "doc_id": doc_id,
                "source": source or f"document_{doc_id}",
                "chunk_index": i,
                "created_at": datetime.now().isoformat()
            }
            
            # Merge additional metadata if provided
            if metadatas and i < len(metadatas):
                meta.update(metadatas[i])
            
            full_metadatas.append(meta)
        
        self._knowledge_base.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=full_metadatas
        )
        
        return chunk_ids
    
    def query_knowledge_base(
        self,
        user_id: int,
        query_embedding: List[float],
        n_results: int = 5,
        doc_ids: List[int] = None
    ) -> Dict[str, Any]:
        """
        Query the knowledge base with user isolation.
        
        Args:
            user_id: User ID for filtering
            query_embedding: Query embedding vector
            n_results: Number of results to return
            doc_ids: Optional list of doc_ids to filter by
            
        Returns:
            Query results with documents, distances, and metadata
        """
        # Build where clause for user isolation
        where_clause = {"user_id": user_id}
        
        # Add document filter if specified
        if doc_ids:
            where_clause = {
                "$and": [
                    {"user_id": user_id},
                    {"doc_id": {"$in": doc_ids}}
                ]
            }
        
        results = self._knowledge_base.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    def delete_document_chunks(self, user_id: int, doc_id: int) -> None:
        """
        Delete all chunks for a specific document.
        
        Args:
            user_id: User ID for verification
            doc_id: Document ID to delete
        """
        self._knowledge_base.delete(
            where={
                "$and": [
                    {"user_id": user_id},
                    {"doc_id": doc_id}
                ]
            }
        )
    
    def delete_user_documents(self, user_id: int) -> None:
        """
        Delete all document chunks for a user.
        
        Args:
            user_id: User ID whose documents to delete
        """
        self._knowledge_base.delete(
            where={"user_id": user_id}
        )
    
    def get_document_chunk_count(self, user_id: int, doc_id: int = None) -> int:
        """
        Get the count of chunks for a user or specific document.
        
        Args:
            user_id: User ID for filtering
            doc_id: Optional document ID for filtering
            
        Returns:
            Number of chunks
        """
        where_clause = {"user_id": user_id}
        if doc_id:
            where_clause = {
                "$and": [
                    {"user_id": user_id},
                    {"doc_id": doc_id}
                ]
            }
        
        results = self._knowledge_base.get(
            where=where_clause,
            include=[]  # Only get IDs
        )
        
        return len(results['ids'])
    
    # ========================================================================
    # Long-term Memory Operations
    # ========================================================================
    
    def add_memory(
        self,
        user_id: int,
        session_id: int,
        content: str,
        embedding: List[float],
        memory_type: str = "insight"
    ) -> str:
        """
        Add a memory entry to long-term memory.
        
        Args:
            user_id: User ID for data isolation
            session_id: Chat session ID
            content: Memory content (summarized insight)
            embedding: Embedding vector
            memory_type: Type of memory (insight, summary, preference)
            
        Returns:
            Generated memory ID
        """
        memory_id = f"user_{user_id}_session_{session_id}_memory_{datetime.now().timestamp()}"
        
        self._long_term_memory.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                "session_id": session_id,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "memory_type": memory_type,
                "created_at": datetime.now().isoformat()
            }]
        )
        
        return memory_id
    
    def query_memories(
        self,
        user_id: int,
        query_embedding: List[float],
        n_results: int = 5,
        memory_type: str = None
    ) -> Dict[str, Any]:
        """
        Query long-term memories with user isolation.
        
        Args:
            user_id: User ID for filtering
            query_embedding: Query embedding vector
            n_results: Number of results to return
            memory_type: Optional memory type filter
            
        Returns:
            Query results with memories and metadata
        """
        where_clause = {"user_id": user_id}
        
        if memory_type:
            where_clause = {
                "$and": [
                    {"user_id": user_id},
                    {"memory_type": memory_type}
                ]
            }
        
        results = self._long_term_memory.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    def delete_session_memories(self, user_id: int, session_id: int) -> None:
        """
        Delete all memories for a specific session.
        
        Args:
            user_id: User ID for verification
            session_id: Session ID to delete memories for
        """
        self._long_term_memory.delete(
            where={
                "$and": [
                    {"user_id": user_id},
                    {"session_id": session_id}
                ]
            }
        )
    
    def delete_user_memories(self, user_id: int) -> None:
        """
        Delete all memories for a user.
        
        Args:
            user_id: User ID whose memories to delete
        """
        self._long_term_memory.delete(
            where={"user_id": user_id}
        )
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all collections.
        
        Returns:
            Dictionary with collection counts and info
        """
        return {
            "knowledge_base": {
                "count": self._knowledge_base.count(),
                "name": self.KNOWLEDGE_BASE_COLLECTION
            },
            "long_term_memory": {
                "count": self._long_term_memory.count(),
                "name": self.LONG_TERM_MEMORY_COLLECTION
            }
        }
    
    def reset_collections(self) -> None:
        """
        Reset all collections. USE WITH CAUTION.
        
        This will delete all data in both collections.
        """
        self._client.delete_collection(self.KNOWLEDGE_BASE_COLLECTION)
        self._client.delete_collection(self.LONG_TERM_MEMORY_COLLECTION)
        self._init_collections()
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance. Mainly for testing purposes.
        """
        with cls._lock:
            cls._instance = None
            cls._initialized = False
