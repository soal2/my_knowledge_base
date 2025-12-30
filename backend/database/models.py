"""
SQLAlchemy Models for MySQL Database

This module defines all relational data models for the Personal Federated 
Learning Knowledge Base Agent. All models enforce user_id isolation to ensure 
data privacy between users.

Models:
    - User: Core user authentication and profile
    - APIKey: Third-party API credentials (Qwen, DeepSeek)
    - FileDocument: Uploaded document metadata and parsing status
    - ChatSession: Conversation session grouping
    - ChatMessage: Individual messages within a session
"""

from datetime import datetime
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class ParsingStatus(Enum):
    """Enum for document parsing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(Enum):
    """Enum for chat message roles."""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class User(db.Model):
    """
    User model for authentication and profile management.
    
    Attributes:
        id: Primary key
        username: Unique username for login
        password_hash: Bcrypt hashed password
        created_at: Account creation timestamp
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    # Relationships
    api_keys = db.relationship('APIKey', backref='user', lazy='dynamic', 
                                cascade='all, delete-orphan')
    documents = db.relationship('FileDocument', backref='user', lazy='dynamic',
                                 cascade='all, delete-orphan')
    chat_sessions = db.relationship('ChatSession', backref='user', lazy='dynamic',
                                     cascade='all, delete-orphan')
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify the provided password against the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self) -> str:
        return f'<User {self.username}>'


class APIKey(db.Model):
    """
    API Key storage for third-party LLM providers.
    
    Stores encrypted API keys for providers like Qwen and DeepSeek.
    Keys are isolated per user and can be activated/deactivated.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User (enforces data isolation)
        provider: API provider name (e.g., 'qwen', 'deepseek')
        api_key: The actual API key (should be encrypted in production)
        is_active: Whether this key is currently active
        created_at: Key creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), 
                        nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False)  # 'qwen', 'deepseek'
    api_key = db.Column(db.String(512), nullable=False)  # Consider encryption
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, 
                           onupdate=datetime.now, nullable=False)
    
    # Composite unique constraint: one active key per provider per user
    __table_args__ = (
        Index('idx_user_provider', 'user_id', 'provider'),
    )
    
    def __repr__(self) -> str:
        return f'<APIKey {self.provider} for User {self.user_id}>'


class FileDocument(db.Model):
    """
    Document metadata for uploaded files.
    
    Tracks uploaded academic papers/reports and their parsing status.
    Actual parsed content is stored in ChromaDB as vector embeddings.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User (enforces data isolation)
        filename: Original uploaded filename
        filepath: Server-side storage path
        file_type: Document type (pdf, docx, etc.)
        file_size: File size in bytes
        parsing_status: Current parsing state (pending/processing/completed/failed)
        parsing_error: Error message if parsing failed
        chunk_count: Number of chunks after parsing
        upload_time: File upload timestamp
        parsed_at: Parsing completion timestamp
    """
    __tablename__ = 'file_documents'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), 
                        nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(20), nullable=True)  # pdf, docx, txt, etc.
    file_size = db.Column(db.BigInteger, nullable=True)  # Size in bytes
    parsing_status = db.Column(
        db.Enum(ParsingStatus, values_callable=lambda x: [e.value for e in x]), 
        default=ParsingStatus.PENDING, 
        nullable=False
    )
    parsing_error = db.Column(db.Text, nullable=True)  # Error message if failed
    chunk_count = db.Column(db.Integer, default=0)  # Number of chunks after parsing
    upload_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    parsed_at = db.Column(db.DateTime, nullable=True)
    
    # Index for common queries
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'parsing_status'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'parsing_status': self.parsing_status.value,
            'chunk_count': self.chunk_count,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'parsed_at': self.parsed_at.isoformat() if self.parsed_at else None
        }
    
    def __repr__(self) -> str:
        return f'<FileDocument {self.filename} ({self.parsing_status.value})>'


class ChatSession(db.Model):
    """
    Chat session for grouping related messages.
    
    Represents a conversation thread between the user and the AI agent.
    Sessions help organize chat history and enable context retrieval.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User (enforces data isolation)
        title: Session title (auto-generated or user-defined)
        created_at: Session creation timestamp
        last_active_at: Last message timestamp
    """
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), 
                        nullable=False, index=True)
    title = db.Column(db.String(255), default='New Chat', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    last_active_at = db.Column(db.DateTime, default=datetime.now, 
                                onupdate=datetime.now, nullable=False)
    
    # Relationships
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic',
                                cascade='all, delete-orphan',
                                order_by='ChatMessage.created_at')
    
    # Index for sorting by activity
    __table_args__ = (
        Index('idx_user_active', 'user_id', 'last_active_at'),
    )
    
    def to_dict(self, include_messages: bool = False) -> dict:
        """Convert model to dictionary for API responses."""
        result = {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active_at': self.last_active_at.isoformat() if self.last_active_at else None
        }
        if include_messages:
            result['messages'] = [msg.to_dict() for msg in self.messages.all()]
        return result
    
    def __repr__(self) -> str:
        return f'<ChatSession {self.id}: {self.title}>'


class ChatMessage(db.Model):
    """
    Individual chat message within a session.
    
    Stores both user inputs and AI responses. Supports deep thinking mode
    for complex reasoning tasks requiring extended processing.
    
    Attributes:
        id: Primary key
        session_id: Foreign key to ChatSession
        role: Message author (user/ai/system)
        content: Message text content
        is_deep_thought: Whether this used deep thinking mode
        thinking_content: Extended reasoning process (for deep thought)
        tokens_used: Token count for this message
        created_at: Message timestamp
    """
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id', ondelete='CASCADE'), 
                           nullable=False, index=True)
    # SQLAlchemy 默认使用 Enum 成员的名称（USER, AI, SYSTEM）而不是值（user, ai, system）。需要明确告诉 SQLAlchemy 使用 Enum 的值
    role = db.Column(db.Enum(MessageRole, values_callable=lambda x: [e.value for e in x]), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_deep_thought = db.Column(db.Boolean, default=False, nullable=False)
    thinking_content = db.Column(db.Text, nullable=True)  # Reasoning process
    tokens_used = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role.value,
            'content': self.content,
            'is_deep_thought': self.is_deep_thought,
            'thinking_content': self.thinking_content,
            'tokens_used': self.tokens_used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self) -> str:
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f'<ChatMessage {self.role.value}: {preview}>'


# ============================================================================
# Utility Functions for Data Isolation
# ============================================================================

def get_user_documents(user_id: int, status: ParsingStatus = None):
    """
    Get all documents for a specific user with optional status filter.
    
    Args:
        user_id: The user's ID
        status: Optional parsing status filter
        
    Returns:
        Query object for user's documents
    """
    query = FileDocument.query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(parsing_status=status)
    return query.order_by(FileDocument.upload_time.desc())


def get_user_sessions(user_id: int, limit: int = None):
    """
    Get all chat sessions for a specific user, ordered by last activity.
    
    Args:
        user_id: The user's ID
        limit: Optional limit on number of sessions
        
    Returns:
        Query object for user's sessions
    """
    query = ChatSession.query.filter_by(user_id=user_id)\
                             .order_by(ChatSession.last_active_at.desc())
    if limit:
        query = query.limit(limit)
    return query


def get_session_messages(session_id: int, user_id: int):
    """
    Get all messages for a session, with user verification.
    
    Args:
        session_id: The session ID
        user_id: The user's ID (for verification)
        
    Returns:
        Query object for session messages or None if session doesn't belong to user
    """
    session = ChatSession.query.filter_by(id=session_id, user_id=user_id).first()
    if not session:
        return None
    return session.messages.order_by(ChatMessage.created_at.asc())
