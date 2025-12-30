"""
Retrieval Service

This module implements hybrid retrieval with cross-encoder reranking:
1. Semantic search using ChromaDB vector similarity
2. Optional BM25 keyword matching
3. Cross-encoder reranking for improved relevance

The service enforces user_id isolation for all retrievals.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer, CrossEncoder

from database.chroma_client import ChromaDBClient
from services.ingestion import IngestionService, get_ingestion_service

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk with metadata."""
    text: str
    doc_id: int
    chunk_id: str
    source: str
    score: float
    page: Optional[int] = None
    section: Optional[str] = None
    rerank_score: Optional[float] = None


class RetrievalService:
    """
    Hybrid retrieval service with cross-encoder reranking.
    
    Retrieval Pipeline:
    1. Generate query embedding
    2. Retrieve candidates from ChromaDB (semantic search)
    3. Apply cross-encoder reranking
    4. Return top-k results
    
    Features:
    - User data isolation
    - Document filtering
    - Configurable reranking
    """
    
    # Default models
    DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Retrieval parameters
    DEFAULT_TOP_K = 5
    DEFAULT_CANDIDATES = 20  # Retrieve more candidates for reranking
    
    def __init__(
        self,
        embedding_model: str = None,
        reranker_model: str = None,
        use_reranking: bool = True
    ):
        """
        Initialize the retrieval service.
        
        Args:
            embedding_model: Model for query embedding
            reranker_model: Cross-encoder model for reranking
            use_reranking: Whether to apply reranking
        """
        self.embedding_model_name = embedding_model or self.DEFAULT_EMBEDDING_MODEL
        self.reranker_model_name = reranker_model or self.DEFAULT_RERANKER_MODEL
        self.use_reranking = use_reranking
        
        # Lazy initialization
        self._embedding_model = None
        self._reranker = None
        self._chroma_client = None
        self._ingestion_service = None
    
    @property
    def embedding_model(self) -> SentenceTransformer:
        """Lazy load embedding model."""
        if self._embedding_model is None:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
        return self._embedding_model
    
    @property
    def reranker(self) -> CrossEncoder:
        """Lazy load cross-encoder reranker."""
        if self._reranker is None and self.use_reranking:
            logger.info(f"Loading reranker model: {self.reranker_model_name}")
            self._reranker = CrossEncoder(self.reranker_model_name)
        return self._reranker
    
    @property
    def chroma_client(self) -> ChromaDBClient:
        """Get ChromaDB client."""
        if self._chroma_client is None:
            self._chroma_client = ChromaDBClient()
        return self._chroma_client
    
    @property
    def ingestion_service(self) -> IngestionService:
        """Get ingestion service for embeddings."""
        if self._ingestion_service is None:
            self._ingestion_service = get_ingestion_service()
        return self._ingestion_service
    
    def retrieve(
        self,
        query: str,
        user_id: int,
        top_k: int = None,
        doc_ids: List[int] = None,
        apply_reranking: bool = None
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Search query
            user_id: User ID for isolation
            top_k: Number of results to return
            doc_ids: Optional list of document IDs to filter
            apply_reranking: Override default reranking setting
            
        Returns:
            List of RetrievedChunk objects, sorted by relevance
        """
        top_k = top_k or self.DEFAULT_TOP_K
        should_rerank = apply_reranking if apply_reranking is not None else self.use_reranking
        
        # Get more candidates if reranking
        n_candidates = self.DEFAULT_CANDIDATES if should_rerank else top_k
        
        # Step 1: Generate query embedding
        query_embedding = self._embed_query(query)
        
        # Step 2: Retrieve candidates from ChromaDB
        candidates = self._semantic_search(
            query_embedding=query_embedding,
            user_id=user_id,
            n_results=n_candidates,
            doc_ids=doc_ids
        )
        
        if not candidates:
            return []
        
        # Step 3: Apply reranking if enabled
        if should_rerank and self.reranker:
            candidates = self._rerank(query, candidates)
        
        # Return top-k
        return candidates[:top_k]
    
    def retrieve_with_context(
        self,
        query: str,
        user_id: int,
        top_k: int = None,
        doc_ids: List[int] = None,
        include_neighbors: bool = True
    ) -> Tuple[List[RetrievedChunk], str]:
        """
        Retrieve chunks and format as context for LLM.
        
        Args:
            query: Search query
            user_id: User ID
            top_k: Number of results
            doc_ids: Optional document filter
            include_neighbors: Include adjacent chunks
            
        Returns:
            Tuple of (chunks, formatted_context_string)
        """
        chunks = self.retrieve(
            query=query,
            user_id=user_id,
            top_k=top_k,
            doc_ids=doc_ids
        )
        
        if not chunks:
            return [], ""
        
        # Format context
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_info = f"[Source: {chunk.source}"
            if chunk.page:
                source_info += f", Page {chunk.page}"
            source_info += "]"
            
            context_parts.append(
                f"--- Document {i} {source_info} ---\n{chunk.text}\n"
            )
        
        formatted_context = "\n".join(context_parts)
        
        return chunks, formatted_context
    
    def _embed_query(self, query: str) -> List[float]:
        """Generate embedding for query."""
        embedding = self.embedding_model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
    
    def _semantic_search(
        self,
        query_embedding: List[float],
        user_id: int,
        n_results: int,
        doc_ids: List[int] = None
    ) -> List[RetrievedChunk]:
        """
        Perform semantic search in ChromaDB.
        
        Args:
            query_embedding: Query embedding vector
            user_id: User ID for filtering
            n_results: Number of results
            doc_ids: Optional document IDs to filter
            
        Returns:
            List of RetrievedChunk objects
        """
        results = self.chroma_client.query_knowledge_base(
            user_id=user_id,
            query_embedding=query_embedding,
            n_results=n_results,
            doc_ids=doc_ids
        )
        
        if not results or not results.get('ids') or not results['ids'][0]:
            return []
        
        chunks = []
        ids = results['ids'][0]
        documents = results['documents'][0]
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]
        
        for i, (chunk_id, doc_text, distance, metadata) in enumerate(
            zip(ids, documents, distances, metadatas)
        ):
            # Convert distance to similarity score (assuming cosine distance)
            score = 1 - distance  # ChromaDB returns distances
            
            chunk = RetrievedChunk(
                text=doc_text,
                doc_id=metadata.get('doc_id', 0),
                chunk_id=chunk_id,
                source=metadata.get('source', 'Unknown'),
                score=score,
                page=metadata.get('page'),
                section=metadata.get('section')
            )
            chunks.append(chunk)
        
        return chunks
    
    def _rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk]
    ) -> List[RetrievedChunk]:
        """
        Apply cross-encoder reranking to candidates.
        
        Args:
            query: Original query
            candidates: List of candidate chunks
            
        Returns:
            Reranked list of chunks
        """
        if not candidates:
            return []
        
        # Prepare pairs for cross-encoder
        pairs = [(query, chunk.text) for chunk in candidates]
        
        # Get reranking scores
        scores = self.reranker.predict(pairs)
        
        # Update chunks with rerank scores
        for chunk, score in zip(candidates, scores):
            chunk.rerank_score = float(score)
        
        # Sort by rerank score (descending)
        reranked = sorted(
            candidates,
            key=lambda x: x.rerank_score,
            reverse=True
        )
        
        return reranked
    
    def search_memories(
        self,
        query: str,
        user_id: int,
        n_results: int = 5,
        memory_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search long-term memory for relevant past insights.
        
        Args:
            query: Search query
            user_id: User ID
            n_results: Number of results
            memory_type: Optional memory type filter
            
        Returns:
            List of memory entries
        """
        query_embedding = self._embed_query(query)
        
        results = self.chroma_client.query_memories(
            user_id=user_id,
            query_embedding=query_embedding,
            n_results=n_results,
            memory_type=memory_type
        )
        
        if not results or not results.get('ids') or not results['ids'][0]:
            return []
        
        memories = []
        for i, (memory_id, content, distance, metadata) in enumerate(
            zip(
                results['ids'][0],
                results['documents'][0],
                results['distances'][0],
                results['metadatas'][0]
            )
        ):
            memories.append({
                'id': memory_id,
                'content': content,
                'score': 1 - distance,
                'session_id': metadata.get('session_id'),
                'date': metadata.get('date'),
                'memory_type': metadata.get('memory_type')
            })
        
        return memories
    
    def hybrid_retrieve(
        self,
        query: str,
        user_id: int,
        top_k: int = 5,
        doc_ids: List[int] = None,
        include_memories: bool = True
    ) -> Dict[str, Any]:
        """
        Perform hybrid retrieval combining documents and memories.
        
        Args:
            query: Search query
            user_id: User ID
            top_k: Number of document results
            doc_ids: Optional document filter
            include_memories: Whether to include long-term memory
            
        Returns:
            Dictionary with 'documents' and optionally 'memories'
        """
        result = {
            'documents': [],
            'memories': [],
            'context': ''
        }
        
        # Get document chunks
        chunks, context = self.retrieve_with_context(
            query=query,
            user_id=user_id,
            top_k=top_k,
            doc_ids=doc_ids
        )
        
        result['documents'] = [
            {
                'text': c.text,
                'source': c.source,
                'page': c.page,
                'score': c.rerank_score or c.score
            }
            for c in chunks
        ]
        result['context'] = context
        
        # Get memories if requested
        if include_memories:
            memories = self.search_memories(
                query=query,
                user_id=user_id,
                n_results=3
            )
            result['memories'] = memories
            
            # Add memories to context
            if memories:
                memory_context = "\n--- Relevant Past Insights ---\n"
                for mem in memories:
                    memory_context += f"• {mem['content']}\n"
                result['context'] += memory_context
        
        return result


# Singleton instance
_retrieval_service = None


def get_retrieval_service() -> RetrievalService:
    """Get or create the retrieval service singleton."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
