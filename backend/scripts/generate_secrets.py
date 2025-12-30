#!/usr/bin/env python3
"""
Secret Key Generator

Generates secure random keys for Flask SECRET_KEY and JWT_SECRET_KEY.
Uses Python's secrets module for cryptographically secure random generation.

Usage:
    python generate_secrets.py
"""

import secrets
import string


def generate_secret_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure secret key.
    
    Args:
        length: Length of the key (default: 64 characters)
    
    Returns:
        A secure random string
    """
    # Use URL-safe base64 characters
    return secrets.token_urlsafe(length)


def generate_hex_key(length: int = 32) -> str:
    """
    Generate a hexadecimal secret key.
    
    Args:
        length: Number of bytes (default: 32 = 64 hex chars)
    
    Returns:
        A secure random hex string
    """
    return secrets.token_hex(length)


def main():
    print("=" * 60)
    print("🔐 Secret Key Generator for Flask Application")
    print("=" * 60)
    print()
    
    # Generate Flask SECRET_KEY
    flask_secret = generate_secret_key(48)
    print("Flask SECRET_KEY:")
    print(f"  {flask_secret}")
    print()
    
    # Generate JWT SECRET_KEY
    jwt_secret = generate_secret_key(48)
    print("JWT_SECRET_KEY:")
    print(f"  {jwt_secret}")
    print()
    
    print("=" * 60)
    print("📋 Copy these to your .env file:")
    print("=" * 60)
    print(f"SECRET_KEY={flask_secret}")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print()
    
    return flask_secret, jwt_secret


if __name__ == "__main__":
    main()
