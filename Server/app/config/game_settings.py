"""
Game Configuration Constants Module

This module defines all game configuration constants following the
Single Responsibility Principle and Configuration Management best practices.
All game parameters are centralized here to enable easy modification

"""

import json
import os
from typing import List, Final

# Core Game Configuration Constants (only for single player game)
MAX_ROUNDS: Final[int] = 6
"""
Maximum number of guess attempts allowed per game.
Type: Final[int] - Immutable to prevent accidental modification
"""

# Load word list from JSON file
def _load_word_list() -> List[str]:
    """
    Load word list from wordles.json file.
    
    Returns:
        List[str]: List of uppercase 5-letter words
        
    Raises:
        FileNotFoundError: If wordles.json file is not found
        json.JSONDecodeError: If JSON file is malformed
        ValueError: If word list is empty or contains invalid words
    """
    config_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(config_dir, 'wordles.json')
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            word_list = json.load(f)
            
        if not isinstance(word_list, list):
            raise ValueError("JSON file must contain an array of words")
            
        if not word_list:
            raise ValueError("Word list cannot be empty")
            
        # Convert all words to uppercase and validate
        uppercase_words = [word.upper() for word in word_list]
        
        # Validate word format
        for word in uppercase_words:
            if len(word) != 5:
                raise ValueError(f"Word '{word}' is not 5 characters long")
            if not word.isalpha():
                raise ValueError(f"Word '{word}' contains non-alphabetic characters")
                
        return uppercase_words
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Word list file not found: {json_file_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in wordles.json: {e}")

# Curated Word Database loaded from JSON file
WORD_LIST: Final[List[str]] = _load_word_list()


def validate_word_list_integrity() -> bool:
    """
    Validates the integrity and consistency of the word database.
    
    This function performs validation to ensure:
    1. Length validation: All words must be exactly 5 characters
    2. Character validation: Only alphabetic characters allowed
    3. Uniqueness validation: No duplicate entries
    4. Format validation: Consistent uppercase formatting
    
    Returns:
        bool: True if word list passes all validation checks
        
    Raises:
        ValueError: If any validation check fails with detailed error message
        
    """
    if not WORD_LIST:
        raise ValueError("Word list cannot be empty")
    
    # Validate each word meets game requirements
    for index, word in enumerate(WORD_LIST):
        if len(word) != 5:
            raise ValueError(f"Word at index {index} '{word}' is not 5 characters long")
        
        if not word.isalpha():
            raise ValueError(f"Word at index {index} '{word}' contains non-alphabetic characters")
        
        if not word.isupper():
            raise ValueError(f"Word at index {index} '{word}' is not in uppercase format")
    
    # Validate uniqueness (no duplicates)
    if len(WORD_LIST) != len(set(WORD_LIST)):
        duplicates = [word for word in WORD_LIST if WORD_LIST.count(word) > 1]
        raise ValueError(f"Duplicate words found in word list: {duplicates}")
    
    return True


def get_word_statistics() -> dict:
    """
    Analyzes word list and returns statistical information for game balancing.
    
    Returns:
        dict: Statistical analysis including:
            - total_words: Number of words in database
            - avg_vowel_count: Average vowels per word
            - letter_frequency: Distribution of letters across all words
            - pattern_analysis: Common letter patterns and positions
    
    """
    if not WORD_LIST:
        return {"error": "Word list is empty"}
    
    vowels = set('AEIOU')
    total_vowels = sum(len([char for char in word if char in vowels]) for word in WORD_LIST)
    
    # Calculate letter frequency distribution
    letter_frequency = {}
    for word in WORD_LIST:
        for char in word:
            letter_frequency[char] = letter_frequency.get(char, 0) + 1
    
    return {
        "total_words": len(WORD_LIST),
        "avg_vowel_count": round(total_vowels / len(WORD_LIST), 2),
        "letter_frequency": letter_frequency,
        "most_common_letters": sorted(letter_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
    }


# Module initialization: Validate configuration on import
if __name__ == "__main__":

    try:
        validate_word_list_integrity()
        print(" Word list validation passed")
        
        stats = get_word_statistics()
        print(f" Game statistics: {stats}")
        
        print(" All configuration validation checks passed")
    except ValueError as config_error:
        print(f" Configuration validation failed: {config_error}")
        exit(1)