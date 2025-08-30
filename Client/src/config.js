/**
 * Environment Configuration for Wordle Client
 * 
 * This module handles environment-specific configurations,
 * particularly API URL configuration for different deployment environments.
 */

// Environment detection
const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production';
const isTest = process.env.NODE_ENV === 'test';

// API Configuration based on environment
const getApiBaseUrl = () => {
  // Check for explicit environment variable first
  if (process.env.REACT_APP_API_BASE_URL) {
    return process.env.REACT_APP_API_BASE_URL;
  }
  
  // Fallback to environment-based defaults
  if (isDevelopment) {
    return 'http://127.0.0.1:5000/api';
  }
  
  if (isProduction) {
    // In production, you might want to use relative URLs or a different domain
    return '/api'; // Assumes API is served from same domain
  }
  
  if (isTest) {
    return 'http://localhost:5000/api';
  }
  
  // Ultimate fallback
  return 'http://127.0.0.1:5000/api';
};

// Export configuration object
export const config = {
  // API Configuration
  apiBaseUrl: getApiBaseUrl(),
  
  // Environment flags
  isDevelopment,
  isProduction,
  isTest,
  
  // Other configurable options
  requestTimeout: process.env.REACT_APP_REQUEST_TIMEOUT || 10000, // 10 seconds
  enableDebugLogging: isDevelopment || process.env.REACT_APP_DEBUG === 'true',
  
  // Feature flags (for future use)
  features: {
    darkMode: true,
    keyboardInput: true,
    animations: true,
  }
};

// Debug logging in development
if (config.enableDebugLogging) {
  console.log('🔧 Wordle Client Configuration:', {
    environment: process.env.NODE_ENV,
    apiBaseUrl: config.apiBaseUrl,
    isDevelopment: config.isDevelopment,
    isProduction: config.isProduction,
  });
}

export default config;
