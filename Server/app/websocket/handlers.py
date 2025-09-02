"""
WebSocket Event Handlers

Handles all WebSocket events for real-time multiplayer functionality.
"""

from flask import request
from flask_socketio import emit, join_room, leave_room
from ..services.game_service import get_game_service
from ..services.lobby_service import get_lobby_service
from ..utils.decorators import websocket_auth_required
from ..utils.game_logger import game_logger

# Simple tracking of connected users
connected_users = {}  # user_id -> socket_id


def register_websocket_handlers(socketio):
    """Register all WebSocket event handlers."""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle WebSocket connection."""
        pass

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection."""
        lobby_service = get_lobby_service()
        game_service = get_game_service()
        
        # Find user and clean up
        user_id_to_remove = None
        username_to_remove = None
        for user_id, socket_id in connected_users.items():
            if socket_id == request.sid:
                user_id_to_remove = user_id
                # Try to find username from auth service if possible
                try:
                    from ..services.auth_service import get_auth_service
                    auth_service = get_auth_service()
                    if auth_service:
                        # Get username from active sessions
                        for session_data in auth_service.active_sessions.values():
                            if session_data.get('user_id') == user_id:
                                username_to_remove = session_data.get('username', 'unknown')
                                break
                except:
                    username_to_remove = 'unknown'
                break
        
        if user_id_to_remove:
            # Remove from connected users
            del connected_users[user_id_to_remove]
            
            # Handle immediate multiplayer game forfeit on WebSocket disconnect
            if game_service and username_to_remove:
                try:
                    forfeit_result = game_service.handle_player_disconnect(user_id_to_remove, username_to_remove)
                    
                    # If any multiplayer games were affected, broadcast immediate updates
                    if forfeit_result.get('games_affected', 0) > 0:
                        game_logger.logger.info(f"WebSocket disconnect: User '{username_to_remove}' forfeited {forfeit_result['games_affected']} multiplayer game(s)")
                        
                        # Find affected games and broadcast game state updates
                        for game_id, game_data in game_service.games.items():
                            if (game_data.get("game_mode") == "multiplayer" and 
                                user_id_to_remove in game_data.get("player_states", {}) and
                                game_data.get("game_over")):  # Game just ended due to disconnect
                                
                                # Broadcast game ended event to remaining players
                                winner_id = game_data.get("winner")
                                target_word = game_data.get("target_word", "")
                                
                                socketio.emit('game_ended', {
                                    'game_id': game_id,
                                    'winner_id': winner_id,
                                    'target_word': target_word,
                                    'game_status': 'finished',
                                    'reason': 'opponent_disconnected'
                                }, room=f"game_{game_id}")
                                
                                # Also broadcast updated game state
                                broadcast_game_state_update(game_id, socketio)
                                
                                game_logger.logger.info(f"Broadcast game end due to disconnect: Game {game_id}, Winner: {winner_id}")
                                
                except Exception as e:
                    game_logger.logger.error(f"Error handling multiplayer disconnect for WebSocket user {user_id_to_remove}: {e}")
            
            # Clean up lobby room membership
            if lobby_service:
                lobby_service.cleanup_after_disconnect(user_id_to_remove)
                
                # Broadcast updated lobby state
                lobby_state = lobby_service.get_lobby_state()
                socketio.emit('lobby_state_update', lobby_state, room="lobby")

    @socketio.on('join_multiplayer_game')
    @websocket_auth_required
    def handle_join_multiplayer_game(data, user=None):
        """Join a multiplayer game room for real-time updates."""
        try:
            game_service = get_game_service()
            if not game_service:
                emit('error', {'error': 'Game service unavailable'})
                return
            
            game_id = data.get('game_id')
            if not game_id:
                emit('error', {'error': 'Game ID is required'})
                return
            
            user_id = user['id']
            username = user['username']
            
            # Verify user is part of this game
            game_state = game_service.get_multiplayer_game_state(game_id, user_id)
            if not game_state:
                emit('error', {'error': 'Game not found or access denied'})
                return
            
            # Join the game room
            join_room(f"game_{game_id}")
            connected_users[user_id] = request.sid
            
            game_logger.logger.info(f"WebSocket: {username} joined multiplayer game {game_id}")
            
            # Send initial game state
            emit('game_state_update', {
                'success': True,
                'state': game_state
            })
            
            # Notify other players in the room
            emit('player_joined', {
                'user_id': user_id,
                'username': username
            }, room=f"game_{game_id}", include_self=False)
            
        except Exception as e:
            print(f"Error joining multiplayer game: {e}")
            emit('error', {'error': str(e)})

    @socketio.on('leave_multiplayer_game')
    @websocket_auth_required
    def handle_leave_multiplayer_game(data, user=None):
        """Leave a multiplayer game room."""
        try:
            game_id = data.get('game_id')
            if not game_id:
                emit('error', {'error': 'Game ID is required'})
                return
            
            user_id = user['id']
            username = user['username']
            
            # Leave the game room
            leave_room(f"game_{game_id}")
            
            if user_id in connected_users:
                del connected_users[user_id]
            
            game_logger.logger.info(f"WebSocket: {username} left multiplayer game {game_id}")
            
            # Notify other players in the room
            emit('player_left', {
                'user_id': user_id,
                'username': username
            }, room=f"game_{game_id}", include_self=False)
            
        except Exception as e:
            print(f"Error leaving multiplayer game: {e}")
            emit('error', {'error': str(e)})

    @socketio.on('join_lobby')
    @websocket_auth_required
    def handle_join_lobby(data, user=None):
        """Join the lobby for real-time room updates."""
        lobby_service = get_lobby_service()
        if not lobby_service:
            emit('error', {'error': 'Lobby service unavailable'})
            return
        
        user_id = user['id']
        connected_users[user_id] = request.sid
        
        # Join lobby WebSocket room
        join_room("lobby")
        
        # Send current lobby state
        lobby_state = lobby_service.get_lobby_state()
        emit('lobby_state_update', lobby_state)

    @socketio.on('leave_lobby')
    @websocket_auth_required
    def handle_leave_lobby(data, user=None):
        """Leave the lobby."""
        lobby_service = get_lobby_service()
        if not lobby_service:
            return
        
        user_id = user['id']
        
        # Clean up lobby room membership
        lobby_service.cleanup_after_disconnect(user_id)
        
        # Leave lobby WebSocket room
        leave_room("lobby")
        
        # Broadcast updated lobby state
        lobby_state = lobby_service.get_lobby_state()
        socketio.emit('lobby_state_update', lobby_state, room="lobby")

    @socketio.on('join_room')
    @websocket_auth_required
    def handle_join_room(data, user=None):
        """Join a multiplayer room."""
        lobby_service = get_lobby_service()
        if not lobby_service:
            emit('error', {'error': 'Lobby service unavailable'})
            return
        
        room_id = data.get('room_id')
        if not room_id:
            emit('error', {'error': 'Room ID required'})
            return
        
        user_id = user['id']
        username = user['username']
        
        # Join room
        result = lobby_service.join_room(user_id, username, room_id)
        
        # Broadcast lobby state update first
        lobby_state = lobby_service.get_lobby_state()
        socketio.emit('lobby_state_update', lobby_state, room="lobby")

        # If room is full, start game immediately
        if result.get('room_full'):
            # Notify both players that game is starting
            game_started_data = {
                'success': True,
                'game_id': result['game_id'],
                'players': result['players']
            }

            # Send to each player individually
            for player in result['players']:
                if player['id'] in connected_users:
                    socket_id = connected_users[player['id']]
                    try:
                        socketio.emit('game_started', game_started_data, room=socket_id)
                    except Exception as emit_error:
                        print(f"Failed to emit game_started to {player['username']}: {emit_error}")

            # Also broadcast to lobby room for any clients that might be listening
            socketio.emit('game_started', game_started_data, room="lobby")

            # Broadcast updated lobby state after game starts
            updated_lobby_state = lobby_service.get_lobby_state()
            socketio.emit('lobby_state_update', updated_lobby_state, room="lobby")
        
        emit('room_join_result', result)

    @socketio.on('leave_room')
    @websocket_auth_required
    def handle_leave_room(data, user=None):
        """Leave current room."""
        lobby_service = get_lobby_service()
        if not lobby_service:
            return
        
        user_id = user['id']
        
        # Leave room
        result = lobby_service.leave_room(user_id)
        
        # Broadcast lobby state update
        lobby_state = lobby_service.get_lobby_state()
        socketio.emit('lobby_state_update', lobby_state, room="lobby")
        
        emit('room_leave_result', result)

    @socketio.on('submit_guess')
    @websocket_auth_required
    def handle_submit_guess(data, user=None):
        """Submit a guess via WebSocket."""
        game_service = get_game_service()
        if not game_service:
            emit('error', {'error': 'Game service unavailable'})
            return
        
        game_id = data.get('game_id')
        guess = data.get('guess')

        if not game_id or not guess:
            emit('error', {'error': 'Game ID and guess required'})
            return

        # Process the guess
        result = game_service.make_multiplayer_guess(game_id, user['id'], guess)

        if result and 'error' not in result:
            # Check if this was a spell cast
            if result.get('spell_cast'):
                # Handle spell casting
                spell = result['spell']
                caster_id = result['caster_id']

                # Broadcast spell effect to all players in the game
                spell_data = {
                    'spell': spell,
                    'caster_id': caster_id,
                    'target_ids': []  # Will be populated with opponent IDs
                }

                # Find opponents and send spell effects
                game_data = game_service.games.get(game_id)
                if game_data:
                    for player in game_data.get("players", []):
                        if player["id"] != caster_id:
                            spell_data['target_ids'].append(player["id"])

                # Broadcast spell to all players in the game room
                socketio.emit('spell_cast', spell_data, room=f"game_{game_id}")

                # Also send result to the caster
                emit('guess_result', {'success': True, 'result': result, 'spell_cast': True})

            else:
                # Regular guess - send result to the player
                emit('guess_result', {'success': True, 'result': result})

            # Broadcast game state to all players (for both regular guesses and spells)
            broadcast_game_state_update(game_id, socketio)

        else:
            # Send error to the player
            error_msg = result.get('error') if result else 'Invalid guess'
            emit('guess_result', {'success': False, 'error': error_msg})


def broadcast_game_state_update(game_id, socketio):
    """Broadcast game state update to all players in a game."""
    try:
        game_service = get_game_service()
        if not game_service:
            return
        
        game_data = game_service.games.get(game_id)
        if not game_data or game_data.get("game_mode") != "multiplayer":
            return
        
        # Send updated state to each player individually
        for player in game_data.get("players", []):
            user_id = player["id"]
            game_state = game_service.get_multiplayer_game_state(game_id, user_id)
            
            if game_state and user_id in connected_users:
                player_socket_id = connected_users[user_id]
                socketio.emit('game_state_update', {
                    'success': True,
                    'state': game_state
                }, room=player_socket_id)
        
    except Exception as e:
        print(f"Error broadcasting game state: {e}")
        game_logger.logger.error(f"Error broadcasting game state for {game_id}: {e}")
