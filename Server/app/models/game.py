"""
Game Data Models

Contains all game-related data structures and enums.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


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


@dataclass
class MultiplayerGameState:
    """Multiplayer game state representation."""
    game_id: str
    game_mode: str
    game_status: str  # "active", "finished", "draw"
    winner: Optional[str]
    game_over: bool
    target_word: Optional[str]
    max_rounds: int
    player: Dict
    opponent: Optional[Dict]
    players: List[Dict]
