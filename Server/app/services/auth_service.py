"""
Authentication Service

Handles user authentication including registration, login,
password hashing, and JWT token management using MongoDB for data storage.
"""

import bcrypt
import jwt
import datetime
import hashlib
from typing import Optional, Dict, Any
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
from flask import current_app


class AuthService:
    """
    Authentication service for handling user registration, login, and token management.
    """
    
    def __init__(self, mongo_uri: str, jwt_secret: str):
        """
        Initialize the authentication service with MongoDB connection.
        
        Args:
            mongo_uri: MongoDB connection string
            jwt_secret: Secret key for JWT token generation
        """
        self.mongo_uri = mongo_uri
        self.jwt_secret = jwt_secret
        
        # Create MongoDB client
        self.client = MongoClient(mongo_uri, server_api=ServerApi('1'))
        self.db = self.client.wordle_game
        self.users_collection = self.db.users
        self.sessions_collection = self.db.active_sessions
        
        # Test connection
        try:
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB!")
        except Exception as e:
            print(f"MongoDB connection error: {e}")
            raise
        
        # Create unique index on username
        self.users_collection.create_index("username", unique=True)
        
        # Create indexes for sessions collection
        self.sessions_collection.create_index("user_id", unique=True)  # One session per user
        self.sessions_collection.create_index("token_hash")
        self.sessions_collection.create_index("expires_at", expireAfterSeconds=0)  # TTL index
        self.sessions_collection.create_index("last_activity")  # For activity queries
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password as string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password
            hashed_password: Stored hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def _hash_token(self, token: str) -> str:
        """
        Create a hash of the token for storage (for session tracking).
        
        Args:
            token: JWT token string
            
        Returns:
            SHA256 hash of the token
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    def _create_session(self, user_id: str, token: str) -> bool:
        """
        Create an active session record.
        
        Args:
            user_id: User's unique identifier
            token: JWT token
            
        Returns:
            True if session created successfully
        """
        try:
            now = datetime.datetime.utcnow()
            session_doc = {
                "user_id": user_id,
                "token_hash": self._hash_token(token),
                "created_at": now,
                "last_activity": now,
                "last_heartbeat": now,  # Track when user last sent heartbeat
                "expires_at": now + datetime.timedelta(seconds=current_app.config.get('SESSION_TIMEOUT_SECONDS', 10))
            }
            
            # Use upsert to replace any existing session for this user
            self.sessions_collection.replace_one(
                {"user_id": user_id},
                session_doc,
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    def _is_user_logged_in(self, user_id: str) -> bool:
        """
        Check if a user already has an active session.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            True if user has an active session
        """
        try:
            session = self.sessions_collection.find_one({
                "user_id": user_id,
                "expires_at": {"$gt": datetime.datetime.utcnow()}
            })
            return session is not None
            
        except Exception:
            return False
    
    def _remove_session(self, user_id: str) -> bool:
        """
        Remove an active session.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            True if session removed successfully
        """
        try:
            result = self.sessions_collection.delete_one({"user_id": user_id})
            return result.deleted_count > 0
            
        except Exception as e:
            print(f"Error removing session: {e}")
            return False
    
    def register_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            username: User's chosen username
            password: User's chosen password
            
        Returns:
            Dictionary with success status and message or error
        """
        try:
            # Validate input
            if not username or not password:
                return {"success": False, "error": "Username and password are required"}
            
            if len(username.strip()) < 3:
                return {"success": False, "error": "Username must be at least 3 characters long"}
            
            if len(password) < 6:
                return {"success": False, "error": "Password must be at least 6 characters long"}
            
            username = username.strip().lower()  # Normalize username
            
            # Check if user already exists
            if self.users_collection.find_one({"username": username}):
                return {"success": False, "error": "Username already exists"}
            
            # Hash password
            hashed_password = self.hash_password(password)
            
            # Create user document
            user_doc = {
                "username": username,
                "password": hashed_password,
                "created_at": datetime.datetime.utcnow(),
                "last_login": None,
                "stats": {
                    "games_played": 0,
                    "games_won": 0,
                    "total_guesses": 0,
                    "average_guesses": 0.0
                }
            }
            
            # Insert user
            result = self.users_collection.insert_one(user_doc)
            
            return {
                "success": True,
                "message": "User registered successfully",
                "user_id": str(result.inserted_id)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Registration failed: {str(e)}"}
    
    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user and generate JWT token.
        Prevents duplicate logins for the same account.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Dictionary with success status and JWT token or error
        """
        try:
            # Validate input
            if not username or not password:
                return {"success": False, "error": "Username and password are required"}
            
            username = username.strip().lower()  # Normalize username
            
            # Find user
            user = self.users_collection.find_one({"username": username})
            if not user:
                return {"success": False, "error": "Invalid username or password"}
            
            # Verify password
            if not self.verify_password(password, user["password"]):
                return {"success": False, "error": "Invalid username or password"}
            
            user_id = str(user["_id"])
            
            # Check if user is already logged in
            if self._is_user_logged_in(user_id):
                return {
                    "success": False, 
                    "error": "This account is already logged in from another session. Please log out from the other session first."
                }
            
            # Update last login
            self.users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.datetime.utcnow()}}
            )
            
            # Generate JWT token
            token_payload = {
                "user_id": user_id,
                "username": user["username"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=current_app.config.get('JWT_EXPIRATION_DAYS', 7))
            }
            
            token = jwt.encode(token_payload, self.jwt_secret, algorithm="HS256")
            
            # Create session record
            if not self._create_session(user_id, token):
                return {"success": False, "error": "Failed to create session"}
            
            return {
                "success": True,
                "token": token,
                "user": {
                    "id": user_id,
                    "username": user["username"],
                    "stats": user.get("stats", {})
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Login failed: {str(e)}"}
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token and check if session is still active.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with success status and user data or error
        """
        try:
            if not token:
                return {"success": False, "error": "Token is required"}
            
            # Decode token
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if not user_id:
                return {"success": False, "error": "Invalid token payload"}
            
            # Check if session is still active and heartbeat is recent
            token_hash = self._hash_token(token)
            now = datetime.datetime.utcnow()
            heartbeat_cutoff = now - datetime.timedelta(seconds=current_app.config.get('SESSION_TIMEOUT_SECONDS', 10))
            
            session = self.sessions_collection.find_one({
                "user_id": user_id,
                "token_hash": token_hash,
                "expires_at": {"$gt": now},
                "last_heartbeat": {"$gt": heartbeat_cutoff}  # Check heartbeat freshness
            })
            
            if not session:
                return {"success": False, "error": "Session has expired or is invalid"}
            
            # Get user from database
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {"success": False, "error": "User not found"}
            
            return {
                "success": True,
                "user": {
                    "id": str(user["_id"]),
                    "username": user["username"],
                    "stats": user.get("stats", {})
                }
            }
            
        except jwt.ExpiredSignatureError:
            return {"success": False, "error": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"success": False, "error": "Invalid token"}
        except Exception as e:
            return {"success": False, "error": f"Token verification failed: {str(e)}"}
    
    def logout_user(self, token: str) -> Dict[str, Any]:
        """
        Logout a user by removing their active session.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with success status
        """
        try:
            if not token:
                return {"success": False, "error": "Token is required"}
            
            # Decode token to get user_id
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if not user_id:
                return {"success": False, "error": "Invalid token payload"}
            
            # Remove session
            if self._remove_session(user_id):
                return {"success": True, "message": "Logged out successfully"}
            else:
                return {"success": False, "error": "Session not found or already expired"}
            
        except jwt.ExpiredSignatureError:
            return {"success": False, "error": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"success": False, "error": "Invalid token"}
        except Exception as e:
            return {"success": False, "error": f"Logout failed: {str(e)}"}
    
    def update_session_activity(self, token: str) -> Dict[str, Any]:
        """
        Update the last activity time for a session to keep it alive.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with success status
        """
        try:
            if not token:
                return {"success": False, "error": "Token is required"}
            
            # Decode token to get user_id
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if not user_id:
                return {"success": False, "error": "Invalid token payload"}
            
            token_hash = self._hash_token(token)
            now = datetime.datetime.utcnow()
            
            # Update session heartbeat and extend expiration
            result = self.sessions_collection.update_one(
                {
                    "user_id": user_id,
                    "token_hash": token_hash
                },
                {
                    "$set": {
                        "last_activity": now,
                        "last_heartbeat": now,  # Update heartbeat timestamp
                        "expires_at": now + datetime.timedelta(seconds=current_app.config.get('SESSION_TIMEOUT_SECONDS', 10))
                    }
                }
            )
            
            if result.modified_count > 0:
                return {"success": True, "message": "Session activity updated"}
            else:
                return {"success": False, "error": "Session not found or already expired"}
            
        except jwt.ExpiredSignatureError:
            return {"success": False, "error": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"success": False, "error": "Invalid token"}
        except Exception as e:
            return {"success": False, "error": f"Session update failed: {str(e)}"}
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by user ID.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            User data dictionary or None if not found
        """
        try:
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if user:
                return {
                    "id": str(user["_id"]),
                    "username": user["username"],
                    "stats": user.get("stats", {}),
                    "created_at": user.get("created_at"),
                    "last_login": user.get("last_login")
                }
            return None
        except Exception:
            return None
    
    def update_user_stats(self, user_id: str, game_won: bool, guesses_used: int) -> bool:
        """
        Update user's game statistics.
        
        Args:
            user_id: User's unique identifier
            game_won: Whether the game was won
            guesses_used: Number of guesses used in the game
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Get current stats
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return False
            
            stats = user.get("stats", {
                "games_played": 0,
                "games_won": 0,
                "total_guesses": 0,
                "average_guesses": 0.0
            })
            
            # Update stats
            stats["games_played"] += 1
            if game_won:
                stats["games_won"] += 1
            stats["total_guesses"] += guesses_used
            stats["average_guesses"] = stats["total_guesses"] / stats["games_played"]
            
            # Update in database
            result = self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"stats": stats}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error updating user stats: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """
        Remove sessions that have missed heartbeats (expired based on last_heartbeat).
        This is called periodically to clean up disconnected users.
        
        Returns:
            Dictionary with cleanup results and user information
        """
        try:
            # Find sessions where last_heartbeat is older than timeout
            cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(
                seconds=current_app.config.get('SESSION_TIMEOUT_SECONDS', 10)
            )
            
            # First, get the sessions that will be deleted to log user information
            expired_sessions = list(self.sessions_collection.find({
                "last_heartbeat": {"$lt": cutoff_time}
            }))
            
            # Get user information for logging
            disconnected_users = []
            for session in expired_sessions:
                user_id = session.get("user_id")
                if user_id:
                    user = self.users_collection.find_one({"_id": ObjectId(user_id)})
                    if user:
                        disconnected_users.append({
                            "user_id": user_id,
                            "username": user.get("username", "unknown"),
                            "last_heartbeat": session.get("last_heartbeat"),
                            "session_duration": (cutoff_time - session.get("created_at", cutoff_time)).total_seconds()
                        })
            
            # Delete expired sessions based on heartbeat timeout
            result = self.sessions_collection.delete_many({
                "last_heartbeat": {"$lt": cutoff_time}
            })
            
            if result.deleted_count > 0:
                print(f"Cleaned up {result.deleted_count} expired sessions due to missed heartbeats")
            
            return {
                "cleaned_count": result.deleted_count,
                "disconnected_users": disconnected_users
            }
            
        except Exception as e:
            print(f"Error cleaning up expired sessions: {e}")
            return {
                "cleaned_count": 0,
                "disconnected_users": [],
                "error": str(e)
            }
    
    def get_active_sessions_count(self) -> int:
        """
        Get the count of currently active sessions.
        
        Returns:
            Number of active sessions
        """
        try:
            return self.sessions_collection.count_documents({
                "expires_at": {"$gt": datetime.datetime.utcnow()}
            })
        except Exception:
            return 0
    
    def close_connection(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()


# Global service instance
_auth_service = None


def get_auth_service() -> Optional[AuthService]:
    """Get the global auth service instance."""
    return _auth_service


def initialize_auth_service(mongo_uri: str, jwt_secret: str) -> AuthService:
    """Initialize the global auth service instance."""
    global _auth_service
    try:
        _auth_service = AuthService(mongo_uri, jwt_secret)
        return _auth_service
    except Exception as e:
        print(f"Failed to initialize authentication service: {e}")
        return None
