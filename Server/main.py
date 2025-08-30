#!/usr/bin/env python3
"""
Wordle Server Launcher

Simple launcher for the Wordle game server.
"""

import sys

def main():
    """Main function to launch the Wordle server."""
    try:
        from wordle_server import app
        print("Starting Wordle Game Server...")
        print("Server will be available at http://127.0.0.1:5000")
        
        app.run(host='127.0.0.1', port=5000, debug=False)
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
