# Wordle Game Server Architecture

## Overview

This document describes the architecture of a scalable, production-ready Wordle game server built with Flask and Socket.IO. The server implements clean architecture principles with proper separation of concerns, comprehensive logging, and support for both single-player and multiplayer game modes.

## Technology Stack

- **Framework**: Flask 2.3.3 with Flask-SocketIO 5.3.6
- **Database**: MongoDB with PyMongo 4.6.0
- **Authentication**: JWT tokens with bcrypt password hashing
- **Real-time Communication**: WebSocket connections via Socket.IO
- **Configuration Management**: Environment variables with python-dotenv
- **Logging**: Structured JSON logging with daily file rotation

## Architecture Principles

The server follows several key architectural principles:

- **Clean Architecture**: Clear separation between controllers, services, and data models
- **Single Responsibility Principle**: Each module has a single, well-defined purpose
- **Dependency Injection**: Services are initialized and injected at startup
- **Configuration Management**: All settings managed via environment variables
- **Comprehensive Logging**: Full audit trail of user actions and system events
- **Error Handling**: Graceful error handling with proper HTTP status codes

## Directory Structure

```
Server/
├── main.py                 # Application entry point and service orchestration
├── requirements.txt        # Python dependencies
├── logs/                  # Application logs (auto-generated)
└── app/                   # Main application package
    ├── __init__.py        # Flask application factory
    ├── config/            # Configuration management
    │   ├── app_config.py  # Environment-based configuration
    │   ├── config.env     # Environment variables
    │   ├── game_settings.py # Game rules and constants
    │   └── wordles.json   # Word database (2309+ words)
    ├── controllers/       # HTTP request handlers
    │   ├── auth_controller.py    # Authentication endpoints
    │   ├── game_controller.py    # Game logic endpoints
    │   └── lobby_controller.py   # Multiplayer lobby endpoints
    ├── services/          # Business logic layer
    │   ├── auth_service.py       # User authentication and session management
    │   ├── game_service.py       # Core game logic and state management
    │   └── lobby_service.py      # Multiplayer room management
    ├── models/            # Data structures and schemas
    │   ├── game.py        # Game state and multiplayer models
    │   └── user.py        # User and statistics models
    ├── websocket/         # Real-time communication
    │   └── handlers.py    # Socket.IO event handlers
    └── utils/             # Shared utilities
        ├── decorators.py  # Authentication and validation decorators
        ├── game_logger.py # Comprehensive logging system
        └── helpers.py     # Common utility functions
```

## Core Components

### 1. Application Factory (`app/__init__.py`)

Implements the Flask application factory pattern for creating configurable application instances:

- **Extension Initialization**: Sets up CORS and Socket.IO with proper configuration
- **Blueprint Registration**: Registers all controller blueprints with appropriate URL prefixes
- **WebSocket Integration**: Connects Socket.IO handlers for real-time functionality
- **Modular Design**: Enables easy testing and deployment configuration

### 2. Configuration Management (`app/config/`)

Centralized configuration following 12-factor app methodology:

- **Environment-Based**: All settings loaded from environment variables
- **Multiple Environments**: Support for development, production, and testing configurations
- **Game Settings**: Centralized game rules and JSON-based word database management
- **Word Database**: 2309+ words loaded from JSON file with automatic validation
- **Security**: Secure handling of sensitive configuration like JWT secrets and database URIs

### 3. Authentication Service (`app/services/auth_service.py`)

Comprehensive user authentication and session management:

- **User Registration**: Secure password hashing with bcrypt
- **JWT Authentication**: Stateless token-based authentication
- **Session Management**: Active session tracking with heartbeat monitoring
- **MongoDB Integration**: Persistent user data storage
- **Security Features**: Automatic session cleanup and timeout handling

### 4. Game Service (`app/services/game_service.py`)

Core game logic engine supporting multiple game modes:

- **Game State Management**: Secure server-side game state without exposing answers
- **Multiple Game Modes**: Support for Wordle, Absurdle, and multiplayer variants
- **Word Validation**: Comprehensive guess validation and evaluation
- **Multiplayer Support**: Real-time multiplayer game coordination
- **Statistics Tracking**: Game performance and user statistics

### 5. Lobby Service (`app/services/lobby_service.py`)

Multiplayer room management system:

- **Room Management**: Simple, efficient room-based multiplayer organization
- **Player Coordination**: Automatic game matching when rooms fill up
- **Connection Handling**: Graceful handling of player disconnections
- **State Synchronization**: Real-time lobby state updates via WebSocket

### 6. WebSocket Handlers (`app/websocket/handlers.py`)

Real-time communication layer for multiplayer functionality:

- **Connection Management**: User connection tracking and cleanup
- **Event Routing**: Comprehensive event handling for multiplayer interactions
- **Authentication Integration**: Secure WebSocket connections with JWT validation
- **Broadcast System**: Efficient message broadcasting to specific rooms and users

### 7. HTTP Controllers (`app/controllers/`)

RESTful API endpoints organized by functionality:

- **Authentication Controller**: User registration, login, logout, and session management
- **Game Controller**: Single-player game creation, guess submission, and state retrieval
- **Lobby Controller**: Multiplayer lobby operations and room management

### 8. Data Models (`app/models/`)

Structured data representations using Python dataclasses:

- **Game Models**: Game state, multiplayer state, and letter evaluation enums
- **User Models**: User profiles and statistics tracking
- **Type Safety**: Strongly typed data structures with validation

### 9. Logging System (`app/utils/game_logger.py`)

Comprehensive audit trail and monitoring system:

- **Structured Logging**: JSON-formatted logs for easy parsing and analysis
- **Multiple Log Types**: User actions, server responses, game events, and errors
- **Daily Rotation**: Automatic log file rotation with date-based naming
- **Performance Monitoring**: Request timing and system performance tracking

## API Endpoints

### Authentication Endpoints (`/api/auth/`)

- `POST /register` - User registration with validation
- `POST /login` - User authentication with JWT token generation
- `POST /logout` - Session termination and cleanup
- `POST /heartbeat` - Session keepalive for active users

### Game Endpoints (`/api/`)

- `POST /new_game` - Create new single-player game session
- `POST /submit_guess` - Submit guess and receive evaluation
- `GET /game_state/<game_id>` - Retrieve current game state

### Lobby Endpoints (`/api/`)

- `GET /lobby` - Get current lobby state with all rooms
- `POST /join_room` - Join a specific multiplayer room
- `POST /leave_room` - Leave current room

## WebSocket Events

### Connection Management
- `connect` - Initial WebSocket connection
- `disconnect` - Connection termination and cleanup

### Multiplayer Events
- `join_multiplayer_game` - Join multiplayer game session
- `multiplayer_guess` - Submit guess in multiplayer game
- `lobby_state_update` - Real-time lobby state synchronization

## Security Features

### Authentication Security
- **Password Hashing**: bcrypt with salt for secure password storage
- **JWT Tokens**: Stateless authentication with configurable expiration
- **Session Management**: Active session tracking with automatic cleanup
- **Heartbeat Monitoring**: Automatic logout for inactive users

### Input Validation
- **Request Validation**: Comprehensive input validation and sanitization
- **Game State Protection**: Server-side game state prevents cheating
- **Rate Limiting**: Built-in protection against abuse

### Error Handling
- **Graceful Degradation**: Proper error responses without system exposure
- **Logging Integration**: All errors logged for monitoring and debugging
- **Status Codes**: Appropriate HTTP status codes for all responses

## Scalability Considerations

### Current Architecture
- **In-Memory State**: Game and lobby state stored in memory for performance
- **Single Instance**: Designed for single-server deployment
- **WebSocket Scaling**: Socket.IO with single-process architecture

### Future Scaling Options
- **Database State**: Migrate game state to MongoDB for multi-instance support
- **Redis Integration**: Add Redis for session management and real-time data
- **Load Balancing**: Socket.IO sticky sessions for horizontal scaling
- **Microservices**: Potential service separation for larger deployments

## Monitoring and Observability

### Logging Capabilities
- **User Action Tracking**: Complete audit trail of user interactions
- **Performance Metrics**: Request timing and response monitoring
- **Error Tracking**: Comprehensive error logging and categorization
- **Game Analytics**: Game performance and user behavior insights

### Health Monitoring
- **Database Connectivity**: MongoDB connection health checks
- **Service Status**: Individual service health validation
- **Memory Usage**: Game state memory monitoring
- **Connection Tracking**: Active user and WebSocket connection monitoring



