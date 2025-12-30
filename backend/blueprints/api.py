"""
API Blueprint

This module handles core API endpoints:
- POST /api/settings/keys: Save/update LLM API keys
- GET /api/settings/keys: Get user's API keys
- DELETE /api/settings/keys/<provider>: Delete an API key
- GET /api/history: Get chat session history
- POST /api/chat/new: Create a new chat session
- GET /api/chat/<session_id>: Get session with messages
- DELETE /api/chat/<session_id>: Delete a chat session
"""

from datetime import datetime

from flask import Blueprint, request, g

from database import db
from database.models import (
    APIKey, 
    ChatSession, 
    ChatMessage, 
    MessageRole,
    get_user_sessions,
    get_session_messages
)
from utils.auth_utils import token_required
from utils.response import success_response, error_response, paginated_response


api_bp = Blueprint('api', __name__)


# =============================================================================
# API Key Management Endpoints
# =============================================================================

VALID_PROVIDERS = ['qwen', 'deepseek', 'openai', 'anthropic']


@api_bp.route('/settings/keys', methods=['POST'])
@token_required
def save_api_key():
    """
    Save or update an LLM API key for the current user.
    
    Request Body:
        {
            "provider": "qwen" | "deepseek" | "openai" | "anthropic",
            "api_key": "string"
        }
    
    Returns:
        200: API key saved successfully
        400: Validation error
    """
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return error_response("Request body is required", 400)
    
    provider = data.get('provider', '').strip().lower()
    api_key = data.get('api_key', '').strip()
    
    # Validation
    errors = {}
    
    if not provider:
        errors['provider'] = 'Provider is required'
    elif provider not in VALID_PROVIDERS:
        errors['provider'] = f'Invalid provider. Must be one of: {", ".join(VALID_PROVIDERS)}'
    
    if not api_key:
        errors['api_key'] = 'API key is required'
    elif len(api_key) < 10:
        errors['api_key'] = 'API key seems too short'
    
    if errors:
        return error_response("Validation failed", 400, errors=errors)
    
    try:
        # Check if key already exists for this provider
        existing_key = APIKey.query.filter_by(
            user_id=user_id,
            provider=provider
        ).first()
        
        if existing_key:
            # Update existing key
            existing_key.api_key = api_key
            existing_key.is_active = True
            existing_key.updated_at = datetime.now()
            message = f"API key for {provider} updated successfully"
        else:
            # Create new key
            new_key = APIKey(
                user_id=user_id,
                provider=provider,
                api_key=api_key,
                is_active=True
            )
            db.session.add(new_key)
            message = f"API key for {provider} saved successfully"
        
        db.session.commit()
        
        return success_response(
            data={'provider': provider},
            message=message
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to save API key: {str(e)}", 500)


@api_bp.route('/settings/keys', methods=['GET'])
@token_required
def get_api_keys():
    """
    Get all API keys for the current user.
    
    Note: API keys are masked for security (only last 4 chars shown).
    
    Returns:
        200: List of API keys
    """
    user_id = g.user_id
    
    keys = APIKey.query.filter_by(user_id=user_id).all()
    
    # Mask API keys for security
    key_list = []
    for key in keys:
        masked_key = '*' * (len(key.api_key) - 4) + key.api_key[-4:]
        key_list.append({
            'id': key.id,
            'provider': key.provider,
            'api_key_masked': masked_key,
            'is_active': key.is_active,
            'created_at': key.created_at.isoformat(),
            'updated_at': key.updated_at.isoformat()
        })
    
    return success_response(data=key_list)


@api_bp.route('/settings/keys/<provider>', methods=['DELETE'])
@token_required
def delete_api_key(provider: str):
    """
    Delete an API key for a specific provider.
    
    Args:
        provider: The API provider name
    
    Returns:
        200: API key deleted
        404: API key not found
    """
    user_id = g.user_id
    
    key = APIKey.query.filter_by(
        user_id=user_id,
        provider=provider.lower()
    ).first()
    
    if not key:
        return error_response(f"API key for {provider} not found", 404)
    
    try:
        db.session.delete(key)
        db.session.commit()
        return success_response(message=f"API key for {provider} deleted")
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to delete API key: {str(e)}", 500)


@api_bp.route('/settings/keys/<provider>/toggle', methods=['POST'])
@token_required
def toggle_api_key(provider: str):
    """
    Toggle the active status of an API key.
    
    Args:
        provider: The API provider name
    
    Returns:
        200: Status toggled
        404: API key not found
    """
    user_id = g.user_id
    
    key = APIKey.query.filter_by(
        user_id=user_id,
        provider=provider.lower()
    ).first()
    
    if not key:
        return error_response(f"API key for {provider} not found", 404)
    
    try:
        key.is_active = not key.is_active
        db.session.commit()
        
        status = "activated" if key.is_active else "deactivated"
        return success_response(
            data={'is_active': key.is_active},
            message=f"API key for {provider} {status}"
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to toggle API key: {str(e)}", 500)


# =============================================================================
# Chat History Endpoints
# =============================================================================

@api_bp.route('/history', methods=['GET'])
@token_required
def get_chat_history():
    """
    Get chat session history for the current user.
    
    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 20, max: 100)
    
    Returns:
        200: Paginated list of chat sessions
    """
    user_id = g.user_id
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # Limit max per_page
    
    # Query sessions with pagination
    sessions_query = ChatSession.query.filter_by(user_id=user_id)\
                                       .order_by(ChatSession.last_active_at.desc())
    
    total = sessions_query.count()
    sessions = sessions_query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Build response
    session_list = []
    for session in sessions:
        # Get message count and preview
        message_count = session.messages.count()
        first_message = session.messages.order_by(ChatMessage.created_at.asc()).first()
        preview = None
        if first_message:
            preview = first_message.content[:100] + '...' if len(first_message.content) > 100 else first_message.content
        
        session_list.append({
            'id': session.id,
            'title': session.title,
            'message_count': message_count,
            'preview': preview,
            'created_at': session.created_at.isoformat(),
            'last_active_at': session.last_active_at.isoformat()
        })
    
    return paginated_response(
        items=session_list,
        page=page,
        per_page=per_page,
        total=total,
        message="Chat history retrieved"
    )


@api_bp.route('/chat/new', methods=['POST'])
@token_required
def create_chat_session():
    """
    Create a new chat session.
    
    Request Body (optional):
        {
            "title": "string",
            "initial_message": "string" (optional first user message)
        }
    
    Returns:
        201: New session created
    """
    user_id = g.user_id
    data = request.get_json() or {}
    
    title = data.get('title', 'New Chat').strip()
    initial_message = data.get('initial_message', '').strip()
    
    try:
        # Create session
        session = ChatSession(
            user_id=user_id,
            title=title[:255] if title else 'New Chat'
        )
        db.session.add(session)
        db.session.flush()  # Get session ID without committing
        
        # Add initial message if provided
        if initial_message:
            message = ChatMessage(
                session_id=session.id,
                role=MessageRole.USER,
                content=initial_message
            )
            db.session.add(message)
        
        db.session.commit()
        
        return success_response(
            data={
                'id': session.id,
                'title': session.title,
                'created_at': session.created_at.isoformat()
            },
            message="Chat session created",
            status_code=201
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to create session: {str(e)}", 500)


@api_bp.route('/chat/<int:session_id>', methods=['GET'])
@token_required
def get_chat_session(session_id: int):
    """
    Get a chat session with all its messages.
    
    Args:
        session_id: The session ID
    
    Returns:
        200: Session with messages
        404: Session not found
    """
    user_id = g.user_id
    
    # Verify session belongs to user (data isolation)
    session = ChatSession.query.filter_by(
        id=session_id,
        user_id=user_id
    ).first()
    
    if not session:
        return error_response("Chat session not found", 404)
    
    # Get all messages
    messages = session.messages.order_by(ChatMessage.created_at.asc()).all()
    
    return success_response(
        data={
            'session': {
                'id': session.id,
                'title': session.title,
                'created_at': session.created_at.isoformat(),
                'last_active_at': session.last_active_at.isoformat()
            },
            'messages': [msg.to_dict() for msg in messages]
        }
    )


@api_bp.route('/chat/<int:session_id>', methods=['PUT'])
@token_required
def update_chat_session(session_id: int):
    """
    Update a chat session's title.
    
    Args:
        session_id: The session ID
    
    Request Body:
        {
            "title": "string"
        }
    
    Returns:
        200: Session updated
        404: Session not found
    """
    user_id = g.user_id
    data = request.get_json()
    
    if not data or 'title' not in data:
        return error_response("Title is required", 400)
    
    session = ChatSession.query.filter_by(
        id=session_id,
        user_id=user_id
    ).first()
    
    if not session:
        return error_response("Chat session not found", 404)
    
    try:
        session.title = data['title'][:255].strip()
        db.session.commit()
        
        return success_response(
            data={'id': session.id, 'title': session.title},
            message="Session updated"
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to update session: {str(e)}", 500)


@api_bp.route('/chat/<int:session_id>', methods=['DELETE'])
@token_required
def delete_chat_session(session_id: int):
    """
    Delete a chat session and all its messages.
    
    Args:
        session_id: The session ID
    
    Returns:
        200: Session deleted
        404: Session not found
    """
    user_id = g.user_id
    
    session = ChatSession.query.filter_by(
        id=session_id,
        user_id=user_id
    ).first()
    
    if not session:
        return error_response("Chat session not found", 404)
    
    try:
        db.session.delete(session)
        db.session.commit()
        
        return success_response(message="Chat session deleted")
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to delete session: {str(e)}", 500)


# =============================================================================
# User Statistics Endpoint
# =============================================================================

@api_bp.route('/stats', methods=['GET'])
@token_required
def get_user_stats():
    """
    Get statistics for the current user.
    
    Returns:
        200: User statistics
    """
    user_id = g.user_id
    
    from database.models import FileDocument, ParsingStatus
    
    # Document stats
    total_documents = FileDocument.query.filter_by(user_id=user_id).count()
    completed_documents = FileDocument.query.filter_by(
        user_id=user_id,
        parsing_status=ParsingStatus.COMPLETED
    ).count()
    
    # Chat stats
    total_sessions = ChatSession.query.filter_by(user_id=user_id).count()
    total_messages = db.session.query(ChatMessage)\
                               .join(ChatSession)\
                               .filter(ChatSession.user_id == user_id)\
                               .count()
    
    # API keys
    active_keys = APIKey.query.filter_by(user_id=user_id, is_active=True).count()
    
    return success_response(
        data={
            'documents': {
                'total': total_documents,
                'completed': completed_documents
            },
            'chat': {
                'sessions': total_sessions,
                'messages': total_messages
            },
            'api_keys': active_keys
        }
    )


# =============================================================================
# Model Selection Endpoints
# =============================================================================

# Available models per provider
AVAILABLE_MODELS = {
    'qwen': [
        {'id': 'qwen-turbo', 'name': 'Qwen Turbo', 'description': 'Fast and cost-effective'},
        {'id': 'qwen-plus', 'name': 'Qwen Plus', 'description': 'Balanced performance'},
        {'id': 'qwen-max', 'name': 'Qwen Max', 'description': 'Most capable'},
    ],
    'deepseek': [
        {'id': 'deepseek-chat', 'name': 'DeepSeek Chat', 'description': 'General purpose chat'},
        {'id': 'deepseek-coder', 'name': 'DeepSeek Coder', 'description': 'Code generation'},
        {'id': 'deepseek-reasoner', 'name': 'DeepSeek Reasoner', 'description': 'Complex reasoning'},
    ],
    'openai': [
        {'id': 'gpt-4o', 'name': 'GPT-4o', 'description': 'Latest multimodal model'},
        {'id': 'gpt-4o-mini', 'name': 'GPT-4o Mini', 'description': 'Fast and affordable'},
        {'id': 'gpt-4-turbo', 'name': 'GPT-4 Turbo', 'description': 'High capability'},
    ],
    'anthropic': [
        {'id': 'claude-3-5-sonnet-20241022', 'name': 'Claude 3.5 Sonnet', 'description': 'Best balance'},
        {'id': 'claude-3-5-haiku-20241022', 'name': 'Claude 3.5 Haiku', 'description': 'Fast and light'},
    ]
}


@api_bp.route('/settings/models', methods=['GET'])
@token_required
def get_available_models():
    """
    Get available models for user's configured providers.
    
    Only returns models for providers where user has an active API key.
    
    Returns:
        200: Dictionary of provider -> models list
    """
    user_id = g.user_id
    
    # Get user's active API keys
    active_keys = APIKey.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    
    result = {}
    for key in active_keys:
        if key.provider in AVAILABLE_MODELS:
            result[key.provider] = AVAILABLE_MODELS[key.provider]
    
    return success_response(
        data=result,
        message="Available models retrieved"
    )


# =============================================================================
# Chat Message Endpoints
# =============================================================================

@api_bp.route('/chat/<int:session_id>/message', methods=['POST'])
@token_required
def send_message(session_id: int):
    """
    Send a message to a chat session and get AI response.
    
    Args:
        session_id: The session ID
    
    Request Body:
        {
            "message": "string",
            "is_deep_thought": boolean (optional, default: false),
            "doc_ids": [int] (optional, document IDs for RAG),
            "model": "string" (optional, e.g., "qwen-plus", "deepseek-chat")
        }
    
    Returns:
        200: AI message response
        400: Validation error
        404: Session not found
    """
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return error_response("Request body is required", 400)
    
    message_content = data.get('message', '').strip()
    if not message_content:
        return error_response("Message is required", 400)
    
    # Verify session belongs to user
    session = ChatSession.query.filter_by(
        id=session_id,
        user_id=user_id
    ).first()
    
    if not session:
        return error_response("Chat session not found", 404)
    
    # Extract options
    is_deep_thought = data.get('is_deep_thought', False)
    doc_ids = data.get('doc_ids', [])
    model = data.get('model')  # e.g., "qwen-plus", "deepseek-chat"
    
    # Determine provider from model name
    provider = 'qwen'  # default
    if model:
        if model.startswith('deepseek'):
            provider = 'deepseek'
        elif model.startswith('gpt'):
            provider = 'openai'
        elif model.startswith('claude'):
            provider = 'anthropic'
    
    # Get user's API key for the provider
    api_key = APIKey.query.filter_by(
        user_id=user_id,
        provider=provider,
        is_active=True
    ).first()
    
    if not api_key:
        return error_response(f"No active API key for {provider}. Please add one in settings.", 400)
    
    try:
        from agent.graph import get_agent
        
        # Get agent and configure LLM
        agent = get_agent()
        agent.configure_llm(provider, api_key.api_key)
        
        # Get previous messages for context
        prev_messages = session.messages.order_by(ChatMessage.created_at.asc()).all()
        messages_history = [
            {"role": msg.role.value if hasattr(msg.role, 'value') else msg.role, "content": msg.content}
            for msg in prev_messages[-10:]  # Last 10 messages for context
        ]
        
        # Process through agent
        result = agent.chat(
            user_id=user_id,
            session_id=session_id,
            query=message_content,
            messages=messages_history,
            is_deep_thought=is_deep_thought,
            doc_ids=doc_ids if doc_ids else None,
            provider=provider
        )
        
        # Save to database
        agent.save_to_database(
            session_id=session_id,
            query=message_content,
            response=result['response'],
            is_deep_thought=is_deep_thought,
            thinking_content=result.get('thinking_content'),
            tokens_used=result.get('tokens_used', 0)
        )
        
        # Get the saved AI message
        ai_message = ChatMessage.query.filter_by(
            session_id=session_id,
            role=MessageRole.AI
        ).order_by(ChatMessage.created_at.desc()).first()
        
        return success_response(
            data=ai_message.to_dict() if ai_message else {
                'content': result['response'],
                'thinking_content': result.get('thinking_content'),
                'tokens_used': result.get('tokens_used', 0),
                'is_deep_thought': is_deep_thought
            },
            message="Message sent"
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to process message: {str(e)}", 500)
