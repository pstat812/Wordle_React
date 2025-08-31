"""
Authentication Service for Wordle Game Server

This module handles user authentication including registration, login,
password hashing, and JWT token management using MongoDB for data storage.
"""

import bcrypt
import jwt
import datetime
from typing import Optional, Dict, Any
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


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
        
        # Test connection
        try:
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB!")
        except Exception as e:
            print(f"MongoDB connection error: {e}")
            raise
        
        # Create unique index on username
        self.users_collection.create_index("username", unique=True)
    
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
            
            # Update last login
            self.users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.datetime.utcnow()}}
            )
            
            # Generate JWT token
            token_payload = {
                "user_id": str(user["_id"]),
                "username": user["username"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)  # Token expires in 7 days
            }
            
            token = jwt.encode(token_payload, self.jwt_secret, algorithm="HS256")
            
            return {
                "success": True,
                "token": token,
                "user": {
                    "id": str(user["_id"]),
                    "username": user["username"],
                    "stats": user.get("stats", {})
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Login failed: {str(e)}"}
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
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
            
            # Get user from database
            user = self.users_collection.find_one({"_id": self.db.users.find_one({"username": payload["username"]})["_id"]})
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
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by user ID.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            User data dictionary or None if not found
        """
        try:
            from bson.objectid import ObjectId
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
            from bson.objectid import ObjectId
            
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
    
    def close_connection(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
