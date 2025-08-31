/**
 * Authentication Hook for User State Management
 * 
 * This hook provides authentication state management including
 * login, logout, token storage, and user session persistence.
 */

import React, { useState, useEffect, createContext, useContext } from 'react';
import { loginUser, verifyToken } from '../apiService';

// Create authentication context
const AuthContext = createContext();

// Token storage key
const AUTH_TOKEN_KEY = 'wordle_auth_token';

/**
 * Authentication Provider Component
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize auth state from localStorage
  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
      
      if (!storedToken) {
        setLoading(false);
        return;
      }

      // Verify token with server
      const result = await verifyToken(storedToken);
      
      if (result.success) {
        setToken(storedToken);
        setUser(result.user);
      } else {
        // Token is invalid, remove it
        localStorage.removeItem(AUTH_TOKEN_KEY);
      }
    } catch (error) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      setError(null);
      
      const result = await loginUser(username, password);
      
      if (result.success) {
        setToken(result.token);
        setUser(result.user);
        localStorage.setItem(AUTH_TOKEN_KEY, result.token);
        return result;
      } else {
        throw new Error(result.error || 'Login failed');
      }
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setError(null);
    localStorage.removeItem(AUTH_TOKEN_KEY);
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
