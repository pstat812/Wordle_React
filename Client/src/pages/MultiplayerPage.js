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

import { getMultiplayerGameState, submitMultiplayerGuess } from '../services/apiService';
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

  // Spell state
  const [spells, setSpells] = useState({
    FLASH: { used: false },
    WRONG: { used: false },
    BLOCK: { used: false }
  });

  // Opponent spell state
  const [opponentSpells, setOpponentSpells] = useState({
    FLASH: { used: false },
    WRONG: { used: false },
    BLOCK: { used: false }
  });

  // Spell effect states
  const [spellEffects, setSpellEffects] = useState({
    flashActive: false,
    wrongActive: false,
    blockActive: false,
    wrongLettersRemaining: 0
  });

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

  // Handle WebSocket game ended events immediately
  useEffect(() => {
    if (wsGameEnded && wsGameState && wsGameState.game_over && !showResultModal) {
      // Game ended via WebSocket (including disconnections) - show modal immediately
      console.log('Game ended via WebSocket, showing result modal');
      setShowResultModal(true);
      
      // Show specific alert for opponent disconnect
      if (wsGameState.disconnect_reason === 'opponent_disconnected') {
        showAlert('Your opponent disconnected - You Win!', 'success');
      }
    }
  }, [wsGameEnded, wsGameState, showResultModal, showAlert]);

  // Submit guess
  const handleSubmitGuess = useCallback(async () => {
    if (isSubmitting) return;
    
    // Client-side validation (only basic checks, let server handle word list)
    if (!currentGuess) {
      showAlert('Please enter a word', 'warning');
      return;
    }
    
    // Check if this is a spell cast
    const isSpell = ['FLASH', 'WRONG', 'BLOCK'].includes(currentGuess);

    if (!isSpell) {
      // Normal word validation
      if (currentGuess.length !== 5) {
        showAlert('Word must be exactly 5 letters', 'warning');
        return;
      }

      if (!/^[A-Z]+$/.test(currentGuess)) {
        showAlert('Word must contain only letters', 'warning');
        return;
      }
    } else {
      // Spell validation
      if (spells[currentGuess]?.used) {
        showAlert(`You have already used ${currentGuess} this game`, 'warning');
        setCurrentGuess('');
        return;
      }
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
  }, [currentGuess, gameId, token, currentGameState, isSubmitting, showAlert, fetchGameState, user.id, isInvalidWordError, wsConnected, spells]);



  // Input handlers (separate functions like normal Wordle)
  const handleLetterInput = useCallback((letter) => {
    if (currentGameState?.player?.finished || currentGameState?.game_over) return;

    // Check if BLOCK spell is active
    if (spellEffects.blockActive) {
      return; // Block all input
    }

    // Handle WRONG spell effect
    if (spellEffects.wrongActive && spellEffects.wrongLettersRemaining > 0) {
      // Replace input with random letter
      const randomLetter = String.fromCharCode(65 + Math.floor(Math.random() * 26));
      setCurrentGuess(prev => prev + randomLetter);
      setSpellEffects(prev => ({
        ...prev,
        wrongLettersRemaining: prev.wrongLettersRemaining - 1,
        wrongActive: prev.wrongLettersRemaining - 1 > 0
      }));
      return;
    }

    if (currentGuess.length < 5) {
      setCurrentGuess(prev => prev + letter);
    }
  }, [currentGuess, currentGameState, spellEffects]);

  const handleBackspaceInput = useCallback(() => {
    if (currentGameState?.player?.finished || currentGameState?.game_over) return;

    // Check if BLOCK spell is active
    if (spellEffects.blockActive) {
      return; // Block all input
    }

    setCurrentGuess(prev => prev.slice(0, -1));
  }, [currentGameState, spellEffects]);

  const handleEnterInput = useCallback(() => {
    if (currentGameState?.player?.finished || currentGameState?.game_over) return;

    // Check if BLOCK spell is active
    if (spellEffects.blockActive) {
      return; // Block all input
    }

    handleSubmitGuess();
  }, [currentGameState, handleSubmitGuess, spellEffects]);



  // Physical keyboard event listener (like normal Wordle)
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (currentGameState?.player?.finished || currentGameState?.game_over) return;

      // Check if BLOCK spell is active - block all keyboard input
      if (spellEffects.blockActive) {
        event.preventDefault();
        return;
      }

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
  }, [currentGameState, handleLetterInput, handleEnterInput, handleBackspaceInput, spellEffects]);

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
        // Check if this was a spell cast
        if (data.spell_cast) {
          // Update spell usage tracking
          const spell = data.result.spell;
          if (spells[spell]) {
            setSpells(prev => ({
              ...prev,
              [spell]: { ...prev[spell], used: true }
            }));
          }
        }
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
  }, [wsConnected, user.id, showAlert, isInvalidWordError, spells]);

  // Handle spell effects from other players
  useEffect(() => {
    if (!wsConnected) return;

    const handleSpellCast = (data) => {
      const { spell, caster_id, target_ids } = data;

      // Update opponent spell tracking if they cast the spell
      if (caster_id !== user.id) {
        setOpponentSpells(prev => ({
          ...prev,
          [spell]: { ...prev[spell], used: true }
        }));
      }

      // Check if we're a target of this spell
      if (target_ids.includes(user.id)) {
        switch (spell) {
          case 'FLASH':
            // Activate flash effect for 3 seconds
            setSpellEffects(prev => ({ ...prev, flashActive: true }));
            setTimeout(() => {
              setSpellEffects(prev => ({ ...prev, flashActive: false }));
            }, 3000);
            showAlert('⚡ FLASH! Your screen is blinded!', 'warning', 3000);
            break;

          case 'WRONG':
            // Activate wrong spell effect for next 5 letters
            setSpellEffects(prev => ({
              ...prev,
              wrongActive: true,
              wrongLettersRemaining: 5
            }));
            showAlert('🎭 WRONG! Your next 5 letters will be randomized!', 'warning', 3000);
            break;

          case 'BLOCK':
            // Activate block effect for 3 seconds
            setSpellEffects(prev => ({ ...prev, blockActive: true }));
            setTimeout(() => {
              setSpellEffects(prev => ({ ...prev, blockActive: false }));
            }, 3000);
            showAlert('🚫 BLOCK! Your input is disabled for 3 seconds!', 'warning', 3000);
            break;

          default:
            break;
        }
      }
    };

    websocketService.onSpellCast(handleSpellCast);

    return () => {
      websocketService.offSpellCast(handleSpellCast);
    };
  }, [wsConnected, user.id, showAlert]);

  // Helper function to render spell status
  const renderSpellStatus = (spellData) => {
    return (
      <div className="spell-status">
        {Object.entries(spellData).map(([spellName, spellInfo]) => (
          <span
            key={spellName}
            className={`spell-indicator ${spellInfo.used ? 'spell-indicator--used' : 'spell-indicator--available'}`}
            title={`${spellName}: ${spellInfo.used ? 'Used' : 'Available'}`}
          >
            {spellName}
          </span>
        ))}
      </div>
    );
  };

  // Loading state or missing player data
  if (loading || !currentGameState || !currentGameState.player) {
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
      {/* Flash Spell Effect Overlay */}
      {spellEffects.flashActive && (
        <div className="flash-overlay"></div>
      )}
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
                {currentGameState.player?.current_round || 0}/{currentGameState.max_rounds} attempts
              </span>
              {renderSpellStatus(spells)}
            </div>
          </div>

          <div className="status-section">
            <h3>{currentGameState.opponent ? currentGameState.opponent.username.toUpperCase() : 'WAITING...'}</h3>
            <div className="player-info">
              {currentGameState.opponent ? (
                <>
                  <span className="attempts">
                    {currentGameState.opponent?.current_round || 0}/{currentGameState.max_rounds} attempts
                  </span>
                  {renderSpellStatus(opponentSpells)}
                </>
              ) : (
                <span>Waiting for opponent...</span>
              )}
            </div>
          </div>
        </div>



        {/* Waiting Message */}
        {currentGameState.player?.finished && !currentGameState.game_over && (
          <div className="waiting-message">
            <h3>⏳ Waiting for opponent to finish...</h3>
            <p>You've completed your attempts. Your opponent is still playing.</p>
          </div>
        )}

        {/* Game Board */}
        <GameBoard
          guesses={currentGameState.player?.guesses || []}
          guessResults={currentGameState.player?.guess_results || []}
          currentInput={currentGameState.player?.finished ? '' : currentGuess}
          maxRounds={currentGameState.max_rounds}
          currentRound={currentGameState.player?.current_round || 0}
          gameOver={currentGameState.player?.finished || false}
          won={currentGameState.player?.won || false}
        />



        {/* Keyboard */}
        {!currentGameState.player?.finished && !currentGameState.game_over && (
          <Keyboard
            letterStatus={currentGameState.player?.letter_status || {}}
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