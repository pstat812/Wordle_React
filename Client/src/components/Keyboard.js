/**
 * Keyboard Component
 * 
 * Virtual on-screen keyboard for letter input.
 * Shows letter status colors based on game state.
 */

import React from 'react';
import { LETTER_STATUS } from '../useWordleGame';
import './Keyboard.css';

const Keyboard = ({ 
  letterStatus = {}, 
  onLetterClick, 
  onEnterClick, 
  onBackspaceClick,
  gameOver = false 
}) => {
  const keyboardRows = [
    "QWERTYUIOP",
    "ASDFGHJKL",
    "ZXCVBNM"
  ];

  const getKeyClassName = (letter) => {
    const baseClass = "keyboard__key";
    const status = letterStatus[letter] || LETTER_STATUS.UNUSED;
    
    switch (status) {
      case LETTER_STATUS.HIT:
        return `${baseClass} keyboard__key--hit`;
      case LETTER_STATUS.PRESENT:
        return `${baseClass} keyboard__key--present`;
      case LETTER_STATUS.MISS:
        return `${baseClass} keyboard__key--miss`;
      default:
        return `${baseClass} keyboard__key--unused`;
    }
  };

  const handleKeyClick = (letter) => {
    if (!gameOver && onLetterClick) {
      onLetterClick(letter);
    }
  };

  const handleEnterClick = () => {
    if (!gameOver && onEnterClick) {
      onEnterClick();
    }
  };

  const handleBackspaceClick = () => {
    if (!gameOver && onBackspaceClick) {
      onBackspaceClick();
    }
  };

  return (
    <div className="keyboard">
      {keyboardRows.map((row, rowIndex) => (
        <div key={rowIndex} className="keyboard__row">
          {/* Add ENTER button to the last row (start) */}
          {rowIndex === 2 && (
            <button
              className="keyboard__key keyboard__key--special"
              onClick={handleEnterClick}
              disabled={gameOver}
            >
              ENTER
            </button>
          )}
          
          {/* Letter keys */}
          {Array.from(row).map((letter) => (
            <button
              key={letter}
              className={getKeyClassName(letter)}
              onClick={() => handleKeyClick(letter)}
              disabled={gameOver}
            >
              {letter}
            </button>
          ))}
          
          {/* Add BACKSPACE button to the last row (end) */}
          {rowIndex === 2 && (
            <button
              className="keyboard__key keyboard__key--special"
              onClick={handleBackspaceClick}
              disabled={gameOver}
            >
              DEL
            </button>
          )}
        </div>
      ))}
    </div>
  );
};

export default Keyboard;
