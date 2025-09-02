/**
 * Lobby Page Component
 * 
 * Handles multiplayer lobby where players can join rooms and start games.
 * Uses WebSocket for real-time updates of room states and player connections.
 */

import React, { useState, useEffect, useCallback } from 'react';
import Header from '../components/Header';
import Alert from '../components/Alert';
import RulesModal from '../components/RulesModal';
import { getLobbyState } from '../services/apiService';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { useLobbyWebSocket } from '../hooks/useWebSocket';
import './LobbyPage.css';
import '../App.css';

function LobbyPage({ 
  onBackToMenu,
  onStartMultiplayer,
  isDarkMode, 
  onToggleDarkMode,
  showAlert,
  hideAlert,
  alert
}) {
  const { token, user } = useAuth();
  const theme = useTheme(isDarkMode);
  
  // WebSocket connection for real-time lobby updates
  const {
    lobbyState: wsLobbyState,
    roomJoinResult,
    gameStarted,
    isConnected: wsConnected,
    joinRoom: wsJoinRoom,
    leaveRoom: wsLeaveRoom,
    clearRoomJoinResult,
    clearGameStarted,
    refreshLobbyState
  } = useLobbyWebSocket();

  // Local state
  const [userCurrentRoom, setUserCurrentRoom] = useState(null);
  const [showRulesModal, setShowRulesModal] = useState(false);

  // Use WebSocket lobby state only
  const currentLobbyState = wsLobbyState;

  // Force fresh lobby state when component mounts (returning from game)
  useEffect(() => {
    if (wsConnected) {
      // When returning to lobby (especially after a game), we want to ensure
      // we have the most up-to-date lobby state, not cached/stale state
      setTimeout(() => {
        refreshLobbyState();
      }, 500); // Small delay to ensure WebSocket is fully ready
    }
  }, [wsConnected, refreshLobbyState]);

  // WebSocket-only approach - no HTTP fallback needed

  // Handle room join - WebSocket only
  const handleJoinRoom = useCallback((roomId) => {
    if (userCurrentRoom) {
      showAlert('Please leave your current room first', 'warning');
      return;
    }

    if (!wsConnected) {
      showAlert('Connection lost. Please refresh the page.', 'error');
      return;
    }

    try {
      // Use WebSocket for real-time join
      wsJoinRoom(roomId);
    } catch (error) {
      // Failed to join room
      showAlert('Failed to join room. Please try again.', 'error');
    }
  }, [userCurrentRoom, wsConnected, wsJoinRoom, showAlert]);

  // Handle room leave - WebSocket only
  const handleLeaveRoom = useCallback(() => {
    if (!wsConnected) {
      showAlert('Connection lost. Please refresh the page.', 'error');
      return;
    }

    try {
      // Use WebSocket for real-time leave
      wsLeaveRoom();
    } catch (error) {
      // Failed to leave room
      showAlert('Failed to leave room. Please try again.', 'error');
    }
  }, [wsConnected, wsLeaveRoom, showAlert]);



  // Handle WebSocket room join results
  useEffect(() => {
    if (roomJoinResult) {
      if (roomJoinResult.success) {
        showAlert(roomJoinResult.message || 'Room action completed', 'success');
        
        // Show auto-start message if room is full
        if (roomJoinResult.room && roomJoinResult.room.players.length === 2) {
          setTimeout(() => {
            showAlert('Room is full! Game will start automatically in 1 second...', 'info', 2000);
          }, 500);
        }
        
        // Don't set userCurrentRoom here, let the lobby state update handle it
      } else {
        showAlert(roomJoinResult.error || 'Failed to join/leave room', 'error');
      }
      
      // Clear the result after processing
      setTimeout(() => clearRoomJoinResult(), 100);
    }
  }, [roomJoinResult, showAlert, clearRoomJoinResult]);

  // Handle game start event
  useEffect(() => {
    if (gameStarted && gameStarted.success && onStartMultiplayer) {
      showAlert('Game is starting!', 'success', 1000);
      setTimeout(() => {
        onStartMultiplayer(gameStarted.game_id, gameStarted.players);
        clearGameStarted();
      }, 1000);
    }
  }, [gameStarted, onStartMultiplayer, showAlert, clearGameStarted]);



  // Update user's current room when lobby state changes
  useEffect(() => {
    if (currentLobbyState && currentLobbyState.rooms) {
      const userRoom = currentLobbyState.rooms.find(room => 
        room.players.some(player => player.id === user.id)
      );
      setUserCurrentRoom(userRoom);
    }
  }, [currentLobbyState, user.id]);

  // Loading state
  if (!wsConnected || !currentLobbyState) {
    return (
      <div className={`lobby-page ${isDarkMode ? 'lobby-page--dark' : ''}`} style={theme.cssProperties}>
        <Header
          isDarkMode={isDarkMode}
          onToggleDarkMode={onToggleDarkMode}
          onBackToMenu={onBackToMenu}
          showBackButton={true}
          showUserInfo={false}
          title="Multiplayer Lobby"
        />
        <div className="lobby-page__container">
          <div className="lobby-loading">
            <h2>Loading...</h2>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`lobby-page ${isDarkMode ? 'lobby-page--dark' : ''}`} style={theme.cssProperties}>
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
        onBackToMenu={onBackToMenu}
        showBackButton={true}
        showUserInfo={false}
        title="Multiplayer Lobby"
      />

      <div className="lobby-page__container">
        <div className="lobby-page__main">
          {/* Rules Button */}
          <div className="lobby-rules-section">
            <button
              className="rules-button"
              onClick={() => setShowRulesModal(true)}
            >
              <div className="rules-button__icon">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25A8.966 8.966 0 0118 3.75c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0118 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="rules-button__content">
                <span className="rules-button__title">Game Rules</span>
                <span className="rules-button__subtitle">Learn about spells & gameplay</span>
              </div>
            </button>
          </div>

          <div className="rooms-container">
            <div className="rooms-list">
              {currentLobbyState.rooms.map(room => {
                const isCurrentRoom = userCurrentRoom?.id === room.id;
                const isFull = room.players.length >= room.max_players;
                
                return (
                  <div 
                    key={room.id} 
                    className={`room-rectangle ${isCurrentRoom ? 'room-rectangle--current' : ''} ${isFull ? 'room-rectangle--full' : ''}`}
                  >
                    <div className="room-info">
                      <h3 className="room-name">{room.name}</h3>
                      <div className="room-players-info">
                        <div className="players-status">
                          <span className="player-count">
                            {room.players.length}/{room.max_players} players
                          </span>
                          {room.players.length > 0 && (
                            <span className="players-display">
                              {room.players.map((player, index) => (
                                <span key={player.id} className="player-name">
                                  {player.username}
                                  {player.id === user.id && ' (You)'}
                                  {index < room.players.length - 1 && ', '}
                                </span>
                              ))}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="room-action">
                      {isCurrentRoom ? (
                        <button 
                          className="btn btn--leave"
                          onClick={handleLeaveRoom}
                        >
                          Leave Room
                        </button>
                      ) : (
                        <button 
                          className={`btn ${isFull || userCurrentRoom ? 'btn--disabled' : 'btn--join'}`}
                          onClick={() => handleJoinRoom(room.id)}
                          disabled={isFull || userCurrentRoom}
                        >
                          {isFull ? 'Room Full' : userCurrentRoom ? 'Leave Current Room First' : 'Join Room'}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Rules Modal */}
        <RulesModal
          isOpen={showRulesModal}
          onClose={() => setShowRulesModal(false)}
        />
      </div>
    </div>
  );
}

export default LobbyPage;
