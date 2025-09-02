"""
Configuration Management Module

Centralized configuration management following the 12-factor app methodology.
All configuration is loaded from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('app/config/config.env')


class Config:
    """Base configuration class with all settings."""
    
    # Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Server Settings
    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = int(os.getenv('PORT', 5000))
    
    # Database Settings
    MONGO_URI = os.getenv('MONGO_URI')
    
    # Authentication Settings
    JWT_SECRET = os.getenv('JWT_SECRET')
    JWT_EXPIRATION_DAYS = int(os.getenv('JWT_EXPIRATION_DAYS', 7))
    SESSION_TIMEOUT_SECONDS = int(os.getenv('SESSION_TIMEOUT_SECONDS', 10))
    HEARTBEAT_INTERVAL_SECONDS = int(os.getenv('HEARTBEAT_INTERVAL_SECONDS', 5))
    
    # Game Settings
    MAX_ROUNDS = int(os.getenv('MAX_ROUNDS', 6))
    
    # Logging Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
