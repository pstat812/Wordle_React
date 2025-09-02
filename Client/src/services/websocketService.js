/**
 * WebSocket Service for Real-time Multiplayer Communication
 * 
 * This service handles WebSocket connections using Socket.IO for real-time
 * multiplayer game synchronization, eliminating the need for polling.
 */

import { io } from 'socket.io-client';
import { config } from '../config';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = config.websocket.reconnectionAttempts;
    this.eventListeners = new Map(); // Store event listeners for cleanup
  }

  /**
   * Connect to the WebSocket server
   * @param {string} token - JWT authentication token
   * @returns {Promise<boolean>} Connection success status
   */
  connect(token) {
    return new Promise((resolve, reject) => {
      try {
        // Prevent multiple simultaneous connection attempts
        if (this.socket && this.socket.connected) {
          // WebSocket already connected, skipping connection attempt
          resolve(true);
          return;
        }

        // Disconnect existing connection if any
        this.disconnect();

        // Connecting to WebSocket server

        // Create new socket connection
        this.socket = io(config.websocketUrl, {
          transports: config.websocket.transports,
          timeout: config.websocket.timeout,
          reconnection: config.websocket.reconnection,
          reconnectionAttempts: config.websocket.reconnectionAttempts,
          reconnectionDelay: config.websocket.reconnectionDelay,
          auth: {
            token: token
          }
        });

        // Connection successful
        this.socket.on('connect', () => {
          this.isConnected = true;
          this.reconnectAttempts = 0;
          resolve(true);
        });

        // Connection error
        this.socket.on('connect_error', (error) => {
          // WebSocket connection error
          this.isConnected = false;
          reject(error);
        });

        // Disconnection
        this.socket.on('disconnect', (reason) => {
          // WebSocket disconnected
          this.isConnected = false;
          
          // Handle different disconnect reasons
          if (reason === 'io server disconnect') {
            // Server disconnected the client, don't reconnect automatically
            // Server disconnected the client
          } else {
            // Client disconnected, will attempt to reconnect automatically
            // Client disconnected, will attempt to reconnect
          }
        });

        // Reconnection attempt
        this.socket.on('reconnect_attempt', (attemptNumber) => {
          // WebSocket reconnection attempt
          this.reconnectAttempts = attemptNumber;
        });

        // Reconnection successful
        this.socket.on('reconnect', (attemptNumber) => {
          // WebSocket reconnected
          this.isConnected = true;
          this.reconnectAttempts = 0;
        });

        // Reconnection failed
        this.socket.on('reconnect_failed', () => {
          // WebSocket reconnection failed after maximum attempts
          this.isConnected = false;
        });

        // Handle server errors
        this.socket.on('error', (error) => {
          // WebSocket error
        });

      } catch (error) {
        // Failed to create WebSocket connection
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    if (this.socket) {
      // Disconnecting WebSocket
      
      try {
        // Remove all event listeners
        this.eventListeners.forEach((listeners, event) => {
          listeners.forEach(listener => {
            try {
              this.socket.off(event, listener);
            } catch (error) {
              // Ignore errors when removing listeners during disconnect
            }
          });
        });
        this.eventListeners.clear();
        
        // Disconnect socket gracefully
        this.socket.disconnect();
      } catch (error) {
        // Ignore errors during disconnect - connection might already be closed
        console.warn('Error during WebSocket disconnect:', error);
      } finally {
        // Always clean up state
        this.socket = null;
        this.isConnected = false;
      }
    }
  }

  /**
   * Check if WebSocket is connected
   * @returns {boolean} Connection status
   */
  isConnectedToServer() {
    try {
      return this.isConnected && this.socket && this.socket.connected;
    } catch (error) {
      // If there's an error checking connection status, assume disconnected
      this.isConnected = false;
      return false;
    }
  }

  /**
   * Join a multiplayer game room for real-time updates
   * @param {string} gameId - Game ID to join
   * @param {string} token - JWT authentication token
   */
  joinMultiplayerGame(gameId, token) {
    if (!this.isConnectedToServer()) {
      // Cannot join game: WebSocket not connected
      return;
    }

    // Joining multiplayer game room
    this.socket.emit('join_multiplayer_game', {
      game_id: gameId,
      token: token
    });
  }

  /**
   * Leave a multiplayer game room
   * @param {string} gameId - Game ID to leave
   * @param {string} token - JWT authentication token
   */
  leaveMultiplayerGame(gameId, token) {
    if (!this.isConnectedToServer()) {
      return;
    }

    // Leaving multiplayer game room
    this.socket.emit('leave_multiplayer_game', {
      game_id: gameId,
      token: token
    });
  }

  /**
   * Join the lobby for real-time room updates
   * @param {string} token - JWT authentication token
   */
  joinLobby(token) {
    if (!this.isConnectedToServer()) {
      return;
    }

    this.socket.emit('join_lobby', {
      token: token
    });
  }

  /**
   * Leave the lobby
   * @param {string} token - JWT authentication token
   */
  leaveLobby(token) {
    if (!this.isConnectedToServer()) {
      return;
    }

    try {
      // Leaving lobby
      this.socket.emit('leave_lobby', {
        token: token
      });
    } catch (error) {
      // Ignore errors when leaving lobby - connection might be closing
      console.warn('Error leaving lobby (connection may be closing):', error);
    }
  }

  /**
   * Join a multiplayer room
   */
  joinRoom(roomId, token) {
    if (!this.isConnectedToServer()) {
      return;
    }

    this.socket.emit('join_room', {
      room_id: roomId,
      token: token
    });
  }

  /**
   * Leave current room
   */
  leaveRoom(token) {
    if (!this.isConnectedToServer()) return;
    
    this.socket.emit('leave_room', {
      token: token
    });
  }

  /**
   * Submit a guess
   */
  submitGuess(gameId, guess, token) {
    if (!this.isConnectedToServer()) return;

    this.socket.emit('submit_guess', {
      game_id: gameId,
      guess: guess,
      token: token
    });
  }

  /**
   * Listen for spell cast events
   */
  onSpellCast(callback) {
    if (!this.socket) return;
    this.socket.on('spell_cast', callback);
  }

  /**
   * Remove spell cast event listener
   */
  offSpellCast(callback) {
    if (!this.socket) return;
    this.socket.off('spell_cast', callback);
  }



  /**
   * Add event listener for WebSocket events
   * @param {string} event - Event name
   * @param {function} callback - Event callback function
   */
  on(event, callback) {
    if (!this.socket) {
      // Cannot add event listener: WebSocket not initialized
      return;
    }

    // Store listener for cleanup
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);

    // Add listener to socket
    this.socket.on(event, callback);
  }

  /**
   * Remove event listener for WebSocket events
   * @param {string} event - Event name
   * @param {function} callback - Event callback function
   */
  off(event, callback) {
    if (!this.socket) {
      return;
    }

    // Remove from stored listeners
    if (this.eventListeners.has(event)) {
      const listeners = this.eventListeners.get(event);
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }

    // Remove from socket
    this.socket.off(event, callback);
  }

  /**
   * Emit an event to the server
   * @param {string} event - Event name
   * @param {object} data - Event data
   */
  emit(event, data) {
    if (!this.isConnectedToServer()) {
      // Cannot emit event: WebSocket not connected
      return;
    }

    try {
      this.socket.emit(event, data);
    } catch (error) {
      // Ignore emit errors - connection might be closing
      console.warn(`Error emitting ${event} event:`, error);
    }
  }
}

// Create singleton instance
const websocketService = new WebSocketService();

export default websocketService;
