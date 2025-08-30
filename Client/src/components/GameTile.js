/**
 * GameTile Component
 * 
 * Represents a single letter tile in the Wordle game board.
 * Handles different states: empty, typing, and evaluated (hit/present/miss).
 */

import React from 'react';
import { LETTER_STATUS } from '../useWordleGame';
import './GameTile.css';

const GameTile = ({ letter = "", status = LETTER_STATUS.UNUSED, isTyping = false }) => {
  const getClassName = () => {
    const baseClass = "game-tile";
    
    if (isTyping) {
      return `${baseClass} game-tile--typing`;
    }
    
    switch (status) {
      case LETTER_STATUS.HIT:
        return `${baseClass} game-tile--hit`;
      case LETTER_STATUS.PRESENT:
        return `${baseClass} game-tile--present`;
      case LETTER_STATUS.MISS:
        return `${baseClass} game-tile--miss`;
      default:
        return `${baseClass} game-tile--empty`;
    }
  };

  return (
    <div className={getClassName()}>
      {letter}
    </div>
  );
};

export default GameTile;
