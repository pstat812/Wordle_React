/**
 * Custom React Hook for Wordle Game State Management with Server Communication
 *
 * This hook encapsulates all game state logic and provides a clean API
 * for React components to interact with the server-based game engine.
 */

import { useState, useCallback, useEffect } from 'react';
import { createNewGame, getGameState, submitGuess as apiSubmitGuess } from '../services/apiService';

// Letter Status Constants (matching server)
export const LETTER_STATUS = {
  HIT: "HIT",         // Letter is correct and in the correct position (Green in UI)
  PRESENT: "PRESENT", // Letter exists in target word but wrong position (Yellow in UI)
  MISS: "MISS",       // Letter does not exist in target word (Gray in UI)
  UNUSED: "UNUSED"    // Letter has not been guessed yet (Default state)
};

/**
 * Custom hook for managing Wordle game state with server communication
 * @param {string} gameMode - Game mode: 'wordle' or 'absurdle'
 * @returns {object} Game state and control functions
 */
export function useWordleGame(gameMode = 'wordle') {
  const [gameId, setGameId] = useState(null);
  const [currentInput, setCurrentInput] = useState("");
  const [initialized, setInitialized] = useState(false);
  const [gameState, setGameState] = useState({
    current_round: 0,
    max_rounds: 6, // will be overridden by server
    game_over: false,
    won: false,
    guesses: [],
    guess_results: [],
    letter_status: {},
    answer: null
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initialize letter status
  useEffect(() => {
    const letterStatus = {};
    for (let i = 65; i <= 90; i++) { // A-Z ASCII codes
      letterStatus[String.fromCharCode(i)] = LETTER_STATUS.UNUSED;
    }
    setGameState(prev => ({ ...prev, letter_status: letterStatus }));
  }, []);

  // Start new game
  const startNewGame = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Reset current input first
      setCurrentInput("");
      
      // Create new game on server
      const response = await createNewGame(gameMode);
      
      // Ensure the server response has the correct initial state
      const serverState = response.state;
      const initialLetterStatus = {};
      for (let i = 65; i <= 90; i++) { // A-Z ASCII codes
        initialLetterStatus[String.fromCharCode(i)] = LETTER_STATUS.UNUSED;
      }
      
      // Update game state first, then set gameId to prevent race conditions
      setGameState({
        current_round: serverState.current_round || 0,
        max_rounds: serverState.max_rounds || (gameMode === 'absurdle' ? 1 : 6),
        game_over: serverState.game_over || false,
        won: serverState.won || false,
        guesses: serverState.guesses || [],
        guess_results: serverState.guess_results || [],
        letter_status: serverState.letter_status || initialLetterStatus,
        answer: serverState.answer || null
      });
      
      // Set gameId last to prevent initialization effect from triggering
      setGameId(response.game_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [gameMode]);

  // Initialize game on first load only
  useEffect(() => {
    if (!initialized && !gameId && !loading) {
      setInitialized(true);
      startNewGame();
    }
  }, [initialized, gameId, loading]);

  // Add letter to current guess
  const addLetter = useCallback((letter) => {
    if (gameState.game_over || loading) return;
    
    if (currentInput.length >= 5 || !/^[A-Z]$/i.test(letter)) {
      return;
    }

    setCurrentInput(prev => prev + letter.toUpperCase());
  }, [gameState.game_over, loading, currentInput.length]);

  // Remove letter from current guess
  const removeLetter = useCallback(() => {
    if (gameState.game_over || loading) return;
    setCurrentInput(prev => prev.slice(0, -1));
  }, [gameState.game_over, loading]);

  // Submit current guess
  const submitGuess = useCallback(async () => {
    if (!gameId || loading || gameState.game_over) return;
    
    if (currentInput.length !== 5) {
      throw new Error("Guess must be exactly 5 letters");
    }

    try {
      setLoading(true);
      setError(null);
      const response = await apiSubmitGuess(gameId, currentInput);
      setGameState(response.state);
      setCurrentInput("");
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [gameId, currentInput, gameState.game_over, loading]);

  // Update game configuration (now only starts new game since server controls max rounds)
  const updateConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await createNewGame(gameMode);
      setGameId(response.game_id);
      setGameState(response.state);
      setCurrentInput("");
    } catch (err) {
      setError(err.message);
      // Failed to update config
    } finally {
      setLoading(false);
    }
  }, []);

  // Check if current input is valid for submission
  const canSubmitGuess = useCallback(() => {
    return currentInput.length === 5 && !loading && !gameState.game_over;
  }, [currentInput.length, loading, gameState.game_over]);

  // Format game state for UI compatibility
  const formattedGameState = {
    // Basic game info
    currentRound: gameState.current_round,
    maxRounds: gameState.max_rounds,
    gameOver: gameState.game_over,
    won: gameState.won,
    answer: gameState.answer,
    
    // Guess history
    guesses: gameState.guesses || [],
    guessResults: gameState.guess_results || [],
    
    // Letter status
    letterStatus: gameState.letter_status || {},
    
    // Current input
    currentInput,
    
    // Utility info
    remainingRounds: Math.max(0, gameState.max_rounds - gameState.current_round),
    
    // Loading and error states
    loading,
    error
  };

  return {
    // Game state
    ...formattedGameState,
    
    // Game actions
    addLetter,
    removeLetter,
    submitGuess,
    newGame: startNewGame,
    updateConfig,
    
    // Utility functions
    canSubmitGuess,
    
    // Server connection state
    connected: gameId !== null,
    gameId
  };
}
