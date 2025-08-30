/**
 * Wordle Game Application - Main Component
 *
 * This is the main React component that orchestrates the entire Wordle game.
 * It handles game state, user interactions, and UI updates following React best practices.
 */

import React, { useState, useEffect, useCallback } from 'react';
import GameBoard from './components/GameBoard';
import Keyboard from './components/Keyboard';
import SettingsModal from './components/SettingsModal';
import DropdownMenu from './components/DropdownMenu';
import Alert from './components/Alert';
import { useWordleGame } from './useWordleGame';
import './App.css';

function App() {
  const game = useWordleGame();
  const [showGameOver, setShowGameOver] = useState(false);
  const [gameOverShown, setGameOverShown] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [currentGameId, setCurrentGameId] = useState(null);
  const [alert, setAlert] = useState({ message: '', type: 'info', isVisible: false });

  // Alert utility functions
  const showAlert = useCallback((message, type = 'info', autoCloseDelay = 3000) => {
    setAlert({ message, type, isVisible: true, autoCloseDelay });
  }, []);

  const hideAlert = useCallback(() => {
    setAlert(prev => ({ ...prev, isVisible: false }));
  }, []);

  // Helper function to determine if an error is about invalid words
  const isInvalidWordError = useCallback((errorMessage) => {
    const lowerMessage = errorMessage.toLowerCase();
    return lowerMessage.includes('word not in word list') || 
           lowerMessage.includes('not in word list') ||
           lowerMessage.includes('invalid guess');
  }, []);

  // Submit guess handler
  const handleSubmitGuess = useCallback(async () => {
    if (game.loading) return; // Prevent multiple submissions
    
    try {
      if (!game.canSubmitGuess()) {
        showAlert("Please enter a 5-letter word from the word list!", "warning");
        return;
      }
      
      await game.submitGuess();
    } catch (error) {
      // Show invalid word errors as warnings, other errors as errors
      showAlert(error.message, isInvalidWordError(error.message) ? "warning" : "error");
    }
  }, [game, showAlert, isInvalidWordError]);

  // Unified input handlers for both physical and virtual keyboards
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
    handleSubmitGuess();
  }, [game.gameOver, game.loading, handleSubmitGuess]);

  // Handle keyboard input
  const handleKeyPress = useCallback((event) => {
    if (game.gameOver || game.loading) return;

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

  // Track game ID changes to detect new games
  useEffect(() => {
    if (game.gameId && game.gameId !== currentGameId) {
      // New game detected - reset all game over flags
      setCurrentGameId(game.gameId);
      setShowGameOver(false);
      setGameOverShown(false);
    }
  }, [game.gameId, currentGameId]);

  // Handle game over state
  useEffect(() => {
    // Only show game over modal if:
    // 1. Game is over
    // 2. Modal is not already shown
    // 3. Game over hasn't been shown for this game yet
    // 4. We have a valid game ID (game is properly initialized)
    if (game.gameOver && !showGameOver && !gameOverShown && game.gameId === currentGameId) {
      // Small delay to let the last guess animate before showing modal
      const GAME_OVER_DELAY_MS = 600;
      setTimeout(() => {
        setShowGameOver(true);
        setGameOverShown(true);
      }, GAME_OVER_DELAY_MS);
    }
  }, [game.gameOver, showGameOver, gameOverShown, game.gameId, currentGameId]);

  // Handle connection status
  useEffect(() => {
    if (!game.connected && game.gameId) {
      showAlert("🔴 Connecting to server...", "info", 0);
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

  const handleNewGame = () => {
    setShowGameOver(false);
    setGameOverShown(false);
    game.newGame();
  };

  const handleGameOverResponse = (playAgain) => {
    setShowGameOver(false);
    if (playAgain) {
      handleNewGame();
    }
  };

  return (
    <div className={`app ${isDarkMode ? 'app--dark' : 'app--light'}`}>
      {/* Alert System */}
      <Alert
        message={alert.message}
        type={alert.type}
        isVisible={alert.isVisible}
        onClose={hideAlert}
        autoCloseDelay={alert.autoCloseDelay}
      />
      
      <div className="app__container">
        <header className="app__header">
          <div className="app__header-line"></div>
          <div className="app__controls">
            <DropdownMenu
              options={[
                {
                  id: 'new-game',
                  label: 'New Game',
                  icon: '🎮',
                  onClick: handleNewGame
                },
                {
                  id: 'settings',
                  label: 'Settings',
                  icon: '⚙️',
                  onClick: () => setShowSettings(true)
                }
              ]}
              disabled={game.loading}
            />
          </div>
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

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        isDarkMode={isDarkMode}
        onToggleDarkMode={setIsDarkMode}
      />

      {/* Game Over Modal */}
      {showGameOver && (
        <div className="game-over-modal__overlay">
          <div className="game-over-modal">
            <div className="game-over-modal__content">
              <h2 className="game-over-modal__title">
                {game.won ? "🎉 You Won!" : "😔 Game Over"}
              </h2>
              <div className="game-over-modal__message">
                {game.won ? (
                  <p>
                    Congratulations!<br />
                    You guessed <strong>'{game.answer}'</strong> in {game.currentRound} attempts!
                  </p>
                ) : (
                  <p>
                    The word was: <strong>{game.answer}</strong><br />
                    Better luck next time!
                  </p>
                )}
              </div>
                              <div className="game-over-modal__buttons">
                  <button 
                    className="game-over-modal__button game-over-modal__button--play-again"
                    onClick={() => handleGameOverResponse(true)}
                  >
                    Play Again
                  </button>
                  <button 
                    className="game-over-modal__button game-over-modal__button--close"
                    onClick={() => handleGameOverResponse(false)}
                  >
                    Close
                  </button>
                </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
