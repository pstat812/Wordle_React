/**
 * API Service Module for Wordle Client-Server Communication
 * 
 * This module handles all HTTP communication with the Wordle server,
 * abstracting API calls and providing error handling.
 */

import { config } from './config';

const API_BASE_URL = config.apiBaseUrl;

/**
 * Generic API request handler with error handling
 * @param {string} endpoint - API endpoint relative to base URL
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise<object>} Response data
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const requestConfig = { ...defaultOptions, ...options };

  try {
    // Add timeout support
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.requestTimeout);
    
    const response = await fetch(url, {
      ...requestConfig,
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    if (!data.success) {
      throw new Error(data.error || 'API request failed');
    }

    return data;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`Request timed out after ${config.requestTimeout / 1000} seconds. Please check your connection.`);
    }
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Unable to connect to game server. Please ensure the server is running.');
    }
    throw error;
  }
}

/**
 * Creates a new game session
 * @param {string} gameMode - Game mode: 'wordle' or 'absurdle'
 * @returns {Promise<object>} Game creation response with game_id and initial state
 */
export async function createNewGame(gameMode = 'wordle') {
  return await apiRequest('/new_game', {
    method: 'POST',
    body: JSON.stringify({ game_mode: gameMode }),
  });
}

/**
 * Gets the current state of a game
 * @param {string} gameId - Unique game identifier
 * @returns {Promise<object>} Current game state
 */
export async function getGameState(gameId) {
  return await apiRequest(`/game/${gameId}/state`);
}

/**
 * Submits a guess for evaluation
 * @param {string} gameId - Unique game identifier  
 * @param {string} guess - 5-letter word guess
 * @returns {Promise<object>} Updated game state with guess result
 */
export async function submitGuess(gameId, guess) {
  return await apiRequest(`/game/${gameId}/guess`, {
    method: 'POST',
    body: JSON.stringify({ guess }),
  });
}

/**
 * Deletes a completed game session
 * @param {string} gameId - Unique game identifier
 * @returns {Promise<object>} Deletion confirmation
 */
export async function deleteGame(gameId) {
  return await apiRequest(`/game/${gameId}`, {
    method: 'DELETE',
  });
}

/**
 * Checks server health status
 * @returns {Promise<object>} Server health information
 */
export async function checkServerHealth() {
  return await apiRequest('/health');
}

/**
 * Registers a new user account
 * @param {string} username - User's chosen username
 * @param {string} password - User's chosen password
 * @returns {Promise<object>} Registration response
 */
export async function registerUser(username, password) {
  return await apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

/**
 * Logs in a user and returns JWT token
 * @param {string} username - User's username
 * @param {string} password - User's password
 * @returns {Promise<object>} Login response with token and user data
 */
export async function loginUser(username, password) {
  return await apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

/**
 * Verifies JWT token and returns user info
 * @param {string} token - JWT token
 * @returns {Promise<object>} User verification response
 */
export async function verifyToken(token) {
  return await apiRequest('/auth/verify', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  });
}

/**
 * Gets user profile information
 * @param {string} token - JWT token
 * @returns {Promise<object>} User profile data
 */
export async function getUserProfile(token) {
  return await apiRequest('/auth/profile', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  });
}

/**
 * Logs out a user and invalidates their session
 * @param {string} token - JWT token
 * @returns {Promise<object>} Logout response
 */
export async function logoutUser(token) {
  return await apiRequest('/auth/logout', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  });
}

/**
 * Sends a heartbeat to keep the session alive
 * @param {string} token - JWT token
 * @returns {Promise<object>} Heartbeat response
 */
export async function sendHeartbeat(token) {
  return await apiRequest('/auth/heartbeat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  });
}

// ============================================================================
// MULTIPLAYER / LOBBY API FUNCTIONS
// ============================================================================

/**
 * Gets the current lobby state with all rooms and players
 * @param {string} token - JWT token
 * @returns {Promise<object>} Lobby state with rooms and players
 */
export async function getLobbyState(token) {
  return await apiRequest('/lobby/state', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  });
}

// HTTP API functions for join/leave room removed - using WebSocket only

/**
 * Starts a multiplayer game from a room
 * @param {string} token - JWT token
 * @param {number} roomId - Room ID to start game from
 * @returns {Promise<object>} Game creation response with multiplayer game details
 */
export async function startMultiplayerGame(token, roomId) {
  return await apiRequest('/multiplayer/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ room_id: roomId }),
  });
}

/**
 * Gets the current state of a multiplayer game
 * @param {string} token - JWT token
 * @param {string} gameId - Multiplayer game ID
 * @returns {Promise<object>} Current multiplayer game state
 */
export async function getMultiplayerGameState(token, gameId) {
  return await apiRequest(`/multiplayer/${gameId}/state`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  });
}

/**
 * Submits a guess in a multiplayer game
 * @param {string} token - JWT token
 * @param {string} gameId - Multiplayer game ID
 * @param {string} guess - 5-letter word guess
 * @returns {Promise<object>} Updated multiplayer game state with guess result
 */
export async function submitMultiplayerGuess(token, gameId, guess) {
  return await apiRequest(`/multiplayer/${gameId}/guess`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ guess }),
  });
}
