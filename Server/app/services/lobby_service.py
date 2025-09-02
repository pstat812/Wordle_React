"""
Lobby Service

Manages multiplayer rooms and lobby functionality.
"""

from typing import Dict, Optional


class LobbyService:
    """
    Simplified lobby manager for multiplayer rooms.
    Uses simple in-memory state without complex threading.
    """
    
    def __init__(self):
        # Simple room structure - just 3 rooms
        self.rooms = {
            1: {'id': 1, 'name': 'Room 1', 'players': []},
            2: {'id': 2, 'name': 'Room 2', 'players': []},
            3: {'id': 3, 'name': 'Room 3', 'players': []}
        }
        # Track which room each user is in
        self.user_to_room = {}  # user_id -> room_id
    
    def get_lobby_state(self):
        """Get current state of all rooms."""
        rooms = []
        for room_id, room in self.rooms.items():
            rooms.append({
                'id': room_id,
                'name': room['name'],
                'players': room['players'].copy(),
                'max_players': 2
            })
        return {'success': True, 'rooms': rooms}
    
    def join_room(self, user_id, username, room_id):
        """Join a user to a room."""
        from .game_service import get_game_service
        
        # Check if room exists
        if room_id not in self.rooms:
            return {'success': False, 'error': 'Room not found'}
        
        room = self.rooms[room_id]
        
        # Check if room is full
        if len(room['players']) >= 2:
            return {'success': False, 'error': 'Room is full'}
        
        # Check if user is already in this room
        if any(p['id'] == user_id for p in room['players']):
            return {'success': False, 'error': 'Already in this room'}
        
        # Remove from current room if in one
        self.leave_room(user_id)
        
        # Add to new room
        player = {'id': user_id, 'username': username}
        room['players'].append(player)
        self.user_to_room[user_id] = room_id
        
        # Auto-start game if room is now full
        if len(room['players']) == 2:
            game_service = get_game_service()
            if not game_service:
                return {
                    'success': False,
                    'error': 'Game service not available'
                }

            game_id = game_service.create_new_game('multiplayer')
            print(f"Created multiplayer game: {game_id}")

            # Add both players to the game
            for p in room['players']:
                result = game_service.add_player_to_multiplayer_game(game_id, p['id'], p['username'])
                print(f"Added player {p['username']} to game {game_id}: {result}")
            
            return {
                'success': True,
                'room_full': True,
                'game_id': game_id,
                'players': room['players'].copy()
            }
        
        return {
            'success': True,
            'room_full': False,
            'message': f'Joined {room["name"]}'
        }
    
    def leave_room(self, user_id):
        """Remove user from their current room."""
        if user_id not in self.user_to_room:
            return {'success': False, 'error': 'Not in any room'}
        
        room_id = self.user_to_room[user_id]
        room = self.rooms[room_id]
        
        # Remove player from room
        room['players'] = [p for p in room['players'] if p['id'] != user_id]
        del self.user_to_room[user_id]
        
        return {
            'success': True,
            'message': f'Left {room["name"]}'
        }
    
    def get_user_room(self, user_id):
        """Get the room a user is in."""
        if user_id in self.user_to_room:
            room_id = self.user_to_room[user_id]
            return self.rooms[room_id]
        return None
    
    def cleanup_after_disconnect(self, user_id):
        """Clean up when user disconnects."""
        return self.leave_room(user_id)


# Global service instance
_lobby_service = None


def get_lobby_service() -> Optional[LobbyService]:
    """Get the global lobby service instance."""
    return _lobby_service


def initialize_lobby_service() -> LobbyService:
    """Initialize the global lobby service instance."""
    global _lobby_service
    _lobby_service = LobbyService()
    return _lobby_service
