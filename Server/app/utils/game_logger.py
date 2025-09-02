"""
Game Logger Module for Wordle Server

This module provides comprehensive logging for user actions, server responses,
and game events. Designed with future multiplayer support in mind.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class GameLogger:
    """
    Centralized logging system for Wordle game server.
    
    Features:
    - User action tracking with IP/user identification
    - Server response logging
    - Game event logging
    - JSON structured logs for easy parsing
    - Future-ready for multiplayer features
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup main game logger
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup the main game logger with file handler."""
        logger = logging.getLogger('wordle_game')
        logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if logger.handlers:
            logger.handlers.clear()
        
        # Create log file with date
        log_file = self.log_dir / f"game_log_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler for only important messages (WARNING and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only show warnings/errors in console
        
        # JSON formatter for structured logging (file only)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Simple formatter for console (if any warnings/errors)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _get_user_identity(self, request) -> Dict[str, str]:
        """Extract user identity information from request."""
        user_ip = request.remote_addr or 'unknown'
        
        # Future: This can be extended to include username, user_id, etc.
        return {
            'user_ip': user_ip,
            'session_id': None,  # Future: session tracking
            'username': None     # Future: actual usernames
        }
    
    def _create_log_entry(self, 
                         event_type: str, 
                         action: str, 
                         user_info: Dict[str, str],
                         details: Dict[str, Any]) -> str:
        """Create a structured log entry."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'action': action,
            'user': user_info,
            'details': details
        }
        return json.dumps(log_entry, ensure_ascii=False)
    
    def log_user_action(self, 
                       request, 
                       action: str, 
                       game_id: Optional[str] = None,
                       **kwargs):
        """
        Log user actions with full context.
        
        Args:
            request: Flask request object
            action: Type of action (e.g., 'new_game', 'submit_guess', 'get_state')
            game_id: Game identifier if applicable
            **kwargs: Additional details to log
        """
        user_info = self._get_user_identity(request)
        
        details = {
            'game_id': game_id,
            'endpoint': request.endpoint,
            'method': request.method,
            'url': request.url,
            **kwargs
        }
        
        log_message = self._create_log_entry('USER_ACTION', action, user_info, details)
        self.logger.info(log_message)
    
    def log_server_response(self, 
                           request, 
                           action: str,
                           success: bool,
                           response_data: Dict[str, Any],
                           game_id: Optional[str] = None,
                           **kwargs):
        """
        Log server responses with full context.
        
        Args:
            request: Flask request object
            action: Action that was performed
            success: Whether the action succeeded
            response_data: Data being returned to client
            game_id: Game identifier if applicable
            **kwargs: Additional details to log
        """
        user_info = self._get_user_identity(request)
        
        # Sanitize response data (remove sensitive info if any)
        safe_response = self._sanitize_response_data(response_data)
        
        details = {
            'game_id': game_id,
            'success': success,
            'response_size': len(str(response_data)),
            'response_data': safe_response,
            **kwargs
        }
        
        event_type = 'SERVER_RESPONSE_SUCCESS' if success else 'SERVER_RESPONSE_ERROR'
        log_message = self._create_log_entry(event_type, action, user_info, details)
        
        if success:
            self.logger.info(log_message)
        else:
            self.logger.error(log_message)
    
    def log_game_event(self, 
                      game_id: str,
                      event: str,
                      user_ip: str,
                      **kwargs):
        """
        Log game-specific events (wins, losses, etc.).
        
        Args:
            game_id: Game identifier
            event: Type of game event (e.g., 'game_won', 'game_lost', 'word_revealed')
            user_ip: User's IP address
            **kwargs: Additional game details
        """
        user_info = {'user_ip': user_ip, 'session_id': None, 'username': None}
        
        details = {
            'game_id': game_id,
            **kwargs
        }
        
        log_message = self._create_log_entry('GAME_EVENT', event, user_info, details)
        self.logger.info(log_message)
    
    def log_error(self, 
                 request, 
                 error: Exception,
                 action: str,
                 game_id: Optional[str] = None):
        """
        Log errors with full context.
        
        Args:
            request: Flask request object
            error: Exception that occurred
            action: Action that was being performed
            game_id: Game identifier if applicable
        """
        user_info = self._get_user_identity(request)
        
        details = {
            'game_id': game_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'action': action
        }
        
        log_message = self._create_log_entry('ERROR', action, user_info, details)
        self.logger.error(log_message)
    
    def _sanitize_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive data from response logs."""
        if not isinstance(data, dict):
            return {'data_type': type(data).__name__}
        
        # Create a copy to avoid modifying original
        sanitized = data.copy()
        
        # Future: Remove sensitive fields like passwords, tokens, etc.
        # For now, just limit the size of large data structures
        if 'state' in sanitized and isinstance(sanitized['state'], dict):
            # Keep essential game state info but limit verbosity
            state = sanitized['state']
            sanitized['state'] = {
                'current_round': state.get('current_round'),
                'max_rounds': state.get('max_rounds'),
                'game_over': state.get('game_over'),
                'won': state.get('won'),
                'guesses_count': len(state.get('guesses', [])),
                'answer_revealed': state.get('answer') is not None
            }
        
        return sanitized
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about logged events (useful for monitoring)."""
        try:
            log_file = self.log_dir / f"game_log_{datetime.now().strftime('%Y-%m-%d')}.log"
            if not log_file.exists():
                return {'error': 'No log file found for today'}
            
            stats = {
                'log_file': str(log_file),
                'file_size_mb': round(log_file.stat().st_size / (1024 * 1024), 2),
                'total_entries': 0,
                'user_actions': 0,
                'server_responses': 0,
                'game_events': 0,
                'errors': 0
            }
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        stats['total_entries'] += 1
                        if 'USER_ACTION' in line:
                            stats['user_actions'] += 1
                        elif 'SERVER_RESPONSE' in line:
                            stats['server_responses'] += 1
                        elif 'GAME_EVENT' in line:
                            stats['game_events'] += 1
                        elif 'ERROR' in line:
                            stats['errors'] += 1
            
            return stats
            
        except Exception as e:
            return {'error': f'Failed to get stats: {str(e)}'}


# Global logger instance
game_logger = GameLogger()
