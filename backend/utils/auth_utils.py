"""
Authentication Utilities

This module provides JWT-based authentication utilities including:
- Token generation and validation
- @token_required decorator for protected routes
- Current user context management
"""

import jwt
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Tuple

from flask import request, g, current_app

from .response import error_response


def generate_tokens(user_id: int, username: str) -> Tuple[str, str]:
    """
    Generate access and refresh tokens for a user.
    
    Args:
        user_id: The user's ID
        username: The user's username
        
    Returns:
        Tuple of (access_token, refresh_token)
    """
    # 使用 UTC 时间，JWT 标准要求
    now = datetime.utcnow()
    
    # Access token payload
    access_payload = {
        'user_id': user_id,
        'username': username,
        'type': 'access',
        'iat': now,
        'exp': now + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }
    
    # Refresh token payload
    refresh_payload = {
        'user_id': user_id,
        'type': 'refresh',
        'iat': now,
        'exp': now + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    }
    
    access_token = jwt.encode(
        access_payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM']
    )
    
    refresh_token = jwt.encode(
        refresh_payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM']
    )
    
    return access_token, refresh_token


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        # 确保 token 是干净的字符串
        token = token.strip()
        
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=[current_app.config['JWT_ALGORITHM']]
        )
        return payload
    except jwt.ExpiredSignatureError:
        current_app.logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        # 记录详细错误信息以便调试
        current_app.logger.error(f"Invalid token error: {type(e).__name__}: {str(e)}")
        current_app.logger.debug(f"Token (first 50 chars): {token[:50] if token else 'None'}...")
        return None


def get_token_from_request() -> Optional[str]:
    """
    Extract JWT token from request headers.
    
    Supports:
    - Authorization: Bearer <token>
    - X-Access-Token: <token>
    
    Returns:
        Token string or None if not found
    """
    # Check Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    # Check X-Access-Token header
    token = request.headers.get('X-Access-Token')
    if token:
        return token
    
    return None


def token_required(f):
    """
    Decorator to protect routes with JWT authentication.
    
    This decorator:
    1. Extracts the JWT token from request headers
    2. Validates the token
    3. Injects user_id into Flask's g context
    4. Returns 401 if authentication fails
    
    Usage:
        @app.route('/protected')
        @token_required
        def protected_route():
            user_id = g.user_id  # Available after authentication
            return f"Hello, user {user_id}!"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return error_response(
                message="Authentication required. Please provide a valid token.",
                status_code=401
            )
        
        payload = decode_token(token)
        
        if not payload:
            return error_response(
                message="Invalid or expired token. Please login again.",
                status_code=401
            )
        
        # Check token type
        if payload.get('type') != 'access':
            return error_response(
                message="Invalid token type. Access token required.",
                status_code=401
            )
        
        # Inject user info into Flask's g context
        g.user_id = payload.get('user_id')
        g.username = payload.get('username')
        g.token_payload = payload
        
        return f(*args, **kwargs)
    
    return decorated_function


def refresh_token_required(f):
    """
    Decorator for routes that require a refresh token.
    
    Similar to @token_required but validates refresh tokens instead.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return error_response(
                message="Refresh token required.",
                status_code=401
            )
        
        payload = decode_token(token)
        
        if not payload:
            return error_response(
                message="Invalid or expired refresh token.",
                status_code=401
            )
        
        if payload.get('type') != 'refresh':
            return error_response(
                message="Invalid token type. Refresh token required.",
                status_code=401
            )
        
        g.user_id = payload.get('user_id')
        g.token_payload = payload
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user_id() -> Optional[int]:
    """
    Get the current authenticated user's ID from g context.
    
    Returns:
        User ID or None if not authenticated
    """
    return getattr(g, 'user_id', None)


def get_current_username() -> Optional[str]:
    """
    Get the current authenticated user's username from g context.
    
    Returns:
        Username or None if not authenticated
    """
    return getattr(g, 'username', None)
