/**
 * SettingsModal Component
 * 
 * Modal dialog for configuring game settings like dark mode.
 */

import React from 'react';
import './SettingsModal.css';

const SettingsModal = ({ 
  isOpen, 
  onClose, 
  isDarkMode, 
  onToggleDarkMode 
}) => {

  const handleToggleDarkMode = () => {
    onToggleDarkMode(!isDarkMode);
  };

  const handleClose = () => {
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="settings-modal__overlay" onClick={handleClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-modal__header">
          <h2>Game Settings</h2>
          <button 
            className="settings-modal__close"
            onClick={handleClose}
          >
            ×
          </button>
        </div>
        
        <div className="settings-modal__content">
          <div className="settings-modal__field">
            <label htmlFor="darkMode">Dark Mode:</label>
            <div className="settings-modal__switch-container">
              <label className="settings-modal__switch">
                <input
                  id="darkMode"
                  type="checkbox"
                  checked={isDarkMode}
                  onChange={handleToggleDarkMode}
                />
                <span className="settings-modal__slider"></span>
              </label>
              <span className="settings-modal__switch-label">
                {isDarkMode ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
