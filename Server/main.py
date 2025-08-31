#!/usr/bin/env python3
"""
Wordle Server Launcher

Simple launcher for the Wordle game server.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv('config.env')

def main():
    """Main function to launch the Wordle server."""
    try:
        HOST = os.getenv('HOST', '127.0.0.1')
        PORT = int(os.getenv('PORT', 5000))
        DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        from wordle_server import app
        print("Starting Wordle Game Server...")
        print(f"Server will be available at http://{HOST}:{PORT}")
        
        app.run(host=HOST, port=PORT, debug=DEBUG)
    except ImportError as e:
        print(f"Error: Could not import server module: {e}")
        print("Please ensure Flask is installed: pip install flask")
        print("Please ensure all required files are in the Server directory.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
