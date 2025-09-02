/**
 * Custom React Hook for WebSocket Management
 * 
 * This hook provides a clean interface for managing WebSocket connections
 * in React components, with automatic cleanup and state management.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import websocketService from '../services/websocketService';
import { useAuth } from './useAuth';

export function useWebSocket() {
  const { token } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const connectionAttempted = useRef(false);

  // Connect to WebSocket server
  const connect = useCallback(async () => {
    if (!token || connectionAttempted.current) {
      return;
    }

    try {
      connectionAttempted.current = true;
      setConnectionError(null);
      
      const success = await websocketService.connect(token);
      setIsConnected(success);
      
      // Set up connection status listeners
      websocketService.on('connect', () => {
        // WebSocket connected
        setIsConnected(true);
        setConnectionError(null);
      });

      websocketService.on('disconnect', () => {
        // WebSocket disconnected
        setIsConnected(false);
      });

      websocketService.on('connect_error', (error) => {
        // WebSocket connection error
        setIsConnected(false);
        setConnectionError(error.message || 'Connection failed');
      });

    } catch (error) {
      // Failed to connect to WebSocket
      setConnectionError(error.message || 'Connection failed');
      setIsConnected(false);
    }
  }, [token]);

  // Disconnect from WebSocket server
  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setIsConnected(false);
    setConnectionError(null);
    connectionAttempted.current = false;
  }, []);

  // Auto-connect when token is available
  useEffect(() => {
    if (token && !connectionAttempted.current) {
      connect();
    }

    // Don't disconnect on unmount - keep WebSocket persistent across page navigation
    // Only disconnect when token changes (user logs out)
  }, [token, connect]);

  return {
    isConnected,
    connectionError,
    connect,
    disconnect,
    websocketService
  };
}

export function useMultiplayerWebSocket(gameId) {
  const { token } = useAuth();
  const { isConnected, websocketService } = useWebSocket();
  const [gameState, setGameState] = useState(null);
  const [gameEnded, setGameEnded] = useState(false);
  const joinedRoom = useRef(false);

  // Join multiplayer game room
  const joinGame = useCallback(() => {
    if (isConnected && gameId && token && !joinedRoom.current) {
      // Joining multiplayer game
      websocketService.joinMultiplayerGame(gameId, token);
      joinedRoom.current = true;
    }
  }, [isConnected, gameId, token, websocketService]);

  // Leave multiplayer game room
  const leaveGame = useCallback(() => {
    if (isConnected && gameId && token && joinedRoom.current) {
      // Leaving multiplayer game
      websocketService.leaveMultiplayerGame(gameId, token);
      joinedRoom.current = false;
    }
  }, [isConnected, gameId, token, websocketService]);

  // Set up game event listeners
  useEffect(() => {
    if (!isConnected || !websocketService) {
      return;
    }

    // Game state update handler
    const handleGameStateUpdate = (data) => {
      // Received game state update
      if (data.success && data.state) {
        // Ensure the game state has required player data before setting
        if (data.state.player || data.state.game_over) {
          setGameState(data.state);
        } else {
          console.warn('Received incomplete game state update, ignoring:', data.state);
        }
      }
    };

    // Game ended handler
    const handleGameEnded = (data) => {
      // Game ended
      console.log('Game ended event received:', data);
      setGameEnded(true);
      
      // Always update game state with final game data, regardless of current state
      const baseState = gameState || {};
      const finalState = {
        ...baseState,
        game_over: true,
        winner: data.winner_id,
        game_status: data.game_status,
        target_word: data.target_word,
        disconnect_reason: data.reason, // Track if game ended due to disconnect
        // Ensure we have the game_id from the event data
        game_id: data.game_id || baseState.game_id,
        // Ensure player object exists to prevent undefined errors
        player: baseState.player || {
          current_round: 0,
          guesses: [],
          guess_results: [],
          letter_status: {},
          game_over: true,
          won: false,
          finished: true
        }
      };
      setGameState(finalState);
    };

    // Player joined handler
    const handlePlayerJoined = (data) => {
      // Player joined
    };

    // Player left handler
    const handlePlayerLeft = (data) => {
      // Player left
    };

    // Error handler
    const handleError = (error) => {
      // WebSocket error
    };

    // Add event listeners
    websocketService.on('game_state_update', handleGameStateUpdate);
    websocketService.on('game_ended', handleGameEnded);
    websocketService.on('player_joined', handlePlayerJoined);
    websocketService.on('player_left', handlePlayerLeft);
    websocketService.on('error', handleError);

    // Join game when ready
    joinGame();

    // Cleanup function
    return () => {
      try {
        websocketService.off('game_state_update', handleGameStateUpdate);
        websocketService.off('game_ended', handleGameEnded);
        websocketService.off('player_joined', handlePlayerJoined);
        websocketService.off('player_left', handlePlayerLeft);
        websocketService.off('error', handleError);
        
        // Only try to leave game if still connected
        if (isConnected && websocketService.isConnectedToServer()) {
          leaveGame();
        }
      } catch (error) {
        // Ignore cleanup errors - connection might be closing
        console.warn('Error during multiplayer WebSocket cleanup:', error);
      }
    };
  }, [isConnected, websocketService, joinGame, leaveGame]);

  // Reset state when game changes
  useEffect(() => {
    setGameState(null);
    setGameEnded(false);
    joinedRoom.current = false;
  }, [gameId]);

  return {
    gameState,
    gameEnded,
    isConnected,
    joinGame,
    leaveGame
  };
}

export function useLobbyWebSocket() {
  const { token } = useAuth();
  const { isConnected, websocketService } = useWebSocket();
  const [lobbyState, setLobbyState] = useState(null);
  const [roomJoinResult, setRoomJoinResult] = useState(null);
  const [gameStarted, setGameStarted] = useState(null);
  const joinedLobby = useRef(false);

  // Join lobby
  const joinLobby = useCallback(() => {
    if (isConnected && token && !joinedLobby.current) {
      // Joining lobby
      websocketService.joinLobby(token);
      joinedLobby.current = true;
    }
  }, [isConnected, token, websocketService]);

  // Leave lobby
  const leaveLobby = useCallback(() => {
    if (isConnected && token && joinedLobby.current) {
      // Leaving lobby
      websocketService.leaveLobby(token);
      joinedLobby.current = false;
    }
  }, [isConnected, token, websocketService]);

  // Join room
  const joinRoom = useCallback((roomId) => {
    if (isConnected && token) {
      // Joining room
      websocketService.joinRoom(roomId, token);
    }
  }, [isConnected, token, websocketService]);

  // Leave room
  const leaveRoom = useCallback(() => {
    if (isConnected && token) {
      // Leaving room
      websocketService.leaveRoom(token);
    }
  }, [isConnected, token, websocketService]);



  // Clear room join result
  const clearRoomJoinResult = useCallback(() => {
    setRoomJoinResult(null);
  }, []);

  // Clear game started
  const clearGameStarted = useCallback(() => {
    setGameStarted(null);
  }, []);

  // Force refresh lobby state
  const refreshLobbyState = useCallback(() => {
    if (isConnected && token) {
      // Forcing lobby state refresh
      // Leave and rejoin lobby to get fresh state
      if (joinedLobby.current) {
        websocketService.leaveLobby(token);
        joinedLobby.current = false;
      }
      // Rejoin will happen automatically via the joinLobby effect
      setTimeout(() => {
        joinLobby();
      }, 100);
    }
  }, [isConnected, token, websocketService, joinLobby]);

  // Set up lobby event listeners
  useEffect(() => {
    if (!isConnected || !websocketService) {
      return;
    }

    // Lobby state update handler
    const handleLobbyStateUpdate = (data) => {
      // Received lobby state update
      setLobbyState(data);
    };

    // Room join result handler
    const handleRoomJoinResult = (data) => {
      // Room join result
      setRoomJoinResult(data);
    };

    // Room leave result handler
    const handleRoomLeaveResult = (data) => {
      // Room leave result
      setRoomJoinResult(data);
    };

    // Game started handler
    const handleGameStarted = (data) => {

      setGameStarted(data);
    };

    // User joined/left lobby handlers
    const handleUserJoinedLobby = (data) => {
      // User joined lobby
    };

    const handleUserLeftLobby = (data) => {
      // User left lobby
    };

    // Error handler
    const handleError = (error) => {
      // Lobby WebSocket error
    };

    // Add event listeners
    websocketService.on('lobby_state_update', handleLobbyStateUpdate);
    websocketService.on('room_join_result', handleRoomJoinResult);
    websocketService.on('room_leave_result', handleRoomLeaveResult);
    websocketService.on('game_started', handleGameStarted);
    websocketService.on('user_joined_lobby', handleUserJoinedLobby);
    websocketService.on('user_left_lobby', handleUserLeftLobby);
    websocketService.on('error', handleError);

    // Join lobby when ready
    joinLobby();

    // Cleanup function
    return () => {
      try {
        websocketService.off('lobby_state_update', handleLobbyStateUpdate);
        websocketService.off('room_join_result', handleRoomJoinResult);
        websocketService.off('room_leave_result', handleRoomLeaveResult);
        websocketService.off('game_started', handleGameStarted);
        websocketService.off('user_joined_lobby', handleUserJoinedLobby);
        websocketService.off('user_left_lobby', handleUserLeftLobby);
        websocketService.off('error', handleError);
        
        // Only try to leave lobby if still connected
        if (isConnected && websocketService.isConnectedToServer()) {
          leaveLobby();
        }
      } catch (error) {
        // Ignore cleanup errors - connection might be closing
        console.warn('Error during lobby WebSocket cleanup:', error);
      }
    };
  }, [isConnected, websocketService, joinLobby, leaveLobby]);

  // Reset state when connection changes
  useEffect(() => {
    if (!isConnected && joinedLobby.current) {
      setLobbyState(null);
      setRoomJoinResult(null);
      setGameStarted(null);
      joinedLobby.current = false;
    }
  }, [isConnected]);

  return {
    lobbyState,
    roomJoinResult,
    gameStarted,
    isConnected,
    joinLobby,
    leaveLobby,
    joinRoom,
    leaveRoom,
    clearRoomJoinResult,
    clearGameStarted,
    refreshLobbyState
  };
}
