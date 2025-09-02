"""
Wordle Game Server Application Package

This package contains a modular, well-structured implementation of the Wordle game server
following clean architecture principles with proper separation of concerns.
"""

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from .config import Config


def create_app(config_class=Config):
    """
    Application factory pattern for creating Flask app instances.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask application instance with all extensions initialized
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)
    
    # Register blueprints
    from .controllers.auth_controller import auth_bp
    from .controllers.game_controller import game_bp
    from .controllers.lobby_controller import lobby_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(game_bp, url_prefix='/api')
    app.register_blueprint(lobby_bp, url_prefix='/api')
    
    # Register WebSocket handlers
    from .websocket.handlers import register_websocket_handlers
    register_websocket_handlers(socketio)
    
    # Store socketio instance for use in other modules
    app.socketio = socketio
    
    return app, socketio
