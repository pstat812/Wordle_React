/**
 * Global Color Theme System
 * 
 * Centralized color definitions for consistent theming across the entire application.
 * This ensures all components use the same color palette for both light and dark modes.
 */

export const colors = {
  // Light Mode Colors
  light: {
    // Backgrounds
    primary: '#ffffff',
    secondary: '#f8fafc',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    
    // Component backgrounds
    card: 'rgba(255, 255, 255, 0.85)',
    cardHover: 'rgba(255, 255, 255, 0.95)',
    disabled: 'rgba(245, 245, 245, 0.7)',
    
    // Text colors
    text: '#333333',
    textSecondary: '#666666',
    textMuted: '#999999',
    textInverse: '#ffffff',
    
    // Button colors
    button: 'rgba(255, 255, 255, 0.15)',
    buttonHover: 'rgba(255, 255, 255, 0.25)',
    buttonBorder: 'rgba(255, 255, 255, 0.3)',
    buttonBorderHover: 'rgba(255, 255, 255, 0.5)',
    
    // Game specific
    gameButton: 'rgba(255, 255, 255, 0.9)',
    gameButtonHover: 'rgba(255, 255, 255, 1)',
    gameButtonBorder: 'rgba(0, 0, 0, 0.1)',
    gameButtonBorderHover: 'rgba(0, 0, 0, 0.2)',
    
    // Accent colors
    accent: '#667eea',
    accentHover: '#5a6fd8',
    
    // Borders and lines
    border: '#e1e5e9',
    line: '#e0e0e0',
    
    // Input colors
    input: '#ffffff',
    inputBorder: '#e1e5e9',
    inputFocus: '#667eea',
  },
  
  // Dark Mode Colors
  dark: {
    // Backgrounds
    primary: '#0f172a',
    secondary: '#1e293b',
    gradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    
    // Component backgrounds
    card: 'rgba(30, 41, 59, 0.85)',
    cardHover: 'rgba(30, 41, 59, 0.95)',
    disabled: 'rgba(30, 41, 59, 0.5)',
    
    // Text colors
    text: '#f1f5f9',
    textSecondary: '#cbd5e1',
    textMuted: 'rgba(241, 245, 249, 0.7)',
    textInverse: '#0f172a',
    
    // Button colors
    button: 'rgba(71, 85, 105, 0.3)',
    buttonHover: 'rgba(71, 85, 105, 0.5)',
    buttonBorder: 'rgba(71, 85, 105, 0.5)',
    buttonBorderHover: 'rgba(71, 85, 105, 0.7)',
    
    // Game specific
    gameButton: 'rgba(30, 41, 59, 0.9)',
    gameButtonHover: 'rgba(30, 41, 59, 1)',
    gameButtonBorder: 'rgba(241, 245, 249, 0.2)',
    gameButtonBorderHover: 'rgba(241, 245, 249, 0.3)',
    
    // Accent colors
    accent: '#60a5fa',
    accentHover: '#3b82f6',
    
    // Borders and lines
    border: 'rgba(241, 245, 249, 0.1)',
    line: '#334155',
    
    // Input colors
    input: '#1e293b',
    inputBorder: '#475569',
    inputFocus: '#60a5fa',
  }
};

/**
 * Get current theme colors based on dark mode state
 * @param {boolean} isDarkMode - Current dark mode state
 * @returns {object} Color object for current theme
 */
export const getThemeColors = (isDarkMode) => {
  return isDarkMode ? colors.dark : colors.light;
};

/**
 * Generate CSS custom properties for the current theme
 * @param {boolean} isDarkMode - Current dark mode state
 * @returns {object} CSS custom properties object
 */
export const getThemeCSSProperties = (isDarkMode) => {
  const themeColors = getThemeColors(isDarkMode);
  const cssProps = {};
  
  // Convert nested color object to CSS custom properties
  Object.keys(themeColors).forEach(key => {
    cssProps[`--color-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`] = themeColors[key];
  });
  
  return cssProps;
};

export default colors;
