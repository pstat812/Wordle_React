/**
 * React Wordle Application Entry Point
 *
 * This file serves as the main entry point for the React Wordle application.
 * It handles React rendering and basic error boundaries.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root'));

try {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
} catch (error) {
  console.error('Failed to render React application:', error);
  document.body.innerHTML = `
    <div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      font-family: Arial, sans-serif;
      text-align: center;
      padding: 20px;
    ">
      <h1 style="color: #dc3545; margin-bottom: 20px;">Application Error</h1>
      <p style="color: #666; margin-bottom: 10px;">
        The Wordle application failed to start due to an unexpected error.
      </p>
      <p style="color: #666; font-size: 14px;">
        Please check your browser console for technical details.
      </p>
    </div>
  `;
}
