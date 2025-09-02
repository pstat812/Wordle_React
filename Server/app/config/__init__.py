"""
Configuration Package

Contains all configuration-related files and settings.

This package separates two types of configuration:
- app_config.py: Flask application configuration (environment-based)
- game_rules.py: Game rules and constants (business logic)
"""

from .app_config import Config, DevelopmentConfig, ProductionConfig, TestingConfig, config
from .game_settings import WORD_LIST, MAX_ROUNDS, validate_word_list_integrity, get_word_statistics

__all__ = [
    # App configuration
    'Config', 'DevelopmentConfig', 'ProductionConfig', 'TestingConfig', 'config',
    # Game rules
    'WORD_LIST', 'MAX_ROUNDS', 'validate_word_list_integrity', 'get_word_statistics'
]
