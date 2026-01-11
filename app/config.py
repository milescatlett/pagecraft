"""Application configuration"""
import os
from datetime import timedelta


class Config:
    """Base configuration class"""

    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cms.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload configuration
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit on CSRF tokens
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_HEADERS_ENABLED = True

    # Admin domains - requests from these domains will show the CMS admin interface
    ADMIN_DOMAINS = [
        'localhost', '127.0.0.1', 'localhost:5000', '127.0.0.1:5000',
        'pagecraft.host', 'www.pagecraft.host'
    ]


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    # Override secret key requirement
    def __init__(self):
        if self.SECRET_KEY == 'your-secret-key-change-in-production':
            raise ValueError("Must set SECRET_KEY environment variable in production!")


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
