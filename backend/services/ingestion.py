"""
Document Ingestion Service

This module handles multi-modal document parsing and ingestion:
1. Parse documents using Docling (PDF, DOCX, etc.)
2. Apply Recursive Semantic Splitting for chunking
3. Generate embeddings and store in ChromaDB

Supports:
- PDF with text and tables
- DOCX documents
- Plain text and Markdown
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker import HierarchicalChunker
from sentence_transformers import SentenceTransformer

from database.models import FileDocument, ParsingStatus, db
from database.chroma_client import ChromaDBClient

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service for document ingestion, parsing, and vectorization.
    
    This service orchestrates the complete document processing pipeline:
    1. Document parsing with Docling (multi-modal)
    2. Hierarchical/semantic chunking
    3. Embedding generation
    4. ChromaDB storage with user isolation
    """
    
    # Default embedding model (multilingual, good for academic papers)
    DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Chunking parameters
    DEFAULT_CHUNK_SIZE = 512  # tokens
    DEFAULT_CHUNK_OVERLAP = 50  # tokens
    
    def __init__(
        self,
        embedding_model: str = None,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        Initialize the ingestion service.
        
        Args:
            embedding_model: HuggingFace model name for embeddings
            chunk_size: Maximum chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
        """
        self.embedding_model_name = embedding_model or self.DEFAULT_EMBEDDING_MODEL
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or self.DEFAULT_CHUNK_OVERLAP
        
        # Lazy initialization for heavy resources
        self._embedding_model = None
        self._doc_converter = None
        self._chunker = None
        self._chroma_client = None
    
    @property
    def embedding_model(self) -> SentenceTransformer:
        """Lazy load embedding model."""
        if self._embedding_model is None:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
        return self._embedding_model
    
    @property
    def doc_converter(self) -> DocumentConverter:
        """Lazy load Docling document converter."""
        if self._doc_converter is None:
            logger.info("Initializing Docling DocumentConverter")
            self._doc_converter = DocumentConverter()
        return self._doc_converter
    
    @property
    def chunker(self) -> HierarchicalChunker:
        """Lazy load hierarchical chunker."""
        if self._chunker is None:
            logger.info("Initializing HierarchicalChunker")
            self._chunker = HierarchicalChunker()
        return self._chunker
    
    @property
    def chroma_client(self) -> ChromaDBClient:
        """Get ChromaDB client singleton."""
        if self._chroma_client is None:
            self._chroma_client = ChromaDBClient()
        return self._chroma_client
    
    def process_document(
        self,
        document_id: int,
        user_id: int
    ) -> Tuple[bool, str]:
        """
        Process a document through the complete ingestion pipeline.
        
        This is the main entry point for document processing.
        
        Args:
            document_id: FileDocument ID
            user_id: User ID for data isolation
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Get document from database
        document = FileDocument.query.filter_by(
            id=document_id,
            user_id=user_id
        ).first()
        
        if not document:
            return False, "Document not found"
        
        if not os.path.exists(document.filepath):
            self._update_status(document, ParsingStatus.FAILED, "File not found on disk")
            return False, "File not found on disk"
        
        try:
            # Update status to processing
            self._update_status(document, ParsingStatus.PROCESSING)
            
            # Step 1: Parse document with Docling
            logger.info(f"Parsing document: {document.filename}")
            parsed_content = self._parse_document(document.filepath)
            
            if not parsed_content:
                self._update_status(document, ParsingStatus.FAILED, "Failed to parse document")
                return False, "Failed to parse document"
            
            # Step 2: Chunk the content
            logger.info(f"Chunking document: {document.filename}")
            chunks = self._chunk_document(parsed_content)
            
            if not chunks:
                self._update_status(document, ParsingStatus.FAILED, "No content extracted")
                return False, "No content extracted from document"
            
            # Step 3: Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = self._generate_embeddings([c['text'] for c in chunks])
            
            # Step 4: Store in ChromaDB
            logger.info(f"Storing {len(chunks)} chunks in ChromaDB")
            chunk_ids = self._store_chunks(
                user_id=user_id,
                doc_id=document_id,
                chunks=chunks,
                embeddings=embeddings,
                source=document.filename
            )
            
            # Update document status
            document.parsing_status = ParsingStatus.COMPLETED
            document.chunk_count = len(chunks)
            document.parsed_at = datetime.now()
            document.parsing_error = None
            db.session.commit()
            
            logger.info(f"Successfully processed document: {document.filename}")
            return True, f"Successfully processed {len(chunks)} chunks"
        
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            self._update_status(document, ParsingStatus.FAILED, str(e))
            return False, f"Processing error: {str(e)}"
    
    def _parse_document(self, filepath: str) -> Optional[Any]:
        """
        Parse document using Docling.
        
        Docling handles multi-modal content including:
        - Text extraction
        - Table detection and extraction
        - Figure/image handling
        - Layout analysis
        
        Args:
            filepath: Path to the document file
            
        Returns:
            Docling document object or None if parsing fails
        """
        try:
            result = self.doc_converter.convert(filepath)
            return result.document
        except Exception as e:
            logger.error(f"Docling parsing error: {str(e)}")
            return None
    
    def _chunk_document(self, docling_doc) -> List[Dict[str, Any]]:
        """
        Apply hierarchical chunking to parsed document.
        
        Uses Docling's HierarchicalChunker which preserves document structure
        and creates semantically meaningful chunks.
        
        Args:
            docling_doc: Parsed Docling document
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        
        try:
            # Use Docling's hierarchical chunker
            raw_chunks = list(self.chunker.chunk(docling_doc))
            
            for i, chunk in enumerate(raw_chunks):
                chunk_data = {
                    'text': chunk.text,
                    'chunk_index': i,
                    'metadata': {}
                }
                
                # Extract metadata if available
                if hasattr(chunk, 'meta'):
                    chunk_data['metadata'] = {
                        'page': getattr(chunk.meta, 'page', None),
                        'section': getattr(chunk.meta, 'section', None),
                        'heading': getattr(chunk.meta, 'heading', None),
                    }
                
                # Filter out empty chunks
                if chunk_data['text'].strip():
                    chunks.append(chunk_data)
            
            return chunks
        
        except Exception as e:
            logger.error(f"Chunking error: {str(e)}")
            # Fallback: try to get markdown and do simple splitting
            return self._fallback_chunking(docling_doc)
    
    def _fallback_chunking(self, docling_doc) -> List[Dict[str, Any]]:
        """
        Fallback chunking using simple text splitting.
        
        Used when hierarchical chunking fails.
        """
        try:
            # Export to markdown
            markdown_text = docling_doc.export_to_markdown()
            
            if not markdown_text:
                return []
            
            # Simple recursive splitting
            chunks = self._recursive_split(
                markdown_text,
                max_length=self.chunk_size * 4,  # Approximate chars
                overlap=self.chunk_overlap * 4
            )
            
            return [
                {'text': chunk, 'chunk_index': i, 'metadata': {}}
                for i, chunk in enumerate(chunks)
                if chunk.strip()
            ]
        
        except Exception as e:
            logger.error(f"Fallback chunking error: {str(e)}")
            return []
    
    def _recursive_split(
        self,
        text: str,
        max_length: int = 2000,
        overlap: int = 200
    ) -> List[str]:
        """
        Recursively split text into chunks.
        
        Tries to split on natural boundaries:
        1. Double newlines (paragraphs)
        2. Single newlines
        3. Sentences (periods)
        4. Words
        """
        if len(text) <= max_length:
            return [text]
        
        # Try splitting on different separators
        separators = ['\n\n', '\n', '. ', ' ']
        
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                chunks = []
                current_chunk = ""
                
                for part in parts:
                    test_chunk = current_chunk + sep + part if current_chunk else part
                    
                    if len(test_chunk) <= max_length:
                        current_chunk = test_chunk
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = part
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Apply overlap
                if overlap > 0 and len(chunks) > 1:
                    overlapped_chunks = []
                    for i, chunk in enumerate(chunks):
                        if i > 0:
                            # Add overlap from previous chunk
                            prev_overlap = chunks[i-1][-overlap:]
                            chunk = prev_overlap + chunk
                        overlapped_chunks.append(chunk)
                    return overlapped_chunks
                
                return chunks
        
        # Fallback: hard split
        return [text[i:i+max_length] for i in range(0, len(text), max_length - overlap)]
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def _store_chunks(
        self,
        user_id: int,
        doc_id: int,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        source: str
    ) -> List[str]:
        """
        Store chunks and embeddings in ChromaDB.
        
        Args:
            user_id: User ID for isolation
            doc_id: Document ID
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors
            source: Source filename
            
        Returns:
            List of chunk IDs
        """
        # Prepare metadata for each chunk
        metadatas = []
        for chunk in chunks:
            meta = {
                'page': chunk['metadata'].get('page'),
                'section': chunk['metadata'].get('section'),
                'heading': chunk['metadata'].get('heading'),
            }
            # Remove None values
            metadatas.append({k: v for k, v in meta.items() if v is not None})
        
        # Store in ChromaDB
        chunk_ids = self.chroma_client.add_document_chunks(
            user_id=user_id,
            doc_id=doc_id,
            chunks=[c['text'] for c in chunks],
            embeddings=embeddings,
            metadatas=metadatas,
            source=source
        )
        
        return chunk_ids
    
    def _update_status(
        self,
        document: FileDocument,
        status: ParsingStatus,
        error: str = None
    ):
        """Update document parsing status."""
        document.parsing_status = status
        document.parsing_error = error
        if status == ParsingStatus.COMPLETED:
            document.parsed_at = datetime.utcnow()
        db.session.commit()
    
    def delete_document_vectors(self, user_id: int, doc_id: int) -> bool:
        """
        Delete all vectors for a document from ChromaDB.
        
        Args:
            user_id: User ID for verification
            doc_id: Document ID
            
        Returns:
            Success status
        """
        try:
            self.chroma_client.delete_document_chunks(user_id, doc_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            return False
    
    def reprocess_document(self, document_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Reprocess a document (delete existing vectors and re-ingest).
        
        Args:
            document_id: Document ID
            user_id: User ID
            
        Returns:
            Tuple of (success, message)
        """
        # Delete existing vectors
        self.delete_document_vectors(user_id, document_id)
        
        # Reprocess
        return self.process_document(document_id, user_id)
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Useful for query embedding.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# Singleton instance
_ingestion_service = None


def get_ingestion_service() -> IngestionService:
    """Get or create the ingestion service singleton."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
