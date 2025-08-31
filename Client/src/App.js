/**
 * Multi-Mode Word Game Application - Main Component
 *
 * This is the main React component that orchestrates the entire application.
 * It handles routing between menu and different game modes (Wordle, Absurdle, Multiplayer),
 * authentication, and dark mode state following React best practices.
 */

import React, { useState, useEffect, useCallback } from 'react';
import MenuPage from './pages/MenuPage';
import LoginPage from './pages/LoginPage';
import WordlePage from './pages/WordlePage';
import AbsurdlePage from './pages/AbsurdlePage';
import MultiplayerPage from './pages/MultiplayerPage';

import { AuthProvider, useAuth } from './hooks/useAuth';
import { useTheme } from './hooks/useTheme';
import './App.css';

function AppContent() {
  const { isAuthenticated, loading: authLoading, login, logout, error: authError, clearError } = useAuth();
  
  // Game mode state - show login if not authenticated
  const [currentPage, setCurrentPage] = useState('menu'); // 'login', 'menu', 'wordle', 'absurdle', 'multiplayer'
  
  // UI state for alerts
  const [alert, setAlert] = useState({ message: '', type: 'info', isVisible: false });

  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedDarkMode = localStorage.getItem('wordleGameDarkMode');
    return savedDarkMode === 'true';
  });

  // Save dark mode preference to localStorage
  useEffect(() => {
    localStorage.setItem('wordleGameDarkMode', isDarkMode.toString());
  }, [isDarkMode]);

  // Dark mode toggle function
  const handleToggleDarkMode = useCallback(() => {
    setIsDarkMode(prev => !prev);
  }, []);

  // Get theme colors
  const theme = useTheme(isDarkMode);

  // Alert utility functions
  const showAlert = useCallback((message, type = 'info', autoCloseDelay = 3000) => {
    setAlert({ message, type, isVisible: true, autoCloseDelay });
  }, []);

  const hideAlert = useCallback(() => {
    setAlert(prev => ({ ...prev, isVisible: false }));
  }, []);

  // Handle authentication errors
  useEffect(() => {
    if (authError) {
      showAlert(authError, 'error', 5000);
      clearError();
    }
  }, [authError, showAlert, clearError]);

  // Game mode selection handler
  const handleGameModeSelect = useCallback((mode) => {
    hideAlert(); // Clear any existing alerts when navigating
    setCurrentPage(mode);
  }, [hideAlert]);

  // Back to menu handler
  const handleBackToMenu = useCallback(() => {
    hideAlert(); // Clear any existing alerts when navigating
    setCurrentPage('menu');
  }, [hideAlert]);

  // Login handler
  const handleLogin = useCallback(async (username, password) => {
    try {
      await login(username, password);
      hideAlert(); // Clear any existing alerts when successfully logging in
      setCurrentPage('menu');
    } catch (error) {
      console.error('Login failed:', error);
      // Error is handled by useAuth hook and shown via authError
    }
  }, [login, hideAlert]);

  // Logout handler
  const handleLogout = useCallback(async () => {
    try {
      await logout();
      setCurrentPage('login');
    } catch (error) {
      console.error('Logout failed:', error);
      showAlert('Logout failed', 'error');
    }
  }, [logout, showAlert]);

  // Clear alerts when navigating between pages
  useEffect(() => {
    hideAlert();
  }, [currentPage, hideAlert]);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated && currentPage !== 'login') {
      setCurrentPage('login');
    }
  }, [isAuthenticated, authLoading, currentPage]);

  // Loading state
  if (authLoading) {
    return (
      <div 
        className={`app ${isDarkMode ? 'app--dark' : 'app--light'} app--loading`}
        style={theme.cssProperties}
      >
        <div className="app__loading">
          <h2>Loading...</h2>
          <p>Setting up your word game experience</p>
        </div>
      </div>
    );
  }

  // Login page
  if (!isAuthenticated || currentPage === 'login') {
    return (
      <div 
        className={`app ${isDarkMode ? 'app--dark' : 'app--light'}`}
        style={theme.cssProperties}
      >
        <LoginPage 
          onLogin={handleLogin}
          showAlert={showAlert}
          hideAlert={hideAlert}
          alert={alert}
          isDarkMode={isDarkMode}
          onToggleDarkMode={handleToggleDarkMode}
        />
      </div>
    );
  }

  // Menu page
  if (currentPage === 'menu') {
    return (
      <div 
        className={`app ${isDarkMode ? 'app--dark' : 'app--light'}`}
        style={theme.cssProperties}
      >
        <MenuPage 
          onGameModeSelect={handleGameModeSelect}
          onLogout={handleLogout}
          isDarkMode={isDarkMode}
          onToggleDarkMode={handleToggleDarkMode}
          showAlert={showAlert}
          hideAlert={hideAlert}
          alert={alert}
        />
      </div>
    );
  }

  // Render game pages
  if (currentPage === 'wordle') {
    return (
      <WordlePage
        isDarkMode={isDarkMode}
        onToggleDarkMode={handleToggleDarkMode}
        onBackToMenu={handleBackToMenu}
        showAlert={showAlert}
        hideAlert={hideAlert}
        alert={alert}
      />
    );
  }

  if (currentPage === 'absurdle') {
    return (
      <AbsurdlePage
        isDarkMode={isDarkMode}
        onToggleDarkMode={handleToggleDarkMode}
        onBackToMenu={handleBackToMenu}
        showAlert={showAlert}
        hideAlert={hideAlert}
        alert={alert}
      />
    );
  }

  if (currentPage === 'multiplayer') {
    return (
      <MultiplayerPage
        isDarkMode={isDarkMode}
        onToggleDarkMode={handleToggleDarkMode}
        onBackToMenu={handleBackToMenu}
        showAlert={showAlert}
        hideAlert={hideAlert}
        alert={alert}
      />
    );
  }
}

// Wrapper component to provide authentication context
function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;