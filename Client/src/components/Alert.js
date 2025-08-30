/**
 * Alert Component - Reusable notification system
 *
 * A fixed-position alert component that displays messages at the top of the screen.
 * Supports different alert types, auto-dismiss functionality, and is fully responsive.
 * 
 * Usage:
 * <Alert
 *   message="Hello World!"
 *   type="success" 
 *   isVisible={true}
 *   onClose={handleClose}
 * />
 *
 * Alert Types:
 * - 'error' - Red background with ❌ icon
 * - 'warning' - Yellow background with ⚠️ icon  
 * - 'success' - Green background with ✅ icon
 * - 'info' - Blue background with ℹ️ icon (default)
 *
 * Props:
 * - message: string - Alert message to display
 * - type: string - Alert type ('error', 'warning', 'info', 'success')
 * - isVisible: boolean - Whether the alert is visible
 * - onClose: function - Callback when alert is closed
 * - autoCloseDelay: number - Auto-close delay in ms (0 = no auto-close)
 * - showCloseButton: boolean - Whether to show close button
 */

import React, { useEffect } from 'react';
import './Alert.css';

/**
 * Alert component for displaying notifications
 * @param {object} props - Component props
 * @param {string} props.message - Alert message to display
 * @param {string} props.type - Alert type ('error', 'warning', 'info', 'success')
 * @param {boolean} props.isVisible - Whether the alert is visible
 * @param {function} props.onClose - Callback when alert is closed
 * @param {number} props.autoCloseDelay - Auto-close delay in milliseconds (0 = no auto-close)
 * @param {boolean} props.showCloseButton - Whether to show close button
 */
function Alert({ 
  message, 
  type = 'info', 
  isVisible = false, 
  onClose, 
  autoCloseDelay = 3000,
  showCloseButton = true 
}) {
  // Auto-close functionality
  useEffect(() => {
    if (isVisible && autoCloseDelay > 0) {
      const timer = setTimeout(() => {
        if (onClose) {
          onClose();
        }
      }, autoCloseDelay);

      return () => clearTimeout(timer);
    }
  }, [isVisible, autoCloseDelay, onClose]);

  if (!isVisible || !message) {
    return null;
  }

  const getAlertIcon = () => {
    switch (type) {
      case 'error':
        return '❌';
      case 'warning':
        return '⚠️';
      case 'success':
        return '✅';
      case 'info':
      default:
        return 'ℹ️';
    }
  };

  return (
    <div className={`alert alert--${type} ${isVisible ? 'alert--visible' : ''}`}>
      <div className="alert__content">
        <span className="alert__icon">{getAlertIcon()}</span>
        <span className="alert__message">{message}</span>
        {showCloseButton && (
          <button 
            className="alert__close"
            onClick={onClose}
            aria-label="Close alert"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}

export default Alert;
