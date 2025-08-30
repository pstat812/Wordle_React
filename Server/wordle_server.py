"""
Wordle Game Server - Server-side Game Logic and API

This module implements the server-side game engine for the client-server Wordle architecture.
The server manages game state, word selection, and validation while keeping the answer
secure from the client until game completion.

"""

import random
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, request, jsonify
from flask_cors import CORS
from game_settings import WORD_LIST, MAX_ROUNDS
from game_logger import game_logger


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
            "target_word": target_word if game_mode == "wordle" else None,
            "current_round": 0,
            "max_rounds": max_rounds if game_mode == "wordle" else 1,  # Start with 1 for Absurdle
            "game_over": False,
            "won": False,
            "guesses": [],
            "guess_results": [],
            "letter_status": {letter: LetterStatus.UNUSED.value for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
            "game_mode": game_mode,
            "candidate_words": self.word_list.copy() if game_mode == "absurdle" else []
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
        
        # Generate all possible patterns for this guess
        all_patterns = self._generate_all_patterns(guess)
        
        # Group candidate words by pattern
        pattern_groups = {}
        
        for pattern in all_patterns:
            pattern_key = self._pattern_to_key(pattern)
            pattern_groups[pattern_key] = {
                'pattern': pattern,
                'words': []
            }
            
            # Find all candidate words that would produce this pattern
            for word in candidate_words:
                if self._is_pattern_consistent(guess, pattern, word):
                    pattern_groups[pattern_key]['words'].append(word)
        
        # Remove empty groups
        valid_groups = [group for group in pattern_groups.values() if group['words']]
        
        if not valid_groups:
            # Fallback - shouldn't happen
            return [(letter, LetterStatus.MISS) for letter in guess]
        
        # Find the group with maximum words (worst case for player)
        chosen_group = valid_groups[0]
        for group in valid_groups:
            if len(group['words']) > len(chosen_group['words']):
                chosen_group = group
            elif len(group['words']) == len(chosen_group['words']):
                # Tie-breaker: choose lexicographically first pattern
                if self._pattern_to_key(group['pattern']) < self._pattern_to_key(chosen_group['pattern']):
                    chosen_group = group
        
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


# Flask REST API setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
server = WordleServer()


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
            'log_stats': log_stats
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


if __name__ == '__main__':
    print("Starting Wordle Server...")
    print("API endpoints:")
    print("  POST /api/new_game - Create new game")
    print("  GET /api/game/<id>/state - Get game state") 
    print("  POST /api/game/<id>/guess - Submit guess")
    print("  DELETE /api/game/<id> - Delete game")
    print("  GET /api/health - Health check")
    print(f"Logging enabled - logs will be saved to: logs/")
    
    # Log server startup
    game_logger.logger.info("🚀 Wordle Server Starting - Comprehensive logging enabled")
    
    app.run(host='127.0.0.1', port=5000, debug=False)
