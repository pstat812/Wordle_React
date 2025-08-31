/**
 * Multiplayer Game Page Component
 * 
 * This component will handle the multiplayer game mode.
 * 
 */

import React from 'react';
import Header from '../components/Header';
import Alert from '../components/Alert';
import { useTheme } from '../hooks/useTheme';
import '../App.css';

function MultiplayerPage({ 
  isDarkMode, 
  onToggleDarkMode, 
  onBackToMenu,
  showAlert,
  hideAlert,
  alert
}) {
  // Get theme colors
  const theme = useTheme(isDarkMode);

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
        showUserInfo={false}
        showLogout={false}
        showBackButton={true}
        showNewGameButton={false}
        className="header--game"
      />

      <div className="app__container">


      </div>
    </div>
  );
}

export default MultiplayerPage;
