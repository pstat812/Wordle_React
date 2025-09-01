/**
 * Multiplayer Game Page Component
 * 
 * Handles competitive multiplayer Wordle gameplay where two players
 * compete to guess the same word. First to guess wins, or draw if both fail.
 */

import React, { useState, useEffect, useCallback } from 'react';
import Header from '../components/Header';
import Alert from '../components/Alert';
import GameBoard from '../components/GameBoard';
import Keyboard from '../components/Keyboard';
import GameResultModal from '../components/GameResultModal';
import { getMultiplayerGameState, submitMultiplayerGuess } from '../apiService';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { useMultiplayerWebSocket } from '../hooks/useWebSocket';
import websocketService from '../services/websocketService';
import './MultiplayerPage.css';
import '../App.css';

function MultiplayerPage({ 
  gameId,
  isDarkMode, 
  onToggleDarkMode, 
  onBackToMenu,
  onBackToLobby,
  showAlert,
  hideAlert,
  alert
}) {
  const { token, user } = useAuth();
  const theme = useTheme(isDarkMode);
  
  // WebSocket connection for real-time updates
  const { 
    gameState: wsGameState, 
    gameEnded: wsGameEnded, 
    isConnected: wsConnected 
  } = useMultiplayerWebSocket(gameId);

  // Helper function to determine if an error is about invalid words
  const isInvalidWordError = useCallback((errorMessage) => {
    const lowerMessage = errorMessage.toLowerCase();
    return lowerMessage.includes('word not in word list') || 
           lowerMessage.includes('not in word list') ||
           lowerMessage.includes('invalid guess') ||
           lowerMessage.includes('must be exactly 5 letters') ||
           lowerMessage.includes('must contain only letters');
  }, []);
  
  // Game state
  const [gameState, setGameState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentGuess, setCurrentGuess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showResultModal, setShowResultModal] = useState(false);
  const [useWebSocket, setUseWebSocket] = useState(false);

  // Fetch game state (fallback for non-WebSocket or initial load)
  const fetchGameState = useCallback(async () => {
    if (!gameId || !token) return;
    
    try {
      const response = await getMultiplayerGameState(token, gameId);
      if (response.success) {
        const newGameState = response.state;
        const wasGameOver = gameState?.game_over;
        
        setGameState(newGameState);
        
        // Show modal when game ends (but not on initial load)
        if (newGameState.game_over && !wasGameOver && !showResultModal) {
          setShowResultModal(true);
        }
      } else {
        showAlert('Failed to load game state', 'error');
      }
    } catch (error) {
      // Failed to fetch game state
      showAlert('Connection error. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  }, [gameId, token, showAlert, gameState?.game_over, showResultModal]);

  // Use WebSocket game state when available, otherwise use local state
  // Hardcode max_rounds to 6 for multiplayer mode
  const currentGameState = wsConnected && wsGameState ? 
    { ...wsGameState, max_rounds: 6 } : 
    (gameState ? { ...gameState, max_rounds: 6 } : gameState);

  // Submit guess
  const handleSubmitGuess = useCallback(async () => {
    if (isSubmitting) return;
    
    // Client-side validation (only basic checks, let server handle word list)
    if (!currentGuess) {
      showAlert('Please enter a word', 'warning');
      return;
    }
    
    if (currentGuess.length !== 5) {
      showAlert('Word must be exactly 5 letters', 'warning');
      return;
    }
    
    if (!/^[A-Z]+$/.test(currentGuess)) {
      showAlert('Word must contain only letters', 'warning');
      return;
    }
    
    if (gameState?.player?.finished) {
      showAlert('You have already finished your attempts!', 'warning');
      return;
    }

    if (gameState?.game_over) {
      showAlert('Game is over!', 'warning');
      return;
    }

    setIsSubmitting(true);
    
    try {
      if (wsConnected) {
        // Use WebSocket for real-time guess submission
        websocketService.submitGuess(gameId, currentGuess, token);
        
        // Clear current guess immediately
        setCurrentGuess('');
        
        // The result will be handled by WebSocket event listeners
      } else {
        // Fallback to HTTP API
        const response = await submitMultiplayerGuess(token, gameId, currentGuess);
        
        if (response.success) {
          // Clear current guess
          setCurrentGuess('');
          
          // Refresh game state
          await fetchGameState();
          
          // Handle game result messages
          const result = response.result;
          if (result.winner && result.game_over) {
            if (result.winner === user.id) {
              showAlert('🎉 You won! You guessed the word first!', 'success', 5000);
            } else {
              showAlert('😔 Your opponent won this round.', 'info', 5000);
            }
          } else if (result.game_status === 'draw') {
            showAlert('🤝 It\'s a draw! Neither player guessed the word.', 'info', 5000);
          } else if (result.player_state?.finished && !result.player_state?.won) {
            showAlert('⏳ You\'ve used all attempts. Waiting for opponent to finish...', 'info', 5000);
          }
        } else {
          const errorMessage = response.error || 'Invalid guess';
          showAlert(errorMessage, isInvalidWordError(errorMessage) ? 'warning' : 'error');
        }
      }
    } catch (error) {
      // Failed to submit guess
      const errorMessage = error.message || 'Failed to submit guess. Please try again.';
      showAlert(errorMessage, isInvalidWordError(errorMessage) ? 'warning' : 'error');
    } finally {
      if (!wsConnected) {
        setIsSubmitting(false);
      }
    }
  }, [currentGuess, gameId, token, currentGameState, isSubmitting, showAlert, fetchGameState, user.id, isInvalidWordError, wsConnected]);

  // Input handlers (separate functions like normal Wordle)
  const handleLetterInput = useCallback((letter) => {
    if (currentGameState?.player?.finished || currentGameState?.game_over) return;
    if (currentGuess.length < 5) {
      setCurrentGuess(prev => prev + letter);
    }
  }, [currentGuess, currentGameState]);

  const handleBackspaceInput = useCallback(() => {
    if (currentGameState?.player?.finished || currentGameState?.game_over) return;
    setCurrentGuess(prev => prev.slice(0, -1));
  }, [currentGameState]);

  const handleEnterInput = useCallback(() => {
    if (currentGameState?.player?.finished || currentGameState?.game_over) return;
    handleSubmitGuess();
  }, [currentGameState, handleSubmitGuess]);



  // Physical keyboard event listener (like normal Wordle)
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (currentGameState?.player?.finished || currentGameState?.game_over) return;
      
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
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [currentGameState, handleLetterInput, handleEnterInput, handleBackspaceInput]);

  // Initial load and polling (only if WebSocket not connected)
  useEffect(() => {
    if (gameId) {
      // Always fetch initial state
      fetchGameState();
      
      // Only use polling if WebSocket is not connected
      if (!wsConnected) {

        const pollInterval = setInterval(fetchGameState, 1000); // Faster polling as fallback
        
        return () => clearInterval(pollInterval);
      } else {

      }
    }
  }, [fetchGameState, gameId, wsConnected]);

  // Handle WebSocket game state updates
  useEffect(() => {
    if (wsGameState) {
      setLoading(false);
      
      // Check for game end and show modal - ensure we have target_word
      const wasGameOver = gameState?.game_over;
      if (wsGameState.game_over && !wasGameOver && !showResultModal && wsGameState.target_word) {
        setTimeout(() => {
          setShowResultModal(true);
        }, 500); // Increased delay to ensure state is fully updated
        
        // Note: Removed auto-return to lobby - only manual "Back to lobby" button should work
      }
    }
  }, [wsGameState, gameState?.game_over, showResultModal, onBackToLobby]);

  // Handle WebSocket game end event  
  useEffect(() => {
    if (wsGameEnded && !showResultModal) {
      // Always show modal when game ends via WebSocket event
      // The wsGameState should have been updated with target_word by handleGameEnded
      setTimeout(() => {
        setShowResultModal(true);
      }, 500); // Increased delay to ensure state is fully updated
      
      // Note: Removed auto-return to lobby - only manual "Back to lobby" button should work
    }
  }, [wsGameEnded, showResultModal, wsGameState, onBackToLobby]);

  // Handle WebSocket guess results
  useEffect(() => {
    if (!wsConnected) return;

    const handleGuessResult = (data) => {

      setIsSubmitting(false);
      
      if (data.success) {
        // Handle successful guess - game state will be updated via WebSocket
        // Game result alerts removed - GameResultModal handles win/lose/draw display
      } else {
        const errorMessage = data.error || 'Invalid guess';
        showAlert(errorMessage, isInvalidWordError(errorMessage) ? 'warning' : 'error');
      }
    };

    websocketService.on('guess_result', handleGuessResult);
    
    return () => {
      websocketService.off('guess_result', handleGuessResult);
    };
  }, [wsConnected, user.id, showAlert, isInvalidWordError]);

  // Loading state
  if (loading || !currentGameState) {
    return (
      <div 
        className={`app ${isDarkMode ? 'app--dark' : 'app--light'}`}
        style={theme.cssProperties}
      >
        <Header 
          isDarkMode={isDarkMode}
          onToggleDarkMode={onToggleDarkMode}
          onBackToMenu={onBackToMenu}
          showBackButton={true}
          showUserInfo={false}
          title="Multiplayer Game"
        />
        <div className="app__container">
          <div className="game__loading">
            <h2>Loading multiplayer game...</h2>
            <p>Please wait while we prepare your game</p>
            {wsConnected ? (
              <p style={{ color: '#22c55e', fontSize: '0.9em' }}>🔌 WebSocket connected - Real-time updates enabled</p>
            ) : (
              <p style={{ color: '#f59e0b', fontSize: '0.9em' }}>📡 Using HTTP polling - Some delays may occur</p>
            )}
          </div>
        </div>
      </div>
    );
  }



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
      
      {/* Header */}
      <Header 
        isDarkMode={isDarkMode}
        onToggleDarkMode={onToggleDarkMode}
        showBackButton={false}
        showUserInfo={false}
        title="Multiplayer Game"
        className="header--game"
      />

      <div className="app__container">


        {/* Game Status */}
        <div className="multiplayer-status">
          <div className="status-section">
            <h3>YOU</h3>
            <div className="player-info">
              <span className="attempts">
                {currentGameState.player.current_round}/{currentGameState.max_rounds} attempts
              </span>
            </div>
          </div>

          <div className="status-section">
            <h3>{currentGameState.opponent ? currentGameState.opponent.username.toUpperCase() : 'WAITING...'}</h3>
            <div className="player-info">
              {currentGameState.opponent ? (
                <span className="attempts">
                  {currentGameState.opponent.current_round}/{currentGameState.max_rounds} attempts
                </span>
              ) : (
                <span>Waiting for opponent...</span>
              )}
            </div>
          </div>
        </div>



        {/* Waiting Message */}
        {currentGameState.player.finished && !currentGameState.game_over && (
          <div className="waiting-message">
            <h3>⏳ Waiting for opponent to finish...</h3>
            <p>You've completed your attempts. Your opponent is still playing.</p>
          </div>
        )}

        {/* Game Board */}
        <GameBoard
          guesses={currentGameState.player.guesses}
          guessResults={currentGameState.player.guess_results}
          currentInput={currentGameState.player.finished ? '' : currentGuess}
          maxRounds={currentGameState.max_rounds}
          currentRound={currentGameState.player.current_round}
          gameOver={currentGameState.player.finished}
          won={currentGameState.player.won}
        />

        {/* Keyboard */}
        {!currentGameState.player.finished && !currentGameState.game_over && (
          <Keyboard
            letterStatus={currentGameState.player.letter_status}
            onLetterClick={handleLetterInput}
            onEnterClick={handleEnterInput}
            onBackspaceClick={handleBackspaceInput}
            gameOver={isSubmitting}
          />
        )}



        {/* Game Result Modal */}
        <GameResultModal
          isOpen={showResultModal}
          onClose={() => setShowResultModal(false)}
          onBackToLobby={onBackToLobby}
          gameResult={currentGameState}
          targetWord={currentGameState?.target_word}
          currentUser={user}
          isMultiplayer={true}
        />
      </div>
    </div>
  );
}

export default MultiplayerPage;