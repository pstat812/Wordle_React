"""
User Data Models

Contains user-related data structures.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime


@dataclass
class User:
    """User data model."""
    id: str
    username: str
    stats: Dict
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


@dataclass
class UserStats:
    """User statistics data model."""
    games_played: int = 0
    games_won: int = 0
    total_guesses: int = 0
    average_guesses: float = 0.0
