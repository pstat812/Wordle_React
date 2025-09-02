"""
Game Controller

Handles all game-related HTTP endpoints.
"""

from flask import Blueprint, request, jsonify
from dataclasses import asdict
from ..services.game_service import get_game_service
from ..services.auth_service import get_auth_service
from ..utils.game_logger import game_logger

game_bp = Blueprint('game', __name__)


@game_bp.route('/new_game', methods=['POST'])
def new_game():
    """Create a new game session."""
    try:
        game_service = get_game_service()
        if not game_service:
            return jsonify({
                'success': False,
                'error': 'Game service unavailable'
            }), 500
        
        # Get game mode from request
        data = request.get_json() or {}
        game_mode = data.get('game_mode', 'wordle')  # Default to wordle
        
        # Validate game mode
        if game_mode not in ['wordle', 'absurdle']:
            return jsonify({
                'success': False,
                'error': 'Invalid game mode. Must be "wordle" or "absurdle"'
            }), 400
        
        # Log user action
        game_logger.log_user_action(request, 'new_game', extra_data={'game_mode': game_mode})
        
        game_id = game_service.create_new_game(game_mode)
        state = game_service.get_game_state(game_id)
        
        response_data = {
            'success': True,
            'game_id': game_id,
            'state': asdict(state)
        }
        
        # Log successful response
        game_logger.log_server_response(
            request, 'new_game', True, response_data, game_id,
            word_length=5, max_rounds=state.max_rounds
        )
        
        return jsonify(response_data)
        
    except Exception as e:
        # Log error
        game_logger.log_error(request, e, 'new_game')
        
        error_response = {
            'success': False,
            'error': str(e)
        }
        
        game_logger.log_server_response(request, 'new_game', False, error_response)
        return jsonify(error_response), 400


@game_bp.route('/game/<game_id>/state', methods=['GET'])
def get_state(game_id):
    """Get current game state."""
    try:
        game_service = get_game_service()
        if not game_service:
            return jsonify({
                'success': False,
                'error': 'Game service unavailable'
            }), 500
        
        # Log user action
        game_logger.log_user_action(request, 'get_state', game_id)
        
        state = game_service.get_game_state(game_id)
        if state is None:
            error_response = {
                'success': False,
                'error': 'Game not found'
            }
            game_logger.log_server_response(request, 'get_state', False, error_response, game_id)
            return jsonify(error_response), 404
        
        response_data = {
            'success': True,
            'state': asdict(state)
        }
        
        # Log successful response
        game_logger.log_server_response(
            request, 'get_state', True, response_data, game_id,
            current_round=state.current_round, game_over=state.game_over
        )
        
        return jsonify(response_data)
        
    except Exception as e:
        game_logger.log_error(request, e, 'get_state', game_id)
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'get_state', False, error_response, game_id)
        return jsonify(error_response), 500


@game_bp.route('/game/<game_id>/guess', methods=['POST'])
def make_guess(game_id):
    """Submit a guess for validation and evaluation."""
    try:
        game_service = get_game_service()
        if not game_service:
            return jsonify({
                'success': False,
                'error': 'Game service unavailable'
            }), 500
        
        data = request.get_json()
        if not data or 'guess' not in data:
            error_response = {
                'success': False,
                'error': 'Guess is required'
            }
            game_logger.log_server_response(request, 'submit_guess', False, error_response, game_id)
            return jsonify(error_response), 400
        
        guess = data['guess']
        
        # Log user action
        game_logger.log_user_action(
            request, 'submit_guess', game_id, 
            guess=guess, guess_length=len(guess)
        )
        
        # Validate guess first
        is_valid, error = game_service.is_valid_guess(game_id, guess)
        if not is_valid:
            error_response = {
                'success': False,
                'error': error
            }
            game_logger.log_server_response(
                request, 'submit_guess', False, error_response, game_id,
                validation_error=error, attempted_guess=guess
            )
            return jsonify(error_response), 400
        
        # Process guess
        state = game_service.make_guess(game_id, guess)
        if state is None:
            error_response = {
                'success': False,
                'error': 'Failed to process guess'
            }
            game_logger.log_server_response(request, 'submit_guess', False, error_response, game_id)
            return jsonify(error_response), 500
        
        response_data = {
            'success': True,
            'state': asdict(state)
        }
        
        # Log successful response with game events
        game_logger.log_server_response(
            request, 'submit_guess', True, response_data, game_id,
            guess=guess, round=state.current_round, game_over=state.game_over
        )
        
        # Log special game events
        if state.game_over:
            if state.won:
                game_logger.log_game_event(
                    game_id, 'game_won', request.remote_addr,
                    rounds_used=state.current_round, target_word=state.answer,
                    winning_guess=guess
                )
            else:
                game_logger.log_game_event(
                    game_id, 'game_lost', request.remote_addr,
                    rounds_used=state.current_round, target_word=state.answer,
                    final_guess=guess
                )
        
        return jsonify(response_data)
        
    except Exception as e:
        game_logger.log_error(request, e, 'submit_guess', game_id)
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'submit_guess', False, error_response, game_id)
        return jsonify(error_response), 500


@game_bp.route('/game/<game_id>', methods=['DELETE'])
def delete_game(game_id):
    """Delete a completed game session."""
    try:
        game_service = get_game_service()
        if not game_service:
            return jsonify({
                'success': False,
                'error': 'Game service unavailable'
            }), 500
        
        # Log user action
        game_logger.log_user_action(request, 'delete_game', game_id)
        
        success = game_service.delete_game(game_id)
        
        response_data = {
            'success': success
        }
        
        # Log response
        game_logger.log_server_response(request, 'delete_game', success, response_data, game_id)
        
        if success:
            game_logger.log_game_event(game_id, 'game_deleted', request.remote_addr)
        
        return jsonify(response_data)
        
    except Exception as e:
        game_logger.log_error(request, e, 'delete_game', game_id)
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'delete_game', False, error_response, game_id)
        return jsonify(error_response), 500


@game_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        game_service = get_game_service()
        auth_service = get_auth_service()
        
        # Log user action
        game_logger.log_user_action(request, 'health_check')
        
        # Get log statistics
        log_stats = game_logger.get_log_stats()
        
        response_data = {
            'status': 'healthy',
            'active_games': len(game_service.games) if game_service else 0,
            'log_stats': log_stats,
            'auth_available': auth_service is not None,
            'active_sessions': auth_service.get_active_sessions_count() if auth_service else 0,
            'heartbeat_monitoring': True
        }
        
        # Log response
        game_logger.log_server_response(request, 'health_check', True, response_data)
        
        return jsonify(response_data)
        
    except Exception as e:
        game_logger.log_error(request, e, 'health_check')
        error_response = {
            'status': 'error',
            'error': str(e)
        }
        game_logger.log_server_response(request, 'health_check', False, error_response)
        return jsonify(error_response), 500