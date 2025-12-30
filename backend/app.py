"""
Flask Application Factory

This module implements the Application Factory pattern for Flask,
allowing for flexible configuration and testing setups.

Usage:
    from app import create_app
    app = create_app('development')
    app.run()
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_cors import CORS

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config, get_config
from database import db


def create_app(config_name: str = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config_name: Configuration to use ('development', 'testing', 'production')
                    If None, uses FLASK_ENV environment variable
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Setup logging
    setup_logging(app)
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Create database tables (for development)
    with app.app_context():
        # Don't create tables automatically in production
        if config_name != 'production':
            db.create_all()
    
    return app


def init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    # SQLAlchemy
    db.init_app(app)
    
    # CORS
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-Access-Token'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])


def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""
    from blueprints.auth import auth_bp
    from blueprints.api import api_bp
    from blueprints.files import files_bp
    
    # Auth routes: /auth/login, /auth/register, etc.
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # API routes: /api/settings, /api/history, /api/chat, etc.
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # File routes: /files/upload, /files/list, etc.
    app.register_blueprint(files_bp, url_prefix='/files')


def register_error_handlers(app: Flask) -> None:
    """Register custom error handlers."""
    from utils.response import error_response
    
    @app.errorhandler(400)
    def bad_request(error):
        return error_response(
            message="Bad request",
            status_code=400
        )
    
    @app.errorhandler(401)
    def unauthorized(error):
        return error_response(
            message="Unauthorized access",
            status_code=401
        )
    
    @app.errorhandler(403)
    def forbidden(error):
        return error_response(
            message="Access forbidden",
            status_code=403
        )
    
    @app.errorhandler(404)
    def not_found(error):
        return error_response(
            message="Resource not found",
            status_code=404
        )
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return error_response(
            message="Internal server error",
            status_code=500
        )


def setup_logging(app: Flask) -> None:
    """Configure application logging."""
    if not app.debug and not app.testing:
        # Ensure logs directory exists
        logs_dir = 'logs'
        os.makedirs(logs_dir, exist_ok=True)
        
        # File handler
        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, 'app.log'),
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Knowledge Base Agent startup')


# Health check endpoint
def register_health_check(app: Flask) -> None:
    """Register health check endpoint."""
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'knowledge-base-agent'}


# Entry point for running the application
if __name__ == '__main__':
    app = create_app()
    CORS(app, resources={r"/*": {"origins":"*"}})# 开发环境配置跨域
    app.run(host='0.0.0.0', port=5001, debug=True)
