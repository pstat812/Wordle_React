"""
Helper Functions

Contains utility functions used throughout the application.
"""

from typing import Dict
from flask import request


def get_user_identity(request_obj=None) -> Dict[str, str]:
    """Extract user identity information from request."""
    if request_obj is None:
        request_obj = request
        
    user_ip = request_obj.remote_addr or 'unknown'
    
    return {
        'user_ip': user_ip,
        'session_id': None,  # Future: session tracking
        'username': None     # Future: actual usernames
    }
