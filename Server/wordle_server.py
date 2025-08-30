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
    
    def create_new_game(self) -> str:
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
            "target_word": target_word,
            "current_round": 0,
            "max_rounds": max_rounds,
            "game_over": False,
            "won": False,
            "guesses": [],
            "guess_results": [],
            "letter_status": {letter: LetterStatus.UNUSED.value for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
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
        answer = game["target_word"] if game["game_over"] else None
        
        return GameState(
            game_id=game_id,
            current_round=game["current_round"],
            max_rounds=game["max_rounds"],
            game_over=game["game_over"],
            won=game["won"],
            guesses=game["guesses"].copy(),
            guess_results=game["guess_results"].copy(),
            letter_status=game["letter_status"].copy(),
            answer=answer
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
        target_word = game["target_word"]
        
        # Evaluate guess using the same algorithm as the original game
        evaluations = self._evaluate_guess_against_target(normalized_guess, target_word)
        
        # Update game state
        game["current_round"] += 1
        game["guesses"].append(normalized_guess)
        game["guess_results"].append([(letter, status.value) for letter, status in evaluations])
        
        # Update letter status
        self._update_letter_status(game["letter_status"], evaluations)
        
        # Check win condition
        if normalized_guess == target_word:
            game["won"] = True
            game["game_over"] = True
        
        # Check loss condition
        elif game["current_round"] >= game["max_rounds"]:
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
        game_id = server.create_new_game()
        state = server.get_game_state(game_id)
        return jsonify({
            'success': True,
            'game_id': game_id,
            'state': asdict(state)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/game/<game_id>/state', methods=['GET'])
def get_state(game_id):
    """Get current game state."""
    state = server.get_game_state(game_id)
    if state is None:
        return jsonify({
            'success': False,
            'error': 'Game not found'
        }), 404
    
    return jsonify({
        'success': True,
        'state': asdict(state)
    })


@app.route('/api/game/<game_id>/guess', methods=['POST'])
def make_guess(game_id):
    """Submit a guess for validation and evaluation."""
    data = request.get_json()
    if not data or 'guess' not in data:
        return jsonify({
            'success': False,
            'error': 'Guess is required'
        }), 400
    
    guess = data['guess']
    
    # Validate guess first
    is_valid, error = server.is_valid_guess(game_id, guess)
    if not is_valid:
        return jsonify({
            'success': False,
            'error': error
        }), 400
    
    # Process guess
    state = server.make_guess(game_id, guess)
    if state is None:
        return jsonify({
            'success': False,
            'error': 'Failed to process guess'
        }), 500
    
    return jsonify({
        'success': True,
        'state': asdict(state)
    })


@app.route('/api/game/<game_id>', methods=['DELETE'])
def delete_game(game_id):
    """Delete a completed game session."""
    success = server.delete_game(game_id)
    return jsonify({
        'success': success
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'active_games': len(server.games)
    })


if __name__ == '__main__':
    print("Starting Wordle Server...")
    print("API endpoints:")
    print("  POST /api/new_game - Create new game")
    print("  GET /api/game/<id>/state - Get game state") 
    print("  POST /api/game/<id>/guess - Submit guess")
    print("  DELETE /api/game/<id> - Delete game")
    print("  GET /api/health - Health check")
    
    app.run(host='127.0.0.1', port=5000, debug=False)
