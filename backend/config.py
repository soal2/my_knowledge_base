"""
Flask Application Configuration

This module provides configuration classes for different environments:
- Development: Debug enabled, local databases
- Testing: In-memory databases, testing flags
- Production: Secure settings, production databases

Usage:
    from config import config
    app.config.from_object(config['development'])
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BaseConfig:
    """Base configuration with common settings."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # JWT Settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30) # 30 days for refresh tokens
    JWT_ALGORITHM = 'HS256'
    
    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # File Upload
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './data/uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt', 'md', 'pptx'}
    
    # ChromaDB
    CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', './data/chroma_db')
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
    
    # API Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100/hour"
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    
    # MySQL Database
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'knowledge_base_db')
    
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    
    # More verbose logging
    LOG_LEVEL = 'DEBUG'


class TestingConfig(BaseConfig):
    """Testing configuration."""
    
    DEBUG = True
    TESTING = True
    
    # Use SQLite for faster tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Use temporary directories
    UPLOAD_FOLDER = '/tmp/test_uploads'
    CHROMA_PERSIST_DIR = '/tmp/test_chroma'
    
    # Faster password hashing for tests
    BCRYPT_LOG_ROUNDS = 4
    
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(BaseConfig):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # MySQL Database (from environment variables)
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')
    
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    
    # Stricter rate limiting
    RATELIMIT_DEFAULT = "50/hour"
    
    LOG_LEVEL = 'WARNING'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment."""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
