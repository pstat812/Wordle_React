"""
Lobby Controller

Handles all lobby and multiplayer-related HTTP endpoints.
"""

from flask import Blueprint, request, jsonify
from ..services.game_service import get_game_service
from ..services.lobby_service import get_lobby_service
from ..utils.decorators import require_auth
from ..utils.game_logger import game_logger

lobby_bp = Blueprint('lobby', __name__)


@lobby_bp.route('/lobby/state', methods=['GET'])
@require_auth
def get_lobby_state():
    """Get current lobby state."""
    try:
        lobby_service = get_lobby_service()
        if not lobby_service:
            return jsonify({
                'success': False,
                'error': 'Lobby service unavailable'
            }), 500
        
        result = lobby_service.get_lobby_state()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@lobby_bp.route('/multiplayer/<game_id>/state', methods=['GET'])
@require_auth
def get_multiplayer_state(game_id):
    """Get multiplayer game state for current player."""
    try:
        game_service = get_game_service()
        if not game_service:
            return jsonify({
                'success': False,
                'error': 'Game service unavailable'
            }), 500
        
        user_id = request.user['id']
        
        # Log user action
        game_logger.log_user_action(request, 'get_multiplayer_state', game_id)
        
        result = game_service.get_multiplayer_game_state(game_id, user_id)
        
        if result:
            response_data = {
                'success': True,
                'state': result
            }
            game_logger.log_server_response(request, 'get_multiplayer_state', True, response_data, game_id)
            return jsonify(response_data)
        else:
            error_response = {
                'success': False,
                'error': 'Game not found or access denied'
            }
            game_logger.log_server_response(request, 'get_multiplayer_state', False, error_response, game_id)
            return jsonify(error_response), 404
            
    except Exception as e:
        game_logger.log_error(request, e, 'get_multiplayer_state', game_id)
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'get_multiplayer_state', False, error_response, game_id)
        return jsonify(error_response), 500


@lobby_bp.route('/multiplayer/<game_id>/guess', methods=['POST'])
@require_auth
def make_multiplayer_guess(game_id):
    """Submit a guess in multiplayer game."""
    try:
        game_service = get_game_service()
        if not game_service:
            return jsonify({
                'success': False,
                'error': 'Game service unavailable'
            }), 500
        
        data = request.get_json()
        if not data or 'guess' not in data:
            return jsonify({
                'success': False,
                'error': 'Guess is required'
            }), 400
        
        guess = data['guess']
        user_id = request.user['id']
        
        # Log user action
        game_logger.log_user_action(request, 'multiplayer_guess', game_id, guess=guess)
        
        result = game_service.make_multiplayer_guess(game_id, user_id, guess)
        
        if result:
            # Check if result contains an error
            if "error" in result:
                error_response = {
                    'success': False,
                    'error': result["error"]
                }
                game_logger.log_server_response(request, 'multiplayer_guess', False, error_response, game_id)
                return jsonify(error_response), 400
            else:
                response_data = {
                    'success': True,
                    'result': result
                }
                game_logger.log_server_response(request, 'multiplayer_guess', True, response_data, game_id)
                return jsonify(response_data)
        else:
            error_response = {
                'success': False,
                'error': 'Invalid guess or game not found'
            }
            game_logger.log_server_response(request, 'multiplayer_guess', False, error_response, game_id)
            return jsonify(error_response), 400
            
    except Exception as e:
        game_logger.log_error(request, e, 'multiplayer_guess', game_id)
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'multiplayer_guess', False, error_response, game_id)
        return jsonify(error_response), 500
