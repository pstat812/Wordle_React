# React Wordle

### Implemented Features
- A React implementation of the classic Wordle game, replicating the original NYTimes version
- Supports both keyboard input and on-screen virtual keyboard for letter entry
- Supports Dark Mode to enhance user experience 
- Animated letter tiles that flip and reveal colors when submitting a guess
- Implemented client-server architecture with Flask backend and React frontend
- Comprehensive logging system for game analytics and debugging
- New Host cheating wordle(Absurdle) game mode with adversarial gameplay
- User authentication system with login/registration
- Implemented session tracking with heartbeat mechanism to detect when players close browser tabs
- Added protection against concurrent logins from the same user account
- Real-time multiplayer functionality using WebSocket 
- Lobby system for multiplayer room management
- Automatic win detection when opponent disconnects in multiplayer mode


For detailed architecture documentation, see `Server/ARCHITECTURE.md`

### Planned Development
- Prevent players idle in game
- Personal statistics and game history tracking dashboard
- Enhanced user profile management

### Game Rules

#### Wordle Mode (Classic)
1. Guess the 5-letter word in limited attempts 
2. Each guess must be a valid 5-letter word from the word list
3. After each guess, the color of the tiles will change:
   - Green: Letter is correct and in the right position
   - Yellow: Letter is in the word but in the wrong position
   - Gray: Letter is not in the word at all

#### Absurdle Mode (Adversarial)
1. Guess the 5-letter word
2. Each guess must be a valid 5-letter word from the word list
3. The game dynamically chooses feedback to keep as many word possibilities open
4. The game board grows with each guess (starts with 1 row, adds more as needed)
5. Win condition: Force the game to narrow down to exactly one possible word

#### Multiplayer Mode (Competitive)
1. Two players compete to guess the same 5-letter word
2. Each player has 6 attempts to guess the word
3. Both players see their own game board and opponent progress
4. **Win Conditions:**
   - First player to guess the word correctly wins
   - If both players fail to guess within 6 attempts, the game ends in a draw
   - If one player disconnects, the remaining player wins automatically
5. **Special Spell System** - Players can cast spells to hinder their opponent:
   - **FLASH**: Blinds opponent's screen for 3 seconds (type "FLASH" as your guess)
   - **WRONG**: Next 5 letters opponent types will be randomized (type "WRONG" as your guess)  
   - **BLOCK**: Disables opponent's input for 3 seconds (type "BLOCK" as your guess)
   - Each spell can only be used once per game
   - Spells don't count as regular guesses

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

3. Start the development server
   ```bash
   npm start
   ```

4. Open your browser and navigate to `http://localhost:3000`

#### Server Configuration

**1. Environment Configuration**: Create `Server/app/config/.env` file 
   ```env
   # Database Configuration
   MONGO_URI=mongodb://your-mongo-url-here
   
   # JWT Configuration
   JWT_SECRET=your-jwt-secret-here
   
   # Server Configuration
   HOST=127.0.0.1
   PORT=5000
   DEBUG=True
   
   # Optional: Session and logging settings
   JWT_EXPIRATION_DAYS=7
   SESSION_TIMEOUT_SECONDS=10
   HEARTBEAT_INTERVAL_SECONDS=5
   ```

**2. Game Settings**: The word list is automatically loaded from `Server/app/config/wordles.json`
   ```python
   MAX_ROUNDS: Final[int] = 6  # Maximum attempts (controlled by server)
   # Word list is loaded from wordles.json (2309+ words)
   WORD_LIST: Final[List[str]] = _load_word_list()
   ```
   
   **Note**: To modify the word list, edit `Server/app/config/wordles.json`. The system automatically validates all words are 5 letters and alphabetic.

**3. Application Configuration**: The `Server/app/config/app_config.py` loads settings from environment variables
   ```python
   # Configuration is automatically loaded from environment variables
   # The main settings include:
   class Config:
       SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
       DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
       HOST = os.getenv('HOST', '127.0.0.1')
       PORT = int(os.getenv('PORT', 5000))
       MONGO_URI = os.getenv('MONGO_URI')
       JWT_SECRET = os.getenv('JWT_SECRET')
       JWT_EXPIRATION_DAYS = int(os.getenv('JWT_EXPIRATION_DAYS', 7))
   ```

### Project Structure

```
wordle_task/
├── Client/                          # React Frontend Application
│   ├── public/
│   │   ├── index.html               # Main HTML template with loading states
│   │   └── manifest.json            # PWA manifest configuration
│   │
│   ├── src/
│   │   ├── components/              # Reusable React components
│   │   │   ├── AbsurdleBoard.js     # Dynamic growing game board for Absurdle mode
│   │   │   ├── Alert.js             # Notification system component
│   │   │   ├── GameBoard.js         # Dynamic game board with tile grid
│   │   │   ├── GameResultModal.js   # Game completion modal with results
│   │   │   ├── GameTile.js          # Individual letter tile component
│   │   │   ├── Header.js            # Application header with navigation and controls
│   │   │   ├── Keyboard.js          # Virtual on-screen keyboard 
│   │   │   ├── RegisterModal.js     # User registration modal component
│   │   │   └── RulesModal.js        # Game rules modal component
│   │   │  
│   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── useAuth.js           # Authentication state management hook
│   │   │   ├── useTheme.js          # Theme and dark mode management hook
│   │   │   ├── useWebSocket.js      # WebSocket connection and event management
│   │   │   └── useWordleGame.js     # Game state management hook
│   │   │
│   │   ├── pages/                   # Page components for different app sections
│   │   │   ├── AbsurdlePage.js      # Absurdle game mode page
│   │   │   ├── LoginPage.js         # User authentication page
│   │   │   ├── LobbyPage.js         # Multiplayer lobby and room management
│   │   │   ├── MenuPage.js          # Game mode selection interface
│   │   │   ├── MultiplayerPage.js   # Real-time multiplayer game page
│   │   │   └── WordlePage.js        # Wordle game mode page
│   │   │
│   │   ├── services/                # Service layer for external communication
│   │   │   ├── apiService.js        # HTTP client for server communication
│   │   │   └── websocketService.js  # WebSocket service for real-time communication
│   │   │
│   │   ├── theme/                   # Theme configuration
│   │   │   └── colors.js            # Color scheme definitions
│   │   │  
│   │   ├── config.js                # Application configuration settings
│   │   ├── App.js                   # Main application component with routing
│   │   ├── index.js                 # React application entry point
│   │   └── index.css                # Global styles and themes
│   │ 
│   ├── package.json                 # NPM dependencies and build scripts
│   └── package-lock.json            # Dependency lock file
│
├── Server/                          # Modular Python Flask Backend
│   ├── app/                         # Main application package
│   │   ├── __init__.py             # Flask app factory with blueprint registration
│   │   ├── controllers/            # HTTP route handlers (MVC Controllers)
│   │   │   ├── __init__.py
│   │   │   ├── auth_controller.py  # Authentication endpoints
│   │   │   ├── game_controller.py  # Game-related endpoints
│   │   │   └── lobby_controller.py # Multiplayer/lobby endpoints
│   │   ├── models/                 # Data models and schemas
│   │   │   ├── __init__.py
│   │   │   ├── game.py            # Game state models
│   │   │   └── user.py            # User models
│   │   ├── services/              # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py    # Authentication logic
│   │   │   ├── game_service.py    # Core game logic
│   │   │   └── lobby_service.py   # Multiplayer/lobby logic
│   │   ├── websocket/             # WebSocket handlers
│   │   │   ├── __init__.py
│   │   │   └── handlers.py        # WebSocket event handlers
│   │   ├── utils/                 # Utility functions
│   │   │   ├── __init__.py
│   │   │   ├── decorators.py      # Auth decorators
│   │   │   ├── helpers.py         # Helper functions
│   │   │   └── game_logger.py     # Logging utilities
│   │   └── config/                # Configuration management
│   │       ├── __init__.py
│   │       ├── app_config.py      # Flask application configuration
│   │       ├── game_settings.py   # Game rules and constants
│   │       ├── config.env         # Environment variables
│   │       └── wordles.json       # Word database (2309+ words)
│   ├── logs/                      # Application logs directory
│   ├── main.py                    # Server launcher with error handling
│   ├── requirements.txt           # Python dependencies
│   └── ARCHITECTURE.md            # Detailed architecture documentation
│ 
└── README.md                      # This documentation
```

### Framework

#### Backend Framework
- **Flask 2.3.3**: Lightweight Python web framework for REST API
- **Flask-CORS 4.0.0**: Cross-Origin Resource Sharing support for client-server communication
- **Flask-SocketIO 5.3.6**: WebSocket support for real-time multiplayer functionality
- **PyMongo 4.6.0**: MongoDB integration for user authentication and data persistence
- **bcrypt 4.1.2**: Secure password hashing
- **PyJWT 2.8.0**: JSON Web Token authentication
- **python-dotenv 1.0.0**: Environment variable management from .env files

#### Frontend Framework
- **React 18.2.0**: Modern JavaScript library for building user interfaces
- **React DOM 18.2.0**: React rendering for web browsers
- **Create React App 5.0.1**: Standard toolchain for React development
- **Socket.IO Client 4.7.2**: WebSocket client for real-time communication
- **RESTful API**: Standard HTTP methods for stateless communication