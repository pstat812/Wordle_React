"""
Wordle Game Server - Server-side Game Logic and API

This module implements the server-side game engine for the client-server Wordle architecture.
The server manages game state, word selection, and validation while keeping the answer
secure from the client until game completion.

"""

import random
import uuid
import os
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from dotenv import load_dotenv
from game_settings import WORD_LIST, MAX_ROUNDS
from game_logger import game_logger
from auth_service import AuthService

load_dotenv('config.env')


class LetterStatus(Enum):
    """Letter evaluation status matching the original game logic."""
    HIT = "HIT"
    PRESENT = "PRESENT"
    MISS = "MISS"
    UNUSED = "UNUSED"


@dataclass
class GameState:
    """Server-side game state representation."""
    game_id: str
    current_round: int
    max_rounds: int
    game_over: bool
    won: bool
    guesses: List[str]
    guess_results: List[List[Tuple[str, str]]]  # Letter status as string for JSON serialization
    letter_status: Dict[str, str]
    answer: Optional[str] = None  # Only included when game is over
    game_mode: str = "wordle"  # "wordle" or "absurdle"


class WordleServer:
    """
    Server-side Wordle game engine managing multiple game sessions.
    
    This class handles:
    - Game session management with unique game IDs
    - Word selection and secure answer storage
    - Guess validation and evaluation
    - Game state management without exposing answers to clients
    """
    
    def __init__(self):
        self.games: Dict[str, Dict] = {}  # Store active games by game_id
        self.word_list = WORD_LIST.copy()
    
    def create_new_game(self, game_mode: str = "wordle") -> str:
        """
        Creates a new game session with a randomly selected word.
        
        Returns:
            str: Unique game ID for this session
        """
        game_id = str(uuid.uuid4())
        max_rounds = MAX_ROUNDS
        
        # Select random word (server keeps this secret)
        target_word = random.choice(self.word_list)
        
        # Initialize game state
        game_data = {
            "target_word": target_word if game_mode in ["wordle", "multiplayer"] else None,
            "current_round": 0,
            "max_rounds": max_rounds if game_mode in ["wordle", "multiplayer"] else 1,  # Start with 1 for Absurdle
            "game_over": False,
            "won": False,
            "guesses": [],
            "guess_results": [],
            "letter_status": {letter: LetterStatus.UNUSED.value for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
            "game_mode": game_mode,
            "candidate_words": self.word_list.copy() if game_mode == "absurdle" else [],
            # Multiplayer specific fields
            "players": [] if game_mode == "multiplayer" else None,
            "player_states": {} if game_mode == "multiplayer" else None,
            "winner": None if game_mode == "multiplayer" else None,
            "game_status": "active" if game_mode == "multiplayer" else None  # "active", "finished", "draw"
        }
        
        self.games[game_id] = game_data
        return game_id
    
    def get_game_state(self, game_id: str) -> Optional[GameState]:
        """
        Returns the current game state for a session (without revealing the answer).
        
        Args:
            game_id: Unique game identifier
            
        Returns:
            GameState object or None if game not found
        """
        if game_id not in self.games:
            return None
        
        game = self.games[game_id]
        
        # Create state object without exposing the answer unless game is over
        answer = None
        if game["game_over"]:
            if game["game_mode"] == "wordle":
                answer = game["target_word"]
            elif game["game_mode"] == "absurdle" and len(game["candidate_words"]) == 1:
                answer = game["candidate_words"][0]
        
        return GameState(
            game_id=game_id,
            current_round=game["current_round"],
            max_rounds=game["max_rounds"],
            game_over=game["game_over"],
            won=game["won"],
            guesses=game["guesses"].copy(),
            guess_results=game["guess_results"].copy(),
            letter_status=game["letter_status"].copy(),
            answer=answer,
            game_mode=game["game_mode"]
        )
    
    def is_valid_guess(self, game_id: str, guess: str) -> Tuple[bool, str]:
        """
        Validates a guess for a specific game session.
        
        Args:
            game_id: Unique game identifier
            guess: The word to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if game_id not in self.games:
            return False, "Game not found"
        
        game = self.games[game_id]
        
        if game["game_over"]:
            return False, "Game is already over"
        
        if not guess or not isinstance(guess, str):
            return False, "Guess must be a valid string"
        
        normalized_guess = guess.strip().upper()
        
        if len(normalized_guess) != 5:
            return False, "Guess must be exactly 5 letters"
        
        if not normalized_guess.isalpha():
            return False, "Guess must contain only letters"
        
        if normalized_guess not in self.word_list:
            return False, "Word not in word list"
        
        return True, ""
    
    def make_guess(self, game_id: str, guess: str) -> Optional[GameState]:
        """
        Processes a guess and updates game state.
        
        Args:
            game_id: Unique game identifier
            guess: The 5-letter word guess
            
        Returns:
            Updated GameState or None if invalid
        """
        is_valid, error = self.is_valid_guess(game_id, guess)
        if not is_valid:
            return None
        
        game = self.games[game_id]
        normalized_guess = guess.strip().upper()
        
        # Handle different game modes
        if game["game_mode"] == "wordle":
            target_word = game["target_word"]
            evaluations = self._evaluate_guess_against_target(normalized_guess, target_word)
        else:  # absurdle
            evaluations = self._process_absurdle_guess(game, normalized_guess)
        
        # Update game state
        game["current_round"] += 1
        game["guesses"].append(normalized_guess)
        game["guess_results"].append([(letter, status.value) for letter, status in evaluations])
        
        # Update letter status
        self._update_letter_status(game["letter_status"], evaluations)
        
        # Check win condition based on game mode
        if game["game_mode"] == "wordle":
            target_word = game["target_word"]
            if normalized_guess == target_word:
                game["won"] = True
                game["game_over"] = True
            elif game["current_round"] >= game["max_rounds"]:
                game["game_over"] = True
        else:  # absurdle
            # For Absurdle, always extend max_rounds to accommodate the next guess
            game["max_rounds"] = game["current_round"] + 1
            
            # Check if only one candidate remains and it matches the guess
            if len(game["candidate_words"]) == 1 and normalized_guess == game["candidate_words"][0]:
                game["won"] = True
                game["game_over"] = True
            elif len(game["candidate_words"]) == 0:
                # Shouldn't happen in well-implemented Absurdle
                game["game_over"] = True
        
        return self.get_game_state(game_id)
    
    def _evaluate_guess_against_target(self, guess: str, target: str) -> List[Tuple[str, LetterStatus]]:
        """
        Implements the authentic Wordle letter evaluation algorithm.
        Same logic as the original game engine.
        """
        result: List[Tuple[str, Optional[LetterStatus]]] = []
        
        # Create working copies to track letter consumption
        target_chars = list(target)
        guess_chars = list(guess)
        
        # First pass: Mark all exact position matches (HIT)
        for i in range(5):
            if guess_chars[i] == target_chars[i]:
                result.append((guess_chars[i], LetterStatus.HIT))
                # Mark as consumed to prevent double-counting
                target_chars[i] = None  # type: ignore
                guess_chars[i] = None   # type: ignore
            else:
                result.append((guess_chars[i], None))  # Placeholder for second pass
        
        # Second pass: Mark present letters (PRESENT) and misses (MISS)
        for i in range(5):
            if result[i][1] is None:  # Not already marked as HIT
                letter = guess[i]
                
                # Check if letter exists in remaining target characters
                if letter in target_chars:
                    result[i] = (letter, LetterStatus.PRESENT)
                    # Remove first occurrence to prevent double-counting
                    target_chars[target_chars.index(letter)] = None  # type: ignore
                else:
                    result[i] = (letter, LetterStatus.MISS)
        
        # Type assertion: all placeholders should be resolved
        return [(letter, status) for letter, status in result if status is not None]
    
    def _update_letter_status(self, letter_status: Dict[str, str], evaluations: List[Tuple[str, LetterStatus]]) -> None:
        """
        Updates global letter status tracking based on guess results.
        """
        for letter, new_status in evaluations:
            current_status = LetterStatus(letter_status[letter])
            
            # Status can only progress in priority order
            if new_status == LetterStatus.HIT:
                letter_status[letter] = LetterStatus.HIT.value
            elif new_status == LetterStatus.PRESENT and current_status != LetterStatus.HIT:
                letter_status[letter] = LetterStatus.PRESENT.value
            elif new_status == LetterStatus.MISS and current_status == LetterStatus.UNUSED:
                letter_status[letter] = LetterStatus.MISS.value
    
    def _process_absurdle_guess(self, game: Dict, guess: str) -> List[Tuple[str, LetterStatus]]:
        """
        Process a guess in Absurdle mode by finding the worst possible feedback.
        """
        candidate_words = game["candidate_words"]
        
        # Group candidate words by the patterns they actually produce
        # This is more efficient and accurate than generating all theoretical patterns
        pattern_groups = {}
        
        for word in candidate_words:
            # Calculate the actual pattern this word would produce
            pattern = self._evaluate_guess_against_target(guess, word)
            pattern_key = self._pattern_to_key(pattern)
            
            # Add to pattern group
            if pattern_key not in pattern_groups:
                pattern_groups[pattern_key] = {
                    'pattern': pattern,
                    'words': []
                }
            pattern_groups[pattern_key]['words'].append(word)
        
        # All groups are valid since they come from actual words
        valid_groups = list(pattern_groups.values())
        
        if not valid_groups:
            # Fallback - shouldn't happen
            return [(letter, LetterStatus.MISS) for letter in guess]
        
        # Find the group with maximum words (worst case for player)
        # Absurdle should avoid giving the player a win unless absolutely necessary
        
        # First, separate winning and non-winning groups
        winning_groups = []
        non_winning_groups = []
        
        for group in valid_groups:
            is_win_group = all(status == LetterStatus.HIT for _, status in group['pattern'])
            if is_win_group:
                winning_groups.append(group)
            else:
                non_winning_groups.append(group)
        
        # Choose from non-winning groups first (if any exist)
        if non_winning_groups:
            # Find the non-winning group with maximum words
            chosen_group = max(non_winning_groups, key=lambda g: len(g['words']))
        else:
            # Only winning groups exist, choose the one with maximum words
            chosen_group = max(winning_groups, key=lambda g: len(g['words']))
        
        # Update candidate words
        game["candidate_words"] = chosen_group['words']
        
        return chosen_group['pattern']
    
    def _generate_all_patterns(self, guess: str) -> List[List[Tuple[str, LetterStatus]]]:
        """
        Generate all possible feedback patterns for a guess (3^5 = 243 patterns).
        """
        patterns = []
        
        for i in range(243):  # 3^5 possible patterns
            pattern = []
            num = i
            
            for j in range(5):
                status = num % 3
                letter = guess[j]
                
                if status == 0:
                    pattern.append((letter, LetterStatus.MISS))
                elif status == 1:
                    pattern.append((letter, LetterStatus.PRESENT))
                else:
                    pattern.append((letter, LetterStatus.HIT))
                
                num = num // 3
            
            patterns.append(pattern)
        
        return patterns
    
    def _pattern_to_key(self, pattern: List[Tuple[str, LetterStatus]]) -> str:
        """
        Convert a pattern to a string key for comparison.
        """
        return ''.join([f"{letter}:{status.value}" for letter, status in pattern])
    
    def _is_pattern_consistent(self, guess: str, pattern: List[Tuple[str, LetterStatus]], target: str) -> bool:
        """
        Check if a pattern is consistent with a target word.
        """
        actual_pattern = self._evaluate_guess_against_target(guess, target)
        
        # Compare patterns
        for i in range(5):
            if pattern[i][1] != actual_pattern[i][1]:
                return False
        
        return True
    
    def delete_game(self, game_id: str) -> bool:
        """
        Removes a completed game session from memory.
        
        Args:
            game_id: Unique game identifier
            
        Returns:
            bool: True if game was deleted, False if not found
        """
        if game_id in self.games:
            del self.games[game_id]
            return True
        return False

    def handle_player_disconnect(self, user_id: str, username: str) -> Dict[str, int]:
        """
        Handle player disconnection from active multiplayer games.
        When a player disconnects, they automatically forfeit any active multiplayer games.
        
        Args:
            user_id: ID of the disconnected player
            username: Username of the disconnected player (for logging)
            
        Returns:
            Dictionary with count of games affected
        """
        games_affected = 0
        games_to_delete = []
        
        # Find all multiplayer games where this user is a player
        for game_id, game_data in self.games.items():
            if (game_data.get("game_mode") == "multiplayer" and 
                user_id in game_data.get("player_states", {})):
                
                # Check if game is still active
                if game_data.get("game_status") == "active" and not game_data.get("game_over"):
                    games_affected += 1
                    
                    # Mark the disconnected player as forfeited
                    player_state = game_data["player_states"][user_id]
                    player_state["finished"] = True
                    player_state["game_over"] = True
                    player_state["won"] = False
                    
                    # Find opponent and declare them winner (if they haven't also disconnected)
                    opponent_id = None
                    opponent_won = False
                    
                    for pid in game_data["player_states"]:
                        if pid != user_id:
                            opponent_id = pid
                            opponent_state = game_data["player_states"][pid]
                            
                            # Only declare opponent winner if they're still connected/active
                            if not opponent_state.get("finished", False):
                                opponent_state["won"] = True
                                opponent_state["finished"] = True
                                opponent_state["game_over"] = True
                                game_data["winner"] = opponent_id
                                opponent_won = True
                            break
                    
                    # Mark game as finished
                    game_data["game_status"] = "finished" if opponent_won else "abandoned"
                    game_data["game_over"] = True
                    
                    # Log the forfeit event
                    game_logger.log_game_event(
                        game_id, 
                        'player_disconnected_forfeit', 
                        'system',
                        disconnected_player=username,
                        opponent_id=opponent_id,
                        game_result='forfeit'
                    )
                    
                    # Clean up the room associated with this game
                    if lobby_manager:
                        lobby_manager.cleanup_room_after_game(game_id)
                    
                    print(f"🏳️ Game {game_id}: {username} forfeited due to disconnect")
        
        return {"games_affected": games_affected}

    def add_player_to_multiplayer_game(self, game_id: str, user_id: str, username: str) -> bool:
        """Add a player to a multiplayer game."""
        if game_id not in self.games:
            return False
        
        game_data = self.games[game_id]
        if game_data["game_mode"] != "multiplayer":
            return False
        
        # Initialize player state
        player_info = {"id": user_id, "username": username}
        if player_info not in game_data["players"]:
            game_data["players"].append(player_info)
            game_data["player_states"][user_id] = {
                "current_round": 0,
                "guesses": [],
                "guess_results": [],
                "letter_status": {letter: LetterStatus.UNUSED.value for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
                "game_over": False,
                "won": False,
                "finished": False
            }
        return True

    def make_multiplayer_guess(self, game_id: str, user_id: str, guess: str) -> Optional[Dict]:
        """Process a guess in multiplayer mode."""
        if game_id not in self.games:
            return None
        
        game_data = self.games[game_id]
        if game_data["game_mode"] != "multiplayer":
            return None
        
        if user_id not in game_data["player_states"]:
            return None
        
        player_state = game_data["player_states"][user_id]
        
        # Check if player already finished
        if player_state["finished"]:
            return None
        
        # Check if game is over
        if game_data["game_status"] != "active":
            return None
        
        # Validate guess using the same method as regular Wordle
        is_valid, error_message = self.is_valid_guess(game_id, guess)
        if not is_valid:
            return {"error": error_message}
        
        # Process guess
        target_word = game_data["target_word"]
        result = self._evaluate_guess_against_target(guess, target_word)
        
        # Update player state
        player_state["current_round"] += 1
        player_state["guesses"].append(guess)
        player_state["guess_results"].append([(letter, status.value) for letter, status in result])
        
        # Update letter status for this player
        for letter, status in result:
            current_status = LetterStatus(player_state["letter_status"][letter])
            new_status = status  # status is already a LetterStatus enum
            
            if current_status == LetterStatus.UNUSED or \
               (current_status == LetterStatus.MISS and new_status in [LetterStatus.PRESENT, LetterStatus.HIT]) or \
               (current_status == LetterStatus.PRESENT and new_status == LetterStatus.HIT):
                player_state["letter_status"][letter] = status.value
        
        # Check if player won
        if guess == target_word:
            player_state["won"] = True
            player_state["game_over"] = True
            player_state["finished"] = True
            game_data["winner"] = user_id
            game_data["game_status"] = "finished"
            game_data["game_over"] = True
            game_data["won"] = True
            
            # DON'T clean up here - let the WebSocket handler do it after broadcasting
        
        # Check if player used all attempts
        elif player_state["current_round"] >= game_data["max_rounds"]:
            player_state["game_over"] = True
            player_state["finished"] = True
            
            # Check if both players finished
            all_finished = all(
                game_data["player_states"][pid]["finished"] 
                for pid in game_data["player_states"]
            )
            
            if all_finished and game_data["winner"] is None:
                game_data["game_status"] = "draw"
                game_data["game_over"] = True
                
                # DON'T clean up here - let the WebSocket handler do it after broadcasting
        
        # Note: WebSocket broadcasting is now handled in the WebSocket handler
        # to ensure proper order: broadcast first, then cleanup
        
        return {
            "player_state": player_state,
            "game_status": game_data["game_status"],
            "winner": game_data["winner"],
            "game_over": game_data["game_over"],
            "target_word": target_word if game_data["game_over"] else None
        }

    def get_multiplayer_game_state(self, game_id: str, user_id: str) -> Optional[Dict]:
        """Get multiplayer game state for a specific player."""
        if game_id not in self.games:
            return None
        
        game_data = self.games[game_id]
        if game_data["game_mode"] != "multiplayer":
            return None
        
        if user_id not in game_data["player_states"]:
            return None
        
        player_state = game_data["player_states"][user_id]
        
        # Get opponent info
        opponent = None
        for player in game_data["players"]:
            if player["id"] != user_id:
                opponent = {
                    "username": player["username"],
                    "current_round": game_data["player_states"][player["id"]]["current_round"],
                    "finished": game_data["player_states"][player["id"]]["finished"],
                    "won": game_data["player_states"][player["id"]]["won"]
                }
                break
        
        return {
            "game_id": game_id,
            "game_mode": "multiplayer",
            "game_status": game_data["game_status"],
            "winner": game_data["winner"],
            "game_over": game_data["game_over"],
            "target_word": game_data["target_word"] if game_data["game_over"] else None,
            "max_rounds": game_data["max_rounds"],
            "player": {
                "current_round": player_state["current_round"],
                "guesses": player_state["guesses"],
                "guess_results": player_state["guess_results"],
                "letter_status": player_state["letter_status"],
                "game_over": player_state["game_over"],
                "won": player_state["won"],
                "finished": player_state["finished"]
            },
            "opponent": opponent,
            "players": game_data["players"]
        }


# Flask REST API setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize SocketIO with CORS support
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

server = WordleServer()

# Load configuration from environment variables
MONGO_URI = os.getenv('MONGO_URI')
JWT_SECRET = os.getenv('JWT_SECRET')
HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Initialize authentication service
try:
    auth_service = AuthService(MONGO_URI, JWT_SECRET)
    print("✅ Authentication service initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize authentication service: {e}")
    auth_service = None


def heartbeat_cleanup_worker():
    """
    Background worker that periodically cleans up expired sessions based on missed heartbeats.
    Runs every 15 seconds to check for users who haven't sent heartbeats.
    """
    print("🔄 Heartbeat cleanup worker started")
    while True:
        try:
            if auth_service:
                # Clean up sessions that haven't sent heartbeats in the last 10 seconds
                cleanup_result = auth_service.cleanup_expired_sessions()
                
                # Debug logging
                if cleanup_result["cleaned_count"] > 0:
                    print(f"🧹 Heartbeat cleanup found {cleanup_result['cleaned_count']} expired sessions")
                
                if cleanup_result["cleaned_count"] > 0:
                    game_logger.logger.info(f"🧹 Heartbeat cleanup: Removed {cleanup_result['cleaned_count']} expired sessions")
                    
                    # Log individual logout events for each disconnected user
                    for user_info in cleanup_result["disconnected_users"]:
                        username = user_info["username"]
                        user_id = user_info.get("user_id")
                        last_heartbeat = user_info["last_heartbeat"]
                        session_duration = user_info["session_duration"]
                        
                        # Simple console output for monitoring
                        print(f"🔌 {username} - Auto logout (missed heartbeat)")
                        
                        # Auto-leave lobby room if user was in one
                        if user_id and lobby_manager:
                            try:
                                print(f"🔍 Checking if user {username} ({user_id}) is in a lobby room...")
                                leave_result = lobby_manager.leave_room(user_id)
                                if leave_result['success']:
                                    game_logger.logger.info(f"🚪 User '{username}' automatically removed from lobby room due to disconnect")
                                    print(f"🚪 {username} - Auto removed from lobby room")
                                else:
                                    print(f"ℹ️ User {username} was not in any lobby room")
                            except Exception as lobby_error:
                                game_logger.logger.error(f"❌ Failed to remove disconnected user {username} from lobby: {lobby_error}")
                                print(f"❌ Lobby removal error for {username}: {lobby_error}")
                        else:
                            print(f"⚠️ Cannot remove {username} from lobby - user_id: {user_id}, lobby_manager: {lobby_manager is not None}")
                        
                        # Auto-forfeit multiplayer games if user was in one
                        if user_id and server:
                            try:
                                print(f"🔍 Checking if user {username} ({user_id}) is in an active multiplayer game...")
                                forfeit_result = server.handle_player_disconnect(user_id, username)
                                if forfeit_result['games_affected'] > 0:
                                    game_logger.logger.info(f"🏳️ User '{username}' forfeited {forfeit_result['games_affected']} multiplayer game(s) due to disconnect")
                                    print(f"🏳️ {username} - Auto forfeited {forfeit_result['games_affected']} multiplayer game(s)")
                                else:
                                    print(f"ℹ️ User {username} was not in any active multiplayer games")
                            except Exception as game_error:
                                game_logger.logger.error(f"❌ Failed to handle multiplayer game disconnect for {username}: {game_error}")
                                print(f"❌ Multiplayer game disconnect error for {username}: {game_error}")
                        
                        # Detailed log to file
                        game_logger.logger.info(f"🔌 User '{username}' automatically logged out due to missed heartbeat. Last heartbeat: {last_heartbeat}, Session duration: {session_duration:.1f}s")
                        
                        # Create a mock request object for logging USER_ACTION (same as manual logout)
                        class MockRequest:
                            def __init__(self, username):
                                self.remote_addr = 'system'  # System-initiated
                                self.method = 'AUTO_LOGOUT'
                                self.path = '/heartbeat/timeout'
                                self.user_agent = 'Heartbeat Monitor'
                                self.username = username
                        
                        mock_request = MockRequest(username)
                        
                        # Log USER_ACTION logout event (same as manual logout button)
                        game_logger.log_user_action(
                            mock_request, 
                            'logout', 
                            extra_data={
                                'user': username,
                                'reason': 'missed_heartbeat',
                                'automatic': True,
                                'last_heartbeat': str(last_heartbeat),
                                'session_duration': f"{session_duration:.1f}s"
                            }
                        )
                        
                        # Log server response for the automatic logout
                        game_logger.log_server_response(
                            mock_request, 
                            'logout', 
                            True, 
                            {
                                'success': True, 
                                'message': 'User automatically logged out due to missed heartbeat',
                                'reason': 'missed_heartbeat'
                            }
                        )
                        
                        # Log as a game event for consistency with manual logouts
                        game_logger.log_game_event(
                            None,  # No specific game_id for auth events
                            'user_disconnected',
                            'system',  # System-initiated logout
                            username=username,
                            reason='missed_heartbeat',
                            last_heartbeat=str(last_heartbeat),
                            session_duration_seconds=session_duration
                        )
                
        except Exception as e:
            game_logger.logger.error(f"❌ Error in heartbeat cleanup worker: {e}")
        
        # Wait 15 seconds before next cleanup (reduced for faster testing)
        time.sleep(15)


def require_auth(f):
    """
    Decorator to require authentication for protected endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
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


@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Create a new game session."""
    try:
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
        
        game_id = server.create_new_game(game_mode)
        state = server.get_game_state(game_id)
        
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


@app.route('/api/game/<game_id>/state', methods=['GET'])
def get_state(game_id):
    """Get current game state."""
    try:
        # Log user action
        game_logger.log_user_action(request, 'get_state', game_id)
        
        state = server.get_game_state(game_id)
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


@app.route('/api/game/<game_id>/guess', methods=['POST'])
def make_guess(game_id):
    """Submit a guess for validation and evaluation."""
    try:
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
        is_valid, error = server.is_valid_guess(game_id, guess)
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
        state = server.make_guess(game_id, guess)
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


@app.route('/api/game/<game_id>', methods=['DELETE'])
def delete_game(game_id):
    """Delete a completed game session."""
    try:
        # Log user action
        game_logger.log_user_action(request, 'delete_game', game_id)
        
        success = server.delete_game(game_id)
        
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


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Log user action
        game_logger.log_user_action(request, 'health_check')
        
        # Get log statistics
        log_stats = game_logger.get_log_stats()
        
        response_data = {
            'status': 'healthy',
            'active_games': len(server.games),
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


# Authentication endpoints

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
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


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login a user and return JWT token."""
    try:
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


@app.route('/api/auth/verify', methods=['GET'])
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


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout a user and invalidate their session. Supports both Authorization header and query parameter."""
    try:
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


@app.route('/api/auth/heartbeat', methods=['POST'])
@require_auth
def heartbeat():
    """Update session heartbeat to keep it alive."""
    try:
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
        game_logger.logger.debug(f"💗 Heartbeat: {username}")
        
        # Update session heartbeat
        result = auth_service.update_session_activity(token)
        
        if result['success']:
            return jsonify({'success': True, 'message': 'Heartbeat updated'})
        else:
            game_logger.logger.warning(f"❌ Heartbeat update failed for {username}: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        game_logger.logger.error(f"❌ Heartbeat endpoint error: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return jsonify(error_response), 500


@app.route('/api/auth/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get user profile information."""
    try:
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


# ============================================================================
# MULTIPLAYER / LOBBY FUNCTIONALITY
# ============================================================================

class LobbyManager:
    """
    Manages multiplayer lobby and room functionality.
    Handles real-time room state and player management.
    """
    
    def __init__(self):
        self.rooms = {
            1: {'id': 1, 'name': 'Room 1', 'players': [], 'max_players': 2, 'game_id': None},
            2: {'id': 2, 'name': 'Room 2', 'players': [], 'max_players': 2, 'game_id': None},
            3: {'id': 3, 'name': 'Room 3', 'players': [], 'max_players': 2, 'game_id': None}
        }
        self.user_rooms = {}  # Maps user_id to room_id
        self.lock = threading.Lock()  # Thread safety for concurrent access
    
    def get_lobby_state(self):
        """Get current state of all rooms."""
        with self.lock:
            return {
                'success': True,
                'rooms': list(self.rooms.values())
            }
    
    def join_room(self, user_id, username, room_id):
        """Add user to a room."""
        with self.lock:
            # Check if room exists
            if room_id not in self.rooms:
                return {'success': False, 'error': 'Room not found'}
            
            room = self.rooms[room_id]
            
            # Check if room is full
            if len(room['players']) >= room['max_players']:
                return {'success': False, 'error': 'Room is full'}
            
            # Check if user is already in this room
            if any(player['id'] == user_id for player in room['players']):
                return {'success': False, 'error': 'Already in this room'}
            
            # Remove user from current room if they're in one
            if user_id in self.user_rooms:
                self.leave_room(user_id)
            
            # Add user to room
            player = {'id': user_id, 'username': username}
            room['players'].append(player)
            self.user_rooms[user_id] = room_id
            
            print(f"✅ Added user {username} ({user_id}) to room {room_id}")
            print(f"🔍 Updated user_rooms mapping: {self.user_rooms}")
            
            game_logger.logger.info(f"🏠 Player {username} joined {room['name']} (Room {room_id})")
            
            # Auto-start game if room is now full (2 players)
            if len(room['players']) == 2:
                print(f"🎮 Room {room_id} is full, auto-starting game...")
                # Small delay to let both players see they joined
                def delayed_start():
                    time.sleep(1)  # 1 second delay
                    start_result = self.start_multiplayer_game(user_id, room_id)
                    if start_result['success']:
                        game_id = start_result['game_id']
                        print(f"🎮 HTTP: Auto-started multiplayer game {game_id} in room {room_id}")
                
                # Start game in background thread
                import threading
                start_thread = threading.Thread(target=delayed_start, daemon=True)
                start_thread.start()
            
            return {
                'success': True,
                'room': room,
                'message': f'Joined {room["name"]}',
                'auto_start': len(room['players']) == 2  # Indicate if game will auto-start
            }
    
    def leave_room(self, user_id):
        """Remove user from their current room."""
        with self.lock:
            print(f"🔍 LobbyManager.leave_room called for user_id: {user_id}")
            print(f"🔍 Current user_rooms mapping: {self.user_rooms}")
            
            if user_id not in self.user_rooms:
                print(f"ℹ️ User {user_id} not found in user_rooms mapping")
                return {'success': False, 'error': 'Not in any room'}
            
            room_id = self.user_rooms[user_id]
            room = self.rooms[room_id]
            print(f"🔍 Found user {user_id} in room {room_id}: {room['name']}")
            print(f"🔍 Room players before removal: {[p['username'] for p in room['players']]}")
            
            # Find and remove player
            username = None
            for i, player in enumerate(room['players']):
                if player['id'] == user_id:
                    username = player['username']
                    room['players'].pop(i)
                    break
            
            # Remove from user_rooms mapping
            del self.user_rooms[user_id]
            
            print(f"🔍 Room players after removal: {[p['username'] for p in room['players']]}")
            print(f"🔍 user_rooms after removal: {self.user_rooms}")
            
            game_logger.logger.info(f"🚪 Player {username} left {room['name']} (Room {room_id})")
            print(f"✅ Successfully removed {username} from {room['name']}")
            
            return {
                'success': True,
                'room': room,
                'message': f'Left {room["name"]}'
            }
    
    def get_user_room(self, user_id):
        """Get the room a user is currently in."""
        with self.lock:
            if user_id in self.user_rooms:
                room_id = self.user_rooms[user_id]
                return self.rooms[room_id]
            return None
    
    def reset_all_rooms(self):
        """Reset all rooms to empty state. Used for complete cleanup."""
        with self.lock:
            print("🧹 Resetting all rooms to empty state")
            
            # Clear all players from all rooms
            for room_id, room in self.rooms.items():
                players_count = len(room['players'])
                if players_count > 0:
                    print(f"   Clearing {players_count} players from {room['name']}")
                room['players'] = []
                room['game_id'] = None
            
            # Clear all user-room mappings
            user_count = len(self.user_rooms)
            if user_count > 0:
                print(f"   Clearing {user_count} user-room mappings")
            self.user_rooms.clear()
            
            print("✅ All rooms reset to empty state")
            
            return {
                'success': True,
                'message': 'All rooms have been reset'
            }
    
    def cleanup_room_after_game(self, game_id):
        """Clean up room state after a multiplayer game ends or is abandoned."""
        with self.lock:
            print(f"🧹 Starting cleanup_room_after_game for game_id: {game_id}")
            print(f"🔍 Current rooms state before cleanup:")
            for rid, r in self.rooms.items():
                print(f"   Room {rid} ({r['name']}): {len(r['players'])} players - {[p['username'] for p in r['players']]}")
            print(f"🔍 Current user_rooms mapping: {self.user_rooms}")
            
            for room_id, room in self.rooms.items():
                if room.get('game_id') == game_id:
                    print(f"🎯 Found room {room_id} ({room['name']}) with game_id {game_id}")
                    print(f"🔍 Room players before cleanup: {[p['username'] for p in room['players']]}")
                    
                    # Properly remove each player using the leave_room method
                    # This ensures all state is cleaned up correctly
                    players_to_remove = room['players'].copy()  # Make a copy to avoid modifying while iterating
                    for player in players_to_remove:
                        user_id = player['id']
                        username = player['username']
                        print(f"🚪 Force-removing player {username} ({user_id}) from room")
                        
                        # Use the proper leave_room method to ensure all cleanup
                        try:
                            leave_result = self.leave_room(user_id)
                            print(f"✅ Force leave result for {username}: {leave_result}")
                        except Exception as leave_error:
                            print(f"❌ Error force-leaving {username}: {leave_error}")
                            # Fallback: manually remove from room if leave_room fails
                            if player in room['players']:
                                room['players'].remove(player)
                            if user_id in self.user_rooms:
                                del self.user_rooms[user_id]
                    
                    # Reset room game state
                    room['game_id'] = None
                    # Players should already be cleared by the leave_room calls above
                    
                    print(f"🔍 Final room state - Players: {[p['username'] for p in room['players']]}")
                    print(f"🔍 Final user_rooms mapping: {self.user_rooms}")
                    
                    game_logger.logger.info(f"🧹 Cleaned up {room['name']} after game {game_id} ended")
                    print(f"🧹 Cleaned up {room['name']} after game ended")
                    
                    # Broadcast updated lobby state to all lobby users
                    if 'socketio' in globals():
                        lobby_state = self.get_lobby_state()
                        socketio.emit('lobby_state_update', lobby_state, room="lobby")
                        print(f"📡 Broadcasted lobby state update after room cleanup")
                        print(f"🔍 Updated lobby state after cleanup: {lobby_state}")
                    else:
                        print("⚠️ SocketIO not available for broadcasting lobby state update")
                    
                    break
                    
            print(f"🏁 Finished cleanup_room_after_game for game_id: {game_id}")
    
    def clear_room_players_after_game_start(self, game_id):
        """Clear room players after game starts to prevent lobby issues."""
        with self.lock:
            for room_id, room in self.rooms.items():
                if room.get('game_id') == game_id:
                    # Clear user_rooms mapping for this room (players are now in game)
                    users_to_remove = []
                    for user_id, mapped_room_id in self.user_rooms.items():
                        if mapped_room_id == room_id:
                            users_to_remove.append(user_id)
                    
                    for user_id in users_to_remove:
                        del self.user_rooms[user_id]
                    
                    game_logger.logger.info(f"🎮 Cleared {room['name']} player mappings after game {game_id} started")
                    print(f"🎮 Cleared {room['name']} player mappings after game started")
                    break
    
    def start_multiplayer_game(self, user_id, room_id):
        """Start a multiplayer game from a room."""
        with self.lock:
            if room_id not in self.rooms:
                return {'success': False, 'error': 'Room not found'}
            
            room = self.rooms[room_id]
            
            # Check if user is in this room
            if user_id not in self.user_rooms or self.user_rooms[user_id] != room_id:
                return {'success': False, 'error': 'Not in this room'}
            
            # Check if room has exactly 2 players
            if len(room['players']) != 2:
                return {'success': False, 'error': 'Need exactly 2 players to start'}
            
            # Create multiplayer game
            game_id = server.create_new_game('multiplayer')
            room['game_id'] = game_id
            
            # Add both players to the multiplayer game
            for player in room['players']:
                server.add_player_to_multiplayer_game(game_id, player['id'], player['username'])
            
            game_logger.logger.info(f"🎮 Multiplayer game started in {room['name']} (Game ID: {game_id})")
            
            # Schedule room player cleanup after a delay (5 seconds) to allow both clients to detect game start
            def delayed_cleanup():
                time.sleep(5)
                self.clear_room_players_after_game_start(game_id)
            
            cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
            cleanup_thread.start()
            
            return {
                'success': True,
                'game_id': game_id,
                'room': room,
                'players': room['players']
            }

# Initialize lobby manager
lobby_manager = LobbyManager()

# Lobby API endpoints
@app.route('/api/lobby/state', methods=['GET'])
@require_auth
def get_lobby_state():
    """Get current lobby state with all rooms."""
    try:
        result = lobby_manager.get_lobby_state()
        game_logger.log_server_response(request, 'lobby_state', True, result)
        return jsonify(result)
        
    except Exception as e:
        game_logger.log_error(request, e, 'lobby_state')
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'lobby_state', False, error_response)
        return jsonify(error_response), 500

# HTTP API endpoints for join/leave room removed - using WebSocket only

@app.route('/api/multiplayer/start', methods=['POST'])
@require_auth
def start_multiplayer_game():
    """Start a multiplayer game from a room."""
    try:
        data = request.get_json()
        if not data or 'room_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Room ID is required'
            }), 400
        
        room_id = data['room_id']
        user_id = request.user['id']
        
        # Log user action
        game_logger.log_user_action(request, 'start_multiplayer', extra_data={'room_id': room_id})
        
        result = lobby_manager.start_multiplayer_game(user_id, room_id)
        
        if result['success']:
            game_logger.log_server_response(request, 'start_multiplayer', True, result)
            return jsonify(result)
        else:
            game_logger.log_server_response(request, 'start_multiplayer', False, result)
            return jsonify(result), 400
            
    except Exception as e:
        game_logger.log_error(request, e, 'start_multiplayer')
        error_response = {
            'success': False,
            'error': str(e)
        }
        game_logger.log_server_response(request, 'start_multiplayer', False, error_response)
        return jsonify(error_response), 500

@app.route('/api/multiplayer/<game_id>/state', methods=['GET'])
@require_auth
def get_multiplayer_state(game_id):
    """Get multiplayer game state for current player."""
    try:
        user_id = request.user['id']
        
        # Log user action
        game_logger.log_user_action(request, 'get_multiplayer_state', game_id)
        
        result = server.get_multiplayer_game_state(game_id, user_id)
        
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

@app.route('/api/multiplayer/<game_id>/guess', methods=['POST'])
@require_auth
def make_multiplayer_guess(game_id):
    """Submit a guess in multiplayer game."""
    try:
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
        
        result = server.make_multiplayer_guess(game_id, user_id, guess)
        
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


# ============================================================================
# WEBSOCKET EVENT HANDLERS FOR REAL-TIME MULTIPLAYER
# ============================================================================

# Store connected users and their socket IDs
connected_users = {}  # user_id -> socket_id
user_games = {}       # user_id -> game_id
lobby_users = {}      # user_id -> socket_id (users in lobby)

def websocket_auth_required(f):
    """Decorator to require authentication for WebSocket events."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not auth_service:
            emit('error', {'error': 'Authentication service unavailable'})
            return
        
        # Get token from the event data
        if not args or 'token' not in args[0]:
            emit('error', {'error': 'Authentication token required'})
            return
        
        token = args[0]['token']
        result = auth_service.verify_token(token)
        
        if not result['success']:
            emit('error', {'error': result['error']})
            return
        
        # Add user data to kwargs
        kwargs['user'] = result['user']
        return f(*args, **kwargs)
    
    return decorated_function

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    print(f"🔌 WebSocket client connected: {request.sid}")
    game_logger.logger.info(f"🔌 WebSocket client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    print(f"🔌 WebSocket client disconnected: {request.sid}")
    game_logger.logger.info(f"🔌 WebSocket client disconnected: {request.sid}")
    
    # Find and remove user from connected_users
    user_id_to_remove = None
    for user_id, socket_id in connected_users.items():
        if socket_id == request.sid:
            user_id_to_remove = user_id
            break
    
    if user_id_to_remove:
        print(f"🧹 Cleaning up user {user_id_to_remove} on disconnect")
        
        # Remove from connected_users
        del connected_users[user_id_to_remove]
        
        # Leave any game rooms
        if user_id_to_remove in user_games:
            game_id = user_games[user_id_to_remove]
            leave_room(f"game_{game_id}")
            del user_games[user_id_to_remove]
            print(f"🚪 User {user_id_to_remove} left game room {game_id}")
        
        # Remove from lobby room (WebSocket room)
        if user_id_to_remove in lobby_users:
            leave_room("lobby")
            del lobby_users[user_id_to_remove]
            print(f"🚪 User {user_id_to_remove} left lobby WebSocket room")
        
        # IMPORTANT: Remove user from any multiplayer rooms they're in
        # This ensures rooms are cleaned when users disconnect/go back to menu
        try:
            leave_result = lobby_manager.leave_room(user_id_to_remove)
            if leave_result['success']:
                print(f"✅ Removed user {user_id_to_remove} from multiplayer room: {leave_result['message']}")
            else:
                print(f"ℹ️ User {user_id_to_remove} was not in any multiplayer room")
        except Exception as room_leave_error:
            print(f"❌ Error removing user {user_id_to_remove} from room: {room_leave_error}")
            
        # Broadcast updated lobby state to remaining users
        try:
            lobby_state = lobby_manager.get_lobby_state()
            socketio.emit('lobby_state_update', lobby_state, room="lobby")
            print(f"📡 Broadcasted updated lobby state after disconnect cleanup")
        except Exception as e:
            print(f"❌ Error broadcasting lobby update on disconnect: {e}")

@socketio.on('join_multiplayer_game')
@websocket_auth_required
def handle_join_multiplayer_game(data, user=None):
    """Join a multiplayer game room for real-time updates."""
    try:
        game_id = data.get('game_id')
        if not game_id:
            emit('error', {'error': 'Game ID is required'})
            return
        
        user_id = user['id']
        username = user['username']
        
        # Verify user is part of this game
        game_state = server.get_multiplayer_game_state(game_id, user_id)
        if not game_state:
            emit('error', {'error': 'Game not found or access denied'})
            return
        
        # Join the game room
        join_room(f"game_{game_id}")
        connected_users[user_id] = request.sid
        user_games[user_id] = game_id
        
        print(f"🎮 {username} joined multiplayer game room: {game_id}")
        game_logger.logger.info(f"🎮 WebSocket: {username} joined multiplayer game {game_id}")
        
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
        print(f"❌ Error joining multiplayer game: {e}")
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
        if user_id in user_games:
            del user_games[user_id]
        
        print(f"🚪 {username} left multiplayer game room: {game_id}")
        game_logger.logger.info(f"🚪 WebSocket: {username} left multiplayer game {game_id}")
        
        # Notify other players in the room
        emit('player_left', {
            'user_id': user_id,
            'username': username
        }, room=f"game_{game_id}", include_self=False)
        
    except Exception as e:
        print(f"❌ Error leaving multiplayer game: {e}")
        emit('error', {'error': str(e)})

@socketio.on('join_lobby')
@websocket_auth_required
def handle_join_lobby(data, user=None):
    """Join the lobby for real-time room updates."""
    try:
        user_id = user['id']
        username = user['username']
        
        # Join the lobby room
        join_room("lobby")
        lobby_users[user_id] = request.sid
        connected_users[user_id] = request.sid
        
        print(f"🏠 {username} joined lobby")
        game_logger.logger.info(f"🏠 WebSocket: {username} joined lobby")
        
        # Send current lobby state
        lobby_state = lobby_manager.get_lobby_state()
        emit('lobby_state_update', lobby_state)
        
        # Notify other users in lobby
        emit('user_joined_lobby', {
            'user_id': user_id,
            'username': username
        }, room="lobby", include_self=False)
        
    except Exception as e:
        print(f"❌ Error joining lobby: {e}")
        emit('error', {'error': str(e)})

@socketio.on('leave_lobby')
@websocket_auth_required
def handle_leave_lobby(data, user=None):
    """Leave the lobby."""
    try:
        user_id = user['id']
        username = user['username']
        
        print(f"🧹 {username} leaving lobby - cleaning up all multiplayer state")
        
        # Leave the lobby WebSocket room
        leave_room("lobby")
        
        if user_id in lobby_users:
            del lobby_users[user_id]
        
        # IMPORTANT: Remove user from any multiplayer rooms they're in
        # This ensures clean state when users go back to menu
        try:
            leave_result = lobby_manager.leave_room(user_id)
            if leave_result['success']:
                print(f"✅ Removed {username} from multiplayer room: {leave_result['message']}")
            else:
                print(f"ℹ️ {username} was not in any multiplayer room")
        except Exception as room_leave_error:
            print(f"❌ Error removing {username} from room: {room_leave_error}")
        
        print(f"🚪 {username} left lobby")
        game_logger.logger.info(f"🚪 WebSocket: {username} left lobby")
        
        # Notify other users in lobby
        emit('user_left_lobby', {
            'user_id': user_id,
            'username': username
        }, room="lobby", include_self=False)
        
        # Broadcast updated lobby state to remaining users
        try:
            lobby_state = lobby_manager.get_lobby_state()
            socketio.emit('lobby_state_update', lobby_state, room="lobby")
            print(f"📡 Broadcasted updated lobby state after {username} left")
        except Exception as lobby_error:
            print(f"❌ Error broadcasting lobby update after leave: {lobby_error}")
        
    except Exception as e:
        print(f"❌ Error leaving lobby: {e}")
        emit('error', {'error': str(e)})

@socketio.on('ws_join_room')
@websocket_auth_required
def handle_ws_join_room(data, user=None):
    """Join a multiplayer room via WebSocket."""
    try:
        room_id = data.get('room_id')
        if not room_id:
            emit('error', {'error': 'Room ID is required'})
            return
        
        user_id = user['id']
        username = user['username']
        
        # Use the existing lobby manager to join room
        result = lobby_manager.join_room(user_id, username, room_id)
        
        if result['success']:
            # Broadcast lobby state update to all lobby users
            lobby_state = lobby_manager.get_lobby_state()
            socketio.emit('lobby_state_update', lobby_state, room="lobby")
            
            emit('room_join_result', result)
            print(f"🏠 WebSocket: {username} joined room {room_id}")
            
            # Auto-start game if room is now full (2 players)
            if result['room'] and len(result['room']['players']) == 2:
                print(f"🎮 Room {room_id} is full, auto-starting game...")
                # Small delay to let both players see they joined
                def delayed_start():
                    time.sleep(1)  # 1 second delay
                    start_result = lobby_manager.start_multiplayer_game(user_id, room_id)
                    if start_result['success']:
                        game_id = start_result['game_id']
                        
                        # Notify all players in the room about game start
                        for player in start_result['players']:
                            player_socket_id = connected_users.get(player['id'])
                            if player_socket_id:
                                socketio.emit('game_started', {
                                    'success': True,
                                    'game_id': game_id,
                                    'room': start_result['room'],
                                    'players': start_result['players']
                                }, room=player_socket_id)
                        
                        # Update lobby state for all lobby users
                        updated_lobby_state = lobby_manager.get_lobby_state()
                        socketio.emit('lobby_state_update', updated_lobby_state, room="lobby")
                        
                        print(f"🎮 WebSocket: Auto-started multiplayer game {game_id} in room {room_id}")
                
                # Start game in background thread
                import threading
                start_thread = threading.Thread(target=delayed_start, daemon=True)
                start_thread.start()
            
        else:
            emit('room_join_result', result)
            
    except Exception as e:
        print(f"❌ Error joining room via WebSocket: {e}")
        emit('error', {'error': str(e)})

@socketio.on('ws_leave_room')
@websocket_auth_required
def handle_ws_leave_room(data, user=None):
    """Leave current room via WebSocket."""
    try:
        user_id = user['id']
        username = user['username']
        
        # Use the existing lobby manager to leave room
        print(f"🔍 Attempting to leave room for user {username} ({user_id})")
        result = lobby_manager.leave_room(user_id)
        print(f"🔍 Leave room result: {result}")
        
        # Always broadcast lobby state update (even if user wasn't in a room)
        lobby_state = lobby_manager.get_lobby_state()
        socketio.emit('lobby_state_update', lobby_state, room="lobby")
        
        emit('room_leave_result', result)
        print(f"🚪 WebSocket: {username} left room")
            
    except Exception as e:
        print(f"❌ Error leaving room via WebSocket: {e}")
        emit('error', {'error': str(e)})

@socketio.on('ws_start_multiplayer_game')
@websocket_auth_required
def handle_ws_start_multiplayer_game(data, user=None):
    """Start a multiplayer game via WebSocket."""
    try:
        room_id = data.get('room_id')
        if not room_id:
            emit('error', {'error': 'Room ID is required'})
            return
        
        user_id = user['id']
        username = user['username']
        
        # Use the existing lobby manager to start game
        result = lobby_manager.start_multiplayer_game(user_id, room_id)
        
        if result['success']:
            game_id = result['game_id']
            
            # Notify all players in the room about game start
            for player in result['players']:
                player_socket_id = connected_users.get(player['id'])
                if player_socket_id:
                    socketio.emit('game_started', {
                        'success': True,
                        'game_id': game_id,
                        'room': result['room'],
                        'players': result['players']
                    }, room=player_socket_id)
            
            # Update lobby state for all lobby users
            lobby_state = lobby_manager.get_lobby_state()
            socketio.emit('lobby_state_update', lobby_state, room="lobby")
            
            print(f"🎮 WebSocket: {username} started multiplayer game {game_id}")
        else:
            emit('game_start_result', result)
            
    except Exception as e:
        print(f"❌ Error starting multiplayer game via WebSocket: {e}")
        emit('error', {'error': str(e)})

@socketio.on('ws_reset_all_rooms')
@websocket_auth_required
def handle_ws_reset_all_rooms(data, user=None):
    """Reset all rooms to empty state. For debugging/cleanup purposes."""
    try:
        username = user['username']
        print(f"🧹 {username} requested to reset all rooms")
        
        # Reset all rooms
        result = lobby_manager.reset_all_rooms()
        
        # Broadcast updated lobby state to all lobby users
        lobby_state = lobby_manager.get_lobby_state()
        socketio.emit('lobby_state_update', lobby_state, room="lobby")
        
        emit('room_reset_result', result)
        print(f"✅ All rooms reset by {username}")
        
    except Exception as e:
        print(f"❌ Error resetting all rooms: {e}")
        emit('error', {'error': str(e)})

@socketio.on('ws_submit_guess')
@websocket_auth_required
def handle_ws_submit_guess(data, user=None):
    """Submit a guess via WebSocket."""
    try:
        game_id = data.get('game_id')
        guess = data.get('guess')
        
        if not game_id or not guess:
            emit('error', {'error': 'Game ID and guess are required'})
            return
        
        user_id = user['id']
        username = user['username']
        
        # Log the multiplayer guess attempt
        game_logger.log_game_event(
            game_id, 
            'multiplayer_guess_attempt', 
            user_id,
            username=username,
            guess=guess,
            guess_length=len(guess),
            method='websocket'
        )
        
        # Process the guess using existing server logic
        result = server.make_multiplayer_guess(game_id, user_id, guess)
        
        if result:
            if "error" in result:
                # Log failed guess
                game_logger.log_game_event(
                    game_id, 
                    'multiplayer_guess_failed', 
                    user_id,
                    username=username,
                    guess=guess,
                    error=result["error"],
                    method='websocket'
                )
                
                emit('guess_result', {
                    'success': False,
                    'error': result["error"]
                })
            else:
                # Log successful guess
                game_logger.log_game_event(
                    game_id, 
                    'multiplayer_guess_success', 
                    user_id,
                    username=username,
                    guess=guess,
                    won=result.get('player_state', {}).get('won', False),
                    finished=result.get('player_state', {}).get('finished', False),
                    game_over=result.get('game_over', False),
                    winner=result.get('winner'),
                    game_status=result.get('game_status', 'active')
                )
                
                # Send result to the player who made the guess
                emit('guess_result', {
                    'success': True,
                    'result': result
                })
                
                # Explicitly broadcast game state update to all players
                broadcast_game_state_update(game_id)
                
                # If game ended, clean up the room AFTER broadcasting
                if result.get('game_over', False):
                    print(f"🏁 Game ended, cleaning up room for game {game_id}")
                    if lobby_manager:
                        lobby_manager.cleanup_room_after_game(game_id)
                
                print(f"🎯 WebSocket: {username} submitted guess '{guess}' in game {game_id}")
        else:
            # Log invalid guess
            game_logger.log_game_event(
                game_id, 
                'multiplayer_guess_invalid', 
                user_id,
                username=username,
                guess=guess,
                error='Invalid guess or game not found',
                method='websocket'
            )
            
            emit('guess_result', {
                'success': False,
                'error': 'Invalid guess or game not found'
            })
            
    except Exception as e:
        print(f"❌ Error submitting guess via WebSocket: {e}")
        emit('error', {'error': str(e)})

def broadcast_game_state_update(game_id):
    """Broadcast game state update to all players in a game."""
    try:
        game_data = server.games.get(game_id)
        if not game_data or game_data.get("game_mode") != "multiplayer":
            return
        
        # Send updated state to each player individually
        for player in game_data.get("players", []):
            user_id = player["id"]
            game_state = server.get_multiplayer_game_state(game_id, user_id)
            
            if game_state and user_id in connected_users:
                player_socket_id = connected_users[user_id]
                socketio.emit('game_state_update', {
                    'success': True,
                    'state': game_state
                }, room=player_socket_id)
        
        print(f"📡 Broadcasted game state update for game {game_id}")
        
    except Exception as e:
        print(f"❌ Error broadcasting game state: {e}")
        game_logger.logger.error(f"❌ Error broadcasting game state for {game_id}: {e}")

def broadcast_game_end(game_id, winner_id=None, game_status="finished"):
    """Broadcast game end event to all players in a game."""
    try:
        game_data = server.games.get(game_id)
        if not game_data:
            print(f"⚠️ Cannot broadcast game end - game {game_id} not found")
            return
        
        print(f"🏁 Broadcasting game end for game {game_id}, winner: {winner_id}, status: {game_status}")
        
        # Get the target word for the broadcast
        target_word = game_data.get("target_word")
        print(f"🏁 Target word for broadcast: {target_word}")
        
        # Broadcast to game room
        room_name = f"game_{game_id}"
        print(f"🏁 Broadcasting to room: {room_name}")
        
        socketio.emit('game_ended', {
            'game_id': game_id,
            'winner_id': winner_id,
            'game_status': game_status,
            'target_word': target_word
        }, room=room_name)
        
        # Also broadcast directly to connected players as a fallback
        players = game_data.get("players", [])
        print(f"🏁 Also broadcasting directly to {len(players)} players")
        
        for player in players:
            user_id = player["id"]
            if user_id in connected_users:
                player_socket_id = connected_users[user_id]
                socketio.emit('game_ended', {
                    'game_id': game_id,
                    'winner_id': winner_id,
                    'game_status': game_status,
                    'target_word': target_word
                }, room=player_socket_id)
                print(f"🏁 Sent game end to player {player['username']} ({user_id})")
        
        print(f"🏁 Completed broadcasting game end for game {game_id}")
        
        # Log the game end event
        game_logger.log_game_event(
            game_id, 
            'multiplayer_game_ended', 
            winner_id or 'system',
            winner_id=winner_id,
            game_status=game_status,
            target_word=target_word,
            players=[p['username'] for p in players]
        )
        
    except Exception as e:
        print(f"❌ Error broadcasting game end: {e}")
        game_logger.logger.error(f"❌ Error broadcasting game end for {game_id}: {e}")


if __name__ == '__main__':
    print("Starting Wordle Server...")
    print("API endpoints:")
    print("  POST /api/new_game - Create new game")
    print("  GET /api/game/<id>/state - Get game state") 
    print("  POST /api/game/<id>/guess - Submit guess")
    print("  DELETE /api/game/<id> - Delete game")
    print("  GET /api/health - Health check")
    print("Authentication endpoints:")
    print("  POST /api/auth/register - Register new user")
    print("  POST /api/auth/login - Login user")
    print("  GET /api/auth/verify - Verify JWT token")
    print("  GET /api/auth/profile - Get user profile")
    print("  POST /api/auth/heartbeat - Send heartbeat to keep session alive")
    print("Multiplayer/Lobby endpoints:")
    print("  GET /api/lobby/state - Get lobby state")
    print("  POST /api/lobby/join - Join a room")
    print("  POST /api/lobby/leave - Leave current room")
    print("  POST /api/multiplayer/start - Start multiplayer game")
    print("  GET /api/multiplayer/<id>/state - Get multiplayer game state")
    print("  POST /api/multiplayer/<id>/guess - Submit multiplayer guess")
    print(f"Logging enabled - logs will be saved to: logs/")
    
    # Start heartbeat cleanup worker in background thread
    if auth_service:
        cleanup_thread = threading.Thread(target=heartbeat_cleanup_worker, daemon=True)
        cleanup_thread.start()
        print("💗 Heartbeat cleanup worker started - checking every 15 seconds")
    
    # Log server startup
    game_logger.logger.info("🚀 Wordle Server Starting - Comprehensive logging, authentication, and heartbeat monitoring enabled")
    
    socketio.run(app, host=HOST, port=PORT, debug=DEBUG)
