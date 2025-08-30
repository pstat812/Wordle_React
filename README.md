# React Wordle

### Implemented Features
- A React implementation of the classic Wordle game, replicating the original NYTimes version
- Supports both keyboard input and on-screen virtual keyboard for letter entry
- Supports Dark Mode to enhance user experience 
- Implemented client-server architecture with Flask backend and React frontend

- Next planned update: Server history logging 

### Development Notes
- The current word list contains a small set of test words. A comprehensive word list will be added in a future update.

### Game Rules

1. Guess the 5-letter word in the given number of attempts 
2. Each guess must be a valid 5-letter word from the word list
3. After each guess, the color of the tiles will change:
   - Green: Letter is correct and in the right position
   - Yellow: Letter is in the word but in the wrong position
   - Gray: Letter is not in the word at all

### Project Structure

```
wordle_task/
├── Client/                 # React Frontend Application
│   ├── public/
│   │   ├── index.html      # Main HTML template with loading states
│   │   └── manifest.json   # PWA manifest configuration
│   │
│   ├── src/
│   │   ├── components/     # Reusable React components
│   │   │   ├── Alert.js    # Notification system component
│   │   │   ├── DropdownMenu.js # Navigation dropdown menu
│   │   │   ├── GameBoard.js # Dynamic game board with tile grid
│   │   │   ├── GameTile.js  # Individual letter tile component
│   │   │   ├── InteractiveHoverButton.js # Enhanced button component
│   │   │   ├── Keyboard.js  # Virtual on-screen keyboard
│   │   │   └── SettingsModal.js # Game settings configuration modal
│   │   │  
│   │   ├── apiService.js   # HTTP client for server communication
│   │   ├── useWordleGame.js # Custom React hook for game state management
│   │   ├── App.js          # Main application component with game orchestration
│   │   ├── App.css         # Global application styles
│   │   ├── index.js        # React application entry point
│   │   └── index.css       # Global CSS styles and themes
│   │ 
│   ├── package.json        # NPM dependencies and build scripts
│   └── package-lock.json   # Dependency lock file
│
├── Server/                 # Python Flask Backend
│   ├── game_settings.py    # Server-side game configuration and validation
│   ├── wordle_server.py    # Main Flask application with game engine
│   ├── main.py            # Server launcher with error handling
│   ├── requirements.txt    # Python dependencies
│   └── venv/              # Python virtual environment (local)
│ 
└── README.md              # This documentation
```

### Setup and Installation

#### Prerequisites

**For Client (React Frontend):**
- Node.js 16.0 or higher
- npm 8.0 or higher (or yarn)

**For Server (Python Backend):**
- Python 3.8 or higher
- pip package manager

#### Full Application Setup

**Step 1: Server Setup**
1. Navigate to the Server directory
   ```bash
   cd Server
   ```

2. Create a Python virtual environment 
   ```bash
   python -m venv venv
   
   # Activate virtual environment
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. Install Python dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Start the server
   ```bash
   python main.py
   ```
   
   The server will start on `http://127.0.0.1:5000`

**Step 2: Client Setup**
1. Open a new terminal and navigate to the Client directory
   ```bash
   cd Client
   ```

2. Install NPM dependencies
   ```bash
   npm install
   ```

3. (Optional) Configure environment variables
   ```bash
   # Copy the example environment file
   cp env.example .env.local
   
   # Edit .env.local to customize API URL and other settings
   # Example: REACT_APP_API_BASE_URL=http://localhost:8000/api
   ```

4. Start the development server
   ```bash
   npm start
   ```

5. Open your browser and navigate to `http://localhost:3000`

#### Development Workflow

**Starting Both Servers:**
1. Terminal 1: Start the Python server (from Server/ directory)
   ```bash
   python main.py
   ```

2. Terminal 2: Start the React client (from Client/ directory)
   ```bash
   npm start
   ```

#### Server Configuration

**1. Game Settings**: Edit `Server/game_settings.py`
   ```python
   MAX_ROUNDS: Final[int] = 6  # Maximum attempts (controlled by server)
   WORD_LIST: Final[List[str]] = [
       "ABOUT", "AFTER", "AGAIN", "BRAIN", "CHAIR",
       # Add your words here (authoritative server list)
   ]
   ```

**2. Server Settings**: Edit `Server/wordle_server.py`
   ```python
   app.run(host='127.0.0.1', port=5000, debug=True)  # Server configuration
   ```

**3. CORS Configuration**: Modify CORS settings for production
   ```python
   from flask_cors import CORS
   CORS(app, origins=['http://localhost:3000'])  # Specific origins
   ```

### Framework

#### Backend Framework
- **Flask 2.3.3**: Lightweight Python web framework for REST API
- **Flask-CORS 4.0.0**: Cross-Origin Resource Sharing support for client-server communication

#### Frontend Framework
- **React**: Modern JavaScript library for building user interfaces
- **Create React App**: Standard toolchain for React development
- **RESTful API**: Standard HTTP methods for stateless communication

## API Documentation

The server provides a REST API for game management and communication between client and server.

### Base URL
```
http://127.0.0.1:5000/api
```

### Endpoints

#### POST /new_game
Creates a new game session with a randomly selected word.

**Request Body:**
```json
{
  // No body parameters - max_rounds is controlled by server
}
```

**Response:**
```json
{
  "success": true,
  "game_id": "uuid-string",
  "state": {
    "game_id": "uuid-string",
    "current_round": 0,
    "max_rounds": 6,
    "game_over": false,
    "won": false,
    "guesses": [],
    "guess_results": [],
    "letter_status": {},
    "answer": null
  }
}
```

#### GET /game/{game_id}/state
Retrieves the current state of a game session.

**Response:**
```json
{
  "success": true,
  "state": {
    "game_id": "uuid-string",
    "current_round": 2,
    "max_rounds": 6,
    "game_over": false,
    "won": false,
    "guesses": ["ABOUT", "BRAIN"],
    "guess_results": [
      [["A", "MISS"], ["B", "HIT"], ["O", "PRESENT"], ["U", "MISS"], ["T", "MISS"]],
      [["B", "HIT"], ["R", "MISS"], ["A", "PRESENT"], ["I", "MISS"], ["N", "MISS"]]
    ],
    "letter_status": {},
    "answer": null
  }
}
```

#### POST /game/{game_id}/guess
Submits a guess for validation and evaluation.

**Request Body:**
```json
{
  "guess": "CHAIR"
}
```

**Response:**
```json
{
  "success": true,
  "state": {
    // Updated game state with new guess processed
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Word not in word list"
}
```

#### DELETE /game/{game_id}
Removes a completed game session from server memory.

**Response:**
```json
{
  "success": true
}
```

#### GET /health
Health check endpoint for server monitoring.

**Response:**
```json
{
  "status": "healthy",
  "active_games": 5
}
```