/**
 * Wordle Game Page Component
 * 
 * This component handles the Wordle game mode, including game logic,
 * user interactions, and UI rendering.
 */

import React, { useState, useEffect, useCallback } from 'react';
import Header from '../components/Header';
import GameBoard from '../components/GameBoard';
import Keyboard from '../components/Keyboard';
import Alert from '../components/Alert';
import { useWordleGame } from '../hooks/useWordleGame';
import { useTheme } from '../hooks/useTheme';
import '../App.css';

function WordlePage({ 
  isDarkMode, 
  onToggleDarkMode, 
  onBackToMenu,
  showAlert,
  hideAlert,
  alert
}) {
  // Game hooks
  const game = useWordleGame('wordle');
  
  // UI state
  const [showGameOver, setShowGameOver] = useState(false);
  const [gameOverShown, setGameOverShown] = useState(false);
  const [currentGameId, setCurrentGameId] = useState(null);

  // Get theme colors
  const theme = useTheme(isDarkMode);

  // Helper function to determine if an error is about invalid words
  const isInvalidWordError = useCallback((errorMessage) => {
    const lowerMessage = errorMessage.toLowerCase();
    return lowerMessage.includes('word not in word list') || 
           lowerMessage.includes('not in word list') ||
           lowerMessage.includes('invalid guess');
  }, []);

  // Submit guess handler
  const handleSubmitGuess = useCallback(async (guess) => {
    try {
      await game.submitGuess(guess);
    } catch (error) {
      showAlert(error.message || 'Failed to submit guess', 'error');
    }
  }, [game, showAlert]);

  // Input handlers
  const handleLetterInput = useCallback((letter) => {
    if (game.gameOver || game.loading) return;
    game.addLetter(letter);
  }, [game]);

  const handleBackspaceInput = useCallback(() => {
    if (game.gameOver || game.loading) return;
    game.removeLetter();
  }, [game]);

  const handleEnterInput = useCallback(() => {
    if (game.gameOver || game.loading) return;
    if (game.currentInput.length !== 5) {
      showAlert('Word must be 5 letters long', 'warning');
      return;
    }
    handleSubmitGuess(game.currentInput);
  }, [game, handleSubmitGuess, showAlert]);

  // New game handler
  const handleNewGame = useCallback(async () => {
    // Prevent multiple concurrent new game requests
    if (game.loading) {
      return;
    }
    
    try {
      // Reset all UI state first
      setShowGameOver(false);
      setGameOverShown(false);
      setCurrentGameId(null);
      
      // Start new game
      await game.newGame();
    } catch (error) {
      showAlert(error.message || 'Failed to start new game', 'error');
    }
  }, [game, showAlert]);

  // Game over detection
  useEffect(() => {
    const GAME_OVER_DELAY_MS = 500;
    
    // Only show game over if:
    // 1. Game is actually over
    // 2. Modal is not already showing
    // 3. We haven't shown game over for this specific game ID yet
    // 4. Game has a valid answer (to prevent showing modal for uninitialized games)
    if (game.gameOver && !showGameOver && game.gameId && game.answer && game.gameId !== currentGameId) {
      const timeoutId = setTimeout(() => {
        setShowGameOver(true);
        setGameOverShown(true);
        setCurrentGameId(game.gameId);
      }, GAME_OVER_DELAY_MS);
      
      // Cleanup timeout if component unmounts or dependencies change
      return () => clearTimeout(timeoutId);
    }
  }, [game.gameOver, showGameOver, game.gameId, game.answer, currentGameId]);

  // Handle connection status
  useEffect(() => {
    if (!game.connected && game.gameId) {
      showAlert("🔄 Connecting to server...", "info", 0);
    } else if (game.connected && alert.message.includes("Connecting to server")) {
      hideAlert();
    }
  }, [game.connected, game.gameId, showAlert, hideAlert, alert.message]);

  // Handle error messages
  useEffect(() => {
    if (game.error) {
      // Show invalid word errors as warnings, other errors as errors
      showAlert(game.error, isInvalidWordError(game.error) ? "warning" : "error", 5000);
    }
  }, [game.error, showAlert, isInvalidWordError]);

  // Handle keyboard input
  const handleKeyPress = useCallback((event) => {
    if (game.gameOver || game.loading) return;
    
    // Check if event.key exists and is a string to prevent autofill errors
    if (!event.key || typeof event.key !== 'string') return;

    const key = event.key.toUpperCase();

    if (/^[A-Z]$/.test(key)) {
      handleLetterInput(key);
    } else if (key === 'ENTER') {
      handleEnterInput();
    } else if (key === 'BACKSPACE') {
      handleBackspaceInput();
    }
  }, [game.gameOver, game.loading, handleLetterInput, handleEnterInput, handleBackspaceInput]);

  // Set up keyboard event listener
  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [handleKeyPress]);

  // Game auto-initializes via useWordleGame hook

  return (
    <div 
      className={`app ${isDarkMode ? 'app--dark' : 'app--light'}`}
      style={theme.cssProperties}
    >
      {/* Alert System */}
      <Alert
        message={alert.message}
        type={alert.type}
        isVisible={alert.isVisible}
        onClose={hideAlert}
        autoCloseDelay={alert.autoCloseDelay}
      />
      
      {/* Header with game controls */}
      <Header 
        isDarkMode={isDarkMode}
        onToggleDarkMode={onToggleDarkMode}
        onBackToMenu={onBackToMenu}
        onNewGame={handleNewGame}
        showUserInfo={false}
        showLogout={false}
        showBackButton={true}
        showNewGameButton={true}
        className="header--game"
      />

      <div className="app__container">
        <header className="app__header">
          <div className="app__header-line"></div>
        </header>

        <main className="app__main">
          <GameBoard
            guesses={game.guesses}
            guessResults={game.guessResults}
            currentInput={game.currentInput}
            maxRounds={game.maxRounds}
            gameOver={game.gameOver}
          />

          <Keyboard
            letterStatus={game.letterStatus}
            onLetterClick={handleLetterInput}
            onEnterClick={handleEnterInput}
            onBackspaceClick={handleBackspaceInput}
            gameOver={game.gameOver || game.loading}
          />
          
          <footer className="app__footer">
            <div className="app__footer-line"></div>
          </footer>
        </main>
      </div>

      {/* Game Over Modal */}
      {showGameOver && (
        <div className="game-over-modal__overlay">
          <div className="game-over-modal">
            <div className="game-over-modal__content">
              <h2 className="game-over-modal__title">
                {game.won ? '🎉 Congratulations!' : '😔 Game Over'}
              </h2>
              <p className="game-over-modal__message">
                {game.won 
                  ? `You guessed the word "${game.answer}" in ${game.guesses.length} attempt${game.guesses.length === 1 ? '' : 's'}!`
                  : `The word was "${game.answer}". Better luck next time!`
                }
              </p>
              <div className="game-over-modal__buttons">
                <button 
                  className="game-over-modal__button game-over-modal__button--new-game"
                  onClick={handleNewGame}
                >
                  New Game
                </button>
                <button 
                  className="game-over-modal__button game-over-modal__button--menu"
                  onClick={onBackToMenu}
                >
                  Back to Menu
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WordlePage;
