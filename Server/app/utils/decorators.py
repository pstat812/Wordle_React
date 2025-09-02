"""
Authentication Decorators

Contains decorators for HTTP and WebSocket authentication.
"""

from functools import wraps
from flask import request, jsonify, current_app
from flask_socketio import emit


def require_auth(f):
    """
    Decorator to require authentication for protected HTTP endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from ..services.auth_service import get_auth_service
        
        auth_service = get_auth_service()
        if not auth_service:
            return jsonify({
                'success': False,
                'error': 'Authentication service unavailable'
            }), 500
            
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Authorization token required'
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Verify token
        result = auth_service.verify_token(token)
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 401
        
        # Add user data to request context
        request.user = result['user']
        return f(*args, **kwargs)
    
    return decorated_function


def websocket_auth_required(f):
    """Decorator for WebSocket authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from ..services.auth_service import get_auth_service
        
        auth_service = get_auth_service()
        if not auth_service or not args or 'token' not in args[0]:
            emit('error', {'error': 'Authentication required'})
            return
        
        token = args[0]['token']
        result = auth_service.verify_token(token)
        
        if not result['success']:
            emit('error', {'error': result['error']})
            return
        
        kwargs['user'] = result['user']
        return f(*args, **kwargs)
    
    return decorated_function
