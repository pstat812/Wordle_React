/**
 * Header Component - Reusable header with user info, dark mode toggle, and logout
 * 
 * This component provides a consistent header across all pages with:
 * - Welcome message and username display
 * - Dark mode 
 * - Logout functionality
 * - Back to menu functionality
 * - New Game functionality
 */

import React from 'react';
import { useAuth } from '../hooks/useAuth';
import './Header.css';

function Header({ 
  isDarkMode, 
  onToggleDarkMode, 
  onLogout, 
  onBackToMenu,
  onNewGame,
  showUserInfo = true,
  showDarkModeToggle = true,
  showLogout = true,
  showBackButton = false,
  showNewGameButton = false,
  className = '' 
}) {
  const { user } = useAuth();

  return (
    <header className={`header ${className}`}>
      <div className="header__container">
        {/* Back button for game pages - positioned absolutely */}
        {showBackButton && onBackToMenu && (
          <button 
            className="header__back-button"
            onClick={onBackToMenu}
            title="Back to Menu"
          >
            ←
          </button>
        )}
        
        {showUserInfo && user && (
          <div className="header__user-info">
            <span className="header__welcome">Welcome back,</span>
            <span className="header__username">{user.username || 'Player'}</span>
          </div>
        )}
        
        {!showUserInfo && <div className="header__spacer"></div>}
        
        <div className="header__actions">
          {showNewGameButton && onNewGame && (
            <button 
              className="header__new-game-button"
              onClick={onNewGame}
              title="New Game"
            >
              New Game
            </button>
          )}
          
          {showLogout && onLogout && (
            <button 
              className="header__logout-button"
              onClick={onLogout}
              title="Logout"
            >
              Logout
            </button>
          )}
          
          {showDarkModeToggle && (
            <button 
              className="header__dark-mode-button"
              onClick={onToggleDarkMode}
              title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
              aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
            >
              🌙
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
