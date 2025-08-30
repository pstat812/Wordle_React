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
