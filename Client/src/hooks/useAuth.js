/**
 * Authentication Hook for User State Management
 * 
 * This hook provides authentication state management including
 * login and logout. Tokens are stored in memory only (not persisted)
 * to allow multiple accounts in different tabs.
 */

import React, { useState, useEffect, createContext, useContext } from 'react';
import { loginUser, logoutUser, sendHeartbeat } from '../apiService';

// Create authentication context
const AuthContext = createContext();

/**
 * Authentication Provider Component
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize auth state - no auto-login, always start unauthenticated
  useEffect(() => {
    // Simply set loading to false, don't check for stored tokens
    setLoading(false);
  }, []);

  // Browser event handling to cleanup sessions when tab/browser is closed
  useEffect(() => {
    const handleBeforeUnload = (event) => {
      // Only attempt logout if user is authenticated and has a token
      if (token && user) {
        try {
          // Use sendBeacon API for reliable logout during page unload
          // sendBeacon doesn't support custom headers, so we include token in URL
          const logoutUrl = `/api/auth/logout?token=${encodeURIComponent(token)}`;
          
          // Try sendBeacon first (most reliable during page unload)
          if (navigator.sendBeacon) {
            navigator.sendBeacon(logoutUrl, '');
          } else {
            // Fallback: synchronous fetch (less reliable but better than nothing)
            fetch('/api/auth/logout', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({}),
              keepalive: true // Helps ensure request completes during unload
            }).catch(() => {
              // Ignore errors during unload
            });
          }
        } catch (error) {
          // Ignore errors during unload - we tried our best
          console.log('Cleanup during unload failed:', error);
        }
      }
    };

    const handleVisibilityChange = () => {
      // Additional cleanup when page becomes hidden (mobile browsers, tab switching)
      if (document.visibilityState === 'hidden' && token && user) {
        try {
          // Use sendBeacon for hidden state as well
          const logoutUrl = `/api/auth/logout?token=${encodeURIComponent(token)}`;
          if (navigator.sendBeacon) {
            navigator.sendBeacon(logoutUrl, '');
          }
        } catch (error) {
          console.log('Cleanup during visibility change failed:', error);
        }
      }
    };

    // Only add event listeners if user is authenticated
    if (token && user) {
      // beforeunload: triggered when user closes tab/browser or navigates away
      window.addEventListener('beforeunload', handleBeforeUnload);
      
      // visibilitychange: triggered when tab becomes hidden (mobile browsers)
      document.addEventListener('visibilitychange', handleVisibilityChange);
      
      // pagehide: additional fallback for some browsers
      window.addEventListener('pagehide', handleBeforeUnload);
    }

    // Cleanup function to remove event listeners
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('pagehide', handleBeforeUnload);
    };
  }, [token, user]); // Re-run effect when token or user changes

  // Heartbeat mechanism to detect disconnections
  useEffect(() => {
    let heartbeatInterval;
    let heartbeatFailures = 0;
    const MAX_HEARTBEAT_FAILURES = 1; // Allow only 1 failure before logout (disconnect after 5 seconds)
    
    if (token && user) {
      // Send heartbeat every 5 seconds to detect disconnections quickly
      heartbeatInterval = setInterval(async () => {
        try {
          await sendHeartbeat(token);
          heartbeatFailures = 0; // Reset failure count on success
          // Heartbeat successful (no console output to reduce noise)
        } catch (error) {
          heartbeatFailures++;
          console.error(`Heartbeat failed (${heartbeatFailures}/${MAX_HEARTBEAT_FAILURES}):`, error);
          
          // Check if error indicates session expired or invalid
          const errorMessage = error.message?.toLowerCase() || '';
          const isSessionExpired = errorMessage.includes('session') || 
                                   errorMessage.includes('expired') || 
                                   errorMessage.includes('invalid') ||
                                   errorMessage.includes('unauthorized');
          
          // If session is expired or we've had too many consecutive failures, logout
          if (isSessionExpired || heartbeatFailures >= MAX_HEARTBEAT_FAILURES) {
            console.warn(isSessionExpired ? 
              'Session expired or invalid - logging out user' : 
              'Heartbeat failure detected - logging out user (5 second timeout)');
            
            // Force logout due to connection issues or session expiry
            try {
              await logout();
            } catch (logoutError) {
              console.error('Error during forced logout:', logoutError);
              // Force client-side logout even if server call fails
              setToken(null);
              setUser(null);
              setError('Connection lost - please log in again');
            }
          }
        }
      }, 5 * 1000); // 5 seconds in milliseconds
    }
    
    // Cleanup interval when component unmounts or user logs out
    return () => {
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
      }
    };
  }, [token, user]); // Re-run when token or user changes

  const login = async (username, password) => {
    try {
      setError(null);
      
      const result = await loginUser(username, password);
      
      if (result.success) {
        setToken(result.token);
        setUser(result.user);
        // Remove localStorage token storage to prevent auto-login across tabs
        // localStorage.setItem(AUTH_TOKEN_KEY, result.token);
        return result;
      } else {
        throw new Error(result.error || 'Login failed');
      }
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  const logout = async () => {
    try {
      // Call server logout if we have a token
      if (token) {
        await logoutUser(token);
      }
    } catch (error) {
      console.error('Server logout failed:', error);
      // Continue with client-side logout even if server call fails
    } finally {
      // Always clear client-side state
      setToken(null);
      setUser(null);
      setError(null);
    }
  };

  const clearError = () => {
    setError(null);
  };

  const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    clearError
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to use authentication context
 */
export function useAuth() {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
}
