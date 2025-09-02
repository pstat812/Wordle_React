"""
Game Service

Contains the core game logic for Wordle, Absurdle, and multiplayer games.
"""

import random
import uuid
import time
from typing import Dict, List, Optional, Tuple
from ..models.game import GameState, LetterStatus
from ..config.game_settings import WORD_LIST, MAX_ROUNDS


class GameService:
    """
    Core game service managing multiple game sessions.
    
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
        
        Args:
            game_mode: Type of game ("wordle", "absurdle", "multiplayer")
            
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

        # Check if this is a spell cast
        spells = ["FLASH", "WRONG", "BLOCK"]
        if normalized_guess in spells:
            # Validate spell usage for multiplayer games
            if game["game_mode"] == "multiplayer":
                return True, ""
            else:
                return False, "Spells are only available in multiplayer mode"

        # Normal word validation
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

        # Check if this is a spell cast
        spells = ["FLASH", "WRONG", "BLOCK"]
        if normalized_guess in spells:
            # Handle spell casting - don't count as a regular guess
            return self.get_game_state(game_id)

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

    def _pattern_to_key(self, pattern: List[Tuple[str, LetterStatus]]) -> str:
        """
        Convert a pattern to a string key for comparison.
        """
        return ''.join([f"{letter}:{status.value}" for letter, status in pattern])

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

        # Check if this is a spell cast
        spells = ["FLASH", "WRONG", "BLOCK"]
        if guess in spells:
            # Handle spell casting - return spell cast information
            return {
                "spell_cast": True,
                "spell": guess,
                "caster_id": user_id,
                "player_state": player_state,
                "game_status": game_data["game_status"],
                "game_over": game_data["game_over"]
            }

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

    def handle_player_disconnect(self, user_id: str, username: str) -> Dict:
        """
        Handle player disconnection from active multiplayer games.
        When a player disconnects, they automatically forfeit any active multiplayer games.
        
        Args:
            user_id: ID of the disconnected player
            username: Username of the disconnected player (for logging)
            
        Returns:
            Dictionary with count of games affected and list of affected game IDs
        """
        games_affected = 0
        affected_game_ids = []
        
        # Find all multiplayer games where this user is a player
        for game_id, game_data in self.games.items():
            if (game_data.get("game_mode") == "multiplayer" and 
                user_id in game_data.get("player_states", {})):
                
                # Check if game is still active
                if game_data.get("game_status") == "active" and not game_data.get("game_over"):
                    games_affected += 1
                    affected_game_ids.append(game_id)
                    
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
                    
                    print(f"Game {game_id}: {username} forfeited due to disconnect")
        
        return {
            "games_affected": games_affected,
            "affected_game_ids": affected_game_ids
        }

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


# Global service instance
_game_service = None


def get_game_service() -> Optional[GameService]:
    """Get the global game service instance."""
    return _game_service


def initialize_game_service() -> GameService:
    """Initialize the global game service instance."""
    global _game_service
    _game_service = GameService()
    return _game_service