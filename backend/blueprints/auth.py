"""
Authentication Blueprint

This module handles all authentication-related endpoints:
- POST /auth/register: User registration
- POST /auth/login: User login
- POST /auth/refresh: Refresh access token
- POST /auth/logout: User logout
- GET /auth/me: Get current user info
"""

import re
from datetime import datetime

from flask import Blueprint, request, g

from database import db
from database.models import User
from utils.auth_utils import (
    generate_tokens, 
    token_required, 
    refresh_token_required,
    get_current_user_id
)
from utils.response import success_response, error_response


auth_bp = Blueprint('auth', __name__)


# Username validation regex (alphanumeric, underscore, 3-30 chars)
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,30}$')
# Password minimum requirements
MIN_PASSWORD_LENGTH = 6


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Request Body:
        {
            "username": "string",
            "password": "string",
            "confirm_password": "string" (optional)
        }
    
    Returns:
        201: User created successfully with tokens
        400: Validation error
        409: Username already exists
    """
    data = request.get_json()
    
    if not data:
        return error_response("Request body is required", 400)
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', password)
    
    # Validation
    errors = {}
    
    if not username:
        errors['username'] = 'Username is required'
    elif not USERNAME_REGEX.match(username):
        errors['username'] = 'Username must be 3-30 characters, alphanumeric and underscore only'
    
    if not password:
        errors['password'] = 'Password is required'
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors['password'] = f'Password must be at least {MIN_PASSWORD_LENGTH} characters'
    
    if password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match'
    
    if errors:
        return error_response("Validation failed", 400, errors=errors)
    
    # Check if username exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return error_response("Username already exists", 409)
    
    # Create new user
    user = User(username=username)
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Generate tokens
        access_token, refresh_token = generate_tokens(user.id, user.username)
        
        return success_response(
            data={
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'created_at': user.created_at.isoformat()
                },
                'access_token': access_token,
                'refresh_token': refresh_token
            },
            message="Registration successful",
            status_code=201
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Registration failed: {str(e)}", 500)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return tokens.
    
    Request Body:
        {
            "username": "string",
            "password": "string"
        }
    
    Returns:
        200: Login successful with tokens
        400: Validation error
        401: Invalid credentials
    """
    data = request.get_json()
    
    if not data:
        return error_response("Request body is required", 400)
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return error_response("Username and password are required", 400)
    
    # Find user
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return error_response("Invalid username or password", 401)
    
    # Generate tokens
    access_token, refresh_token = generate_tokens(user.id, user.username)
    
    return success_response(
        data={
            'user': {
                'id': user.id,
                'username': user.username,
                'created_at': user.created_at.isoformat()
            },
            'access_token': access_token,
            'refresh_token': refresh_token
        },
        message="Login successful"
    )


@auth_bp.route('/refresh', methods=['POST'])
@refresh_token_required
def refresh():
    """
    Refresh access token using refresh token.
    
    Headers:
        Authorization: Bearer <refresh_token>
    
    Returns:
        200: New access token
        401: Invalid refresh token
    """
    user_id = g.user_id
    
    # Get user to verify they still exist
    user = User.query.get(user_id)
    
    if not user:
        return error_response("User not found", 401)
    
    # Generate new tokens
    access_token, refresh_token = generate_tokens(user.id, user.username)
    
    return success_response(
        data={
            'access_token': access_token,
            'refresh_token': refresh_token
        },
        message="Token refreshed successfully"
    )


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """
    Get current authenticated user's information.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: User information
        401: Not authenticated
    """
    user_id = g.user_id
    user = User.query.get(user_id)
    
    if not user:
        return error_response("User not found", 404)
    
    return success_response(
        data={
            'id': user.id,
            'username': user.username,
            'created_at': user.created_at.isoformat()
        }
    )


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    Logout current user.
    
    Note: Since we're using stateless JWT, this endpoint mainly serves
    as a confirmation. Client should discard tokens on their side.
    
    For production, consider implementing token blacklisting with Redis.
    
    Returns:
        200: Logout successful
    """
    # In a stateless JWT system, we can't truly invalidate tokens server-side
    # without maintaining a blacklist. For now, we just confirm the logout.
    # TODO: Implement token blacklisting with Redis for production
    
    return success_response(
        message="Logout successful. Please discard your tokens."
    )


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """
    Change current user's password.
    
    Request Body:
        {
            "current_password": "string",
            "new_password": "string",
            "confirm_password": "string"
        }
    
    Returns:
        200: Password changed successfully
        400: Validation error
        401: Current password incorrect
    """
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return error_response("Request body is required", 400)
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    # Validation
    errors = {}
    
    if not current_password:
        errors['current_password'] = 'Current password is required'
    
    if not new_password:
        errors['new_password'] = 'New password is required'
    elif len(new_password) < MIN_PASSWORD_LENGTH:
        errors['new_password'] = f'Password must be at least {MIN_PASSWORD_LENGTH} characters'
    
    if new_password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match'
    
    if errors:
        return error_response("Validation failed", 400, errors=errors)
    
    # Verify current password
    user = User.query.get(user_id)
    if not user.check_password(current_password):
        return error_response("Current password is incorrect", 401)
    
    # Update password
    try:
        user.set_password(new_password)
        db.session.commit()
        
        # Generate new tokens (invalidate old ones)
        access_token, refresh_token = generate_tokens(user.id, user.username)
        
        return success_response(
            data={
                'access_token': access_token,
                'refresh_token': refresh_token
            },
            message="Password changed successfully"
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to change password: {str(e)}", 500)
