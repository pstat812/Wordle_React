"""
Authentication Controller

Handles all authentication-related HTTP endpoints.
"""

from flask import Blueprint, request, jsonify
from ..services.auth_service import get_auth_service
from ..utils.decorators import require_auth
from ..utils.game_logger import game_logger

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        auth_service = get_auth_service()
        if not auth_service:
            return jsonify({
                'success': False,
                'error': 'Authentication service unavailable'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        # Log user action
        game_logger.log_user_action(request, 'register', extra_data={'username': username})
        
        result = auth_service.register_user(username, password)
        
        if result['success']:
            game_logger.log_server_response(request, 'register', True, result)
            return jsonify(result), 201
        else:
            game_logger.log_server_response(request, 'register', False, result)
            return jsonify(result), 400
            
    except Exception as e:
        game_logger.log_error(request, e, 'register')
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'register', False, error_response)
        return jsonify(error_response), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user and return JWT token."""
    try:
        auth_service = get_auth_service()
        if not auth_service:
            return jsonify({
                'success': False,
                'error': 'Authentication service unavailable'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        # Log user action
        game_logger.log_user_action(request, 'login', extra_data={'username': username})
        
        result = auth_service.login_user(username, password)
        
        if result['success']:
            game_logger.log_server_response(request, 'login', True, {
                'success': True,
                'user': result['user']  # Don't log the token
            })
            return jsonify(result)
        else:
            game_logger.log_server_response(request, 'login', False, result)
            return jsonify(result), 401
            
    except Exception as e:
        game_logger.log_error(request, e, 'login')
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'login', False, error_response)
        return jsonify(error_response), 500


@auth_bp.route('/verify', methods=['GET'])
@require_auth
def verify_token():
    """Verify JWT token and return user info."""
    try:
        # User data is already in request.user from the decorator
        response_data = {
            'success': True,
            'user': request.user
        }
        
        game_logger.log_server_response(request, 'verify_token', True, response_data)
        return jsonify(response_data)
        
    except Exception as e:
        game_logger.log_error(request, e, 'verify_token')
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'verify_token', False, error_response)
        return jsonify(error_response), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout a user and invalidate their session."""
    try:
        auth_service = get_auth_service()
        if not auth_service:
            return jsonify({
                'success': False,
                'error': 'Authentication service unavailable'
            }), 500
        
        token = None
        username = None
        
        # Try to get token from Authorization header first (normal logout)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            # Verify token to get user info for logging
            verify_result = auth_service.verify_token(token)
            if verify_result['success']:
                username = verify_result['user']['username']
        
        # If no Authorization header, try query parameter (sendBeacon logout)
        if not token:
            token = request.args.get('token')
            if token:
                # Verify token to get user info for logging
                verify_result = auth_service.verify_token(token)
                if verify_result['success']:
                    username = verify_result['user']['username']
        
        # If still no token, return error
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authorization token required'
            }), 401
        
        # Log user action (use username if available, otherwise 'unknown')
        game_logger.log_user_action(request, 'logout', extra_data={'user': username or 'unknown'})
        
        result = auth_service.logout_user(token)
        
        if result['success']:
            game_logger.log_server_response(request, 'logout', True, result)
            return jsonify(result)
        else:
            game_logger.log_server_response(request, 'logout', False, result)
            return jsonify(result), 400
            
    except Exception as e:
        game_logger.log_error(request, e, 'logout')
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'logout', False, error_response)
        return jsonify(error_response), 500


@auth_bp.route('/heartbeat', methods=['POST'])
@require_auth
def heartbeat():
    """Update session heartbeat to keep it alive."""
    try:
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
        
        # Log heartbeat received (debug level only)
        username = request.user.get('username', 'unknown') if hasattr(request, 'user') else 'unknown'
        game_logger.logger.debug(f"Heartbeat: {username}")
        
        # Update session heartbeat
        result = auth_service.update_session_activity(token)
        
        if result['success']:
            return jsonify({'success': True, 'message': 'Heartbeat updated'})
        else:
            game_logger.logger.warning(f"Heartbeat update failed for {username}: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        game_logger.logger.error(f"Heartbeat endpoint error: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return jsonify(error_response), 500


@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get user profile information."""
    try:
        auth_service = get_auth_service()
        user_data = auth_service.get_user_by_id(request.user['id'])
        if not user_data:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        response_data = {
            'success': True,
            'user': user_data
        }
        
        game_logger.log_server_response(request, 'get_profile', True, response_data)
        return jsonify(response_data)
        
    except Exception as e:
        game_logger.log_error(request, e, 'get_profile')
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'get_profile', False, error_response)
        return jsonify(error_response), 500
