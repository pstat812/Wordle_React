"""
Wordle Game Server - Main Entry Point

This is the main entry point for the Wordle game server.
It initializes all services and starts the Flask-SocketIO application.
"""

import threading
import time
from app import create_app
from app.config import Config
from app.services.auth_service import initialize_auth_service, get_auth_service
from app.services.game_service import initialize_game_service, get_game_service
from app.services.lobby_service import initialize_lobby_service, get_lobby_service
from app.utils.game_logger import game_logger


def heartbeat_cleanup_worker(app):
    """
    Background worker that periodically cleans up expired sessions based on missed heartbeats.
    Runs every 15 seconds to check for users who haven't sent heartbeats.
    """
    print("Heartbeat cleanup worker started")
    while True:
        try:
            with app.app_context():
                auth_service = get_auth_service()
                game_service = get_game_service()
                lobby_service = get_lobby_service()
                
                if auth_service:
                    # Clean up sessions that haven't sent heartbeats in the last 10 seconds
                    cleanup_result = auth_service.cleanup_expired_sessions()
                    
                    # Debug logging
                    if cleanup_result["cleaned_count"] > 0:
                        print(f"Heartbeat cleanup found {cleanup_result['cleaned_count']} expired sessions")
                    
                    if cleanup_result["cleaned_count"] > 0:
                        game_logger.logger.info(f"Heartbeat cleanup: Removed {cleanup_result['cleaned_count']} expired sessions")
                    
                        # Log individual logout events for each disconnected user
                        for user_info in cleanup_result["disconnected_users"]:
                            username = user_info["username"]
                            user_id = user_info.get("user_id")
                            last_heartbeat = user_info["last_heartbeat"]
                            session_duration = user_info["session_duration"]
                            
                            # Simple console output for monitoring
                            print(f"{username} - Auto logout (missed heartbeat)")
                        
                            # Auto-leave lobby room if user was in one
                            if user_id and lobby_service:
                                try:
                                    lobby_service.cleanup_after_disconnect(user_id)
                                    print(f"{username} - Auto removed from lobby room")
                                except Exception as lobby_error:
                                    print(f"Lobby removal error for {username}: {lobby_error}")
                            
                            # Auto-forfeit multiplayer games if user was in one
                            if user_id and game_service:
                                try:
                                    print(f"Checking if user {username} ({user_id}) is in an active multiplayer game...")
                                    forfeit_result = game_service.handle_player_disconnect(user_id, username)
                                    if forfeit_result.get('games_affected', 0) > 0:
                                        game_logger.logger.info(f"User '{username}' forfeited {forfeit_result['games_affected']} multiplayer game(s) due to disconnect")
                                        print(f"{username} - Auto forfeited {forfeit_result['games_affected']} multiplayer game(s)")
                                    else:
                                        print(f"User {username} was not in any active multiplayer games")
                                except Exception as game_error:
                                    game_logger.logger.error(f"Failed to handle multiplayer game disconnect for {username}: {game_error}")
                                    print(f"Multiplayer game disconnect error for {username}: {game_error}")
                        
                            # Detailed log to file
                            game_logger.logger.info(f"User '{username}' automatically logged out due to missed heartbeat. Last heartbeat: {last_heartbeat}, Session duration: {session_duration:.1f}s")
                            
                            # Create a mock request object for logging USER_ACTION (same as manual logout)
                            class MockRequest:
                                def __init__(self, username):
                                    self.remote_addr = 'system'  # System-initiated
                                    self.method = 'AUTO_LOGOUT'
                                    self.path = '/heartbeat/timeout'
                                    self.url = 'http://system/heartbeat/timeout'
                                    self.endpoint = 'auth.heartbeat_timeout'
                                    self.user_agent = 'Heartbeat Monitor'
                                    self.username = username
                            
                            mock_request = MockRequest(username)
                            
                            # Log USER_ACTION logout event (same as manual logout button)
                            game_logger.log_user_action(
                                mock_request, 
                                'logout', 
                                extra_data={
                                    'user': username,
                                    'reason': 'missed_heartbeat',
                                    'automatic': True,
                                    'last_heartbeat': str(last_heartbeat),
                                    'session_duration': f"{session_duration:.1f}s"
                                }
                            )
                            
                            # Log server response for the automatic logout
                            game_logger.log_server_response(
                                mock_request, 
                                'logout', 
                                True, 
                                {
                                    'success': True, 
                                    'message': 'User automatically logged out due to missed heartbeat',
                                    'reason': 'missed_heartbeat'
                                }
                            )
                        
                            # Log as a game event for consistency with manual logouts
                            game_logger.log_game_event(
                                None,  # No specific game_id for auth events
                                'user_disconnected',
                                'system',  # System-initiated logout
                                username=username,
                                reason='missed_heartbeat',
                                last_heartbeat=str(last_heartbeat),
                                session_duration_seconds=session_duration
                            )
                
        except Exception as e:
            game_logger.logger.error(f"Error in heartbeat cleanup worker: {e}")
        
        # Wait 15 seconds before next cleanup (reduced for faster testing)
        time.sleep(15)


def main():
    """Main function to initialize services and start the server."""
    try:
        # Initialize all services
        print("Initializing services...")
        
        # Initialize authentication service
        if Config.MONGO_URI and Config.JWT_SECRET:
            auth_service = initialize_auth_service(Config.MONGO_URI, Config.JWT_SECRET)
            if auth_service:
                print("✓ Authentication service initialized successfully")
            else:
                print("✗ Failed to initialize authentication service")
        else:
            print("✗ MongoDB URI or JWT Secret not configured")
            auth_service = None
        
        # Initialize game service
        game_service = initialize_game_service()
        if game_service:
            print("✓ Game service initialized successfully")
        else:
            print("✗ Failed to initialize game service")
        
        # Initialize lobby service
        lobby_service = initialize_lobby_service()
        if lobby_service:
            print("✓ Lobby service initialized successfully")
        else:
            print("✗ Failed to initialize lobby service")
        
        # Create Flask app
        print("Creating Flask application...")
        app, socketio = create_app(Config)
        print("✓ Flask application created successfully")
        
        # Start heartbeat cleanup worker in background thread
        if auth_service:
            cleanup_thread = threading.Thread(target=heartbeat_cleanup_worker, args=(app,), daemon=True)
            cleanup_thread.start()
            print("✓ Heartbeat cleanup worker started - checking every 15 seconds")
        
        # Log server startup
        game_logger.logger.info("Wordle Server Starting - Comprehensive logging, authentication, and heartbeat monitoring enabled")
        
        print(f"\nStarting Wordle Game Server on {Config.HOST}:{Config.PORT}")
        print(f"Debug mode: {Config.DEBUG}")
        print(f"Auth available: {auth_service is not None}")
        print("=" * 50)
        
        # Start the server
        socketio.run(app, host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
        
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        game_logger.logger.info("Wordle Server shutting down (KeyboardInterrupt)")
    except Exception as e:
        print(f"Error starting server: {e}")
        game_logger.logger.error(f"Error starting server: {e}")
        raise


if __name__ == '__main__':
    main()