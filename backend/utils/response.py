"""
Standardized API Response Utilities

This module provides helper functions for creating consistent API responses
across all endpoints.
"""

from typing import Any, Dict, Optional
from flask import jsonify


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    **kwargs
) -> tuple:
    """
    Create a standardized success response.
    
    Args:
        data: Response data payload
        message: Success message
        status_code: HTTP status code (default: 200)
        **kwargs: Additional fields to include in response
        
    Returns:
        Tuple of (response_json, status_code)
    """
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    response.update(kwargs)
    return jsonify(response), status_code


def error_response(
    message: str = "An error occurred",
    status_code: int = 400,
    errors: Optional[Dict] = None,
    **kwargs
) -> tuple:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        status_code: HTTP status code (default: 400)
        errors: Dictionary of field-specific errors
        **kwargs: Additional fields to include in response
        
    Returns:
        Tuple of (response_json, status_code)
    """
    response = {
        "success": False,
        "message": message,
        "errors": errors
    }
    response.update(kwargs)
    return jsonify(response), status_code


def paginated_response(
    items: list,
    page: int,
    per_page: int,
    total: int,
    message: str = "Success"
) -> tuple:
    """
    Create a standardized paginated response.
    
    Args:
        items: List of items for current page
        page: Current page number
        per_page: Items per page
        total: Total number of items
        message: Success message
        
    Returns:
        Tuple of (response_json, status_code)
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return success_response(
        data=items,
        message=message,
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    )
