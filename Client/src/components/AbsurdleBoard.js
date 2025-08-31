/**
 * Absurdle Game Board Component
 * 
 * Dynamic game board that grows with each guess, starting with 1 row
 * and adding more as the player continues to guess.
 * Uses exact same rendering logic as GameBoard for consistency.
 */

import React from 'react';
import GameTile from './GameTile';
import { LETTER_STATUS } from '../hooks/useWordleGame';
import './GameBoard.css'; // Use the same CSS as regular GameBoard

function AbsurdleBoard({
  guesses = [],
  guessResults = [],
  currentInput = "",
  maxRounds = 1,
  gameOver = false
}) {
  const renderRow = (rowIndex) => {
    const tiles = [];
    
    // If this row has a completed guess
    if (rowIndex < guesses.length) {
      const guess = guesses[rowIndex];
      const results = guessResults[rowIndex];
      
      for (let colIndex = 0; colIndex < 5; colIndex++) {
        const letter = guess[colIndex] || "";
        const status = results[colIndex] ? results[colIndex][1] : LETTER_STATUS.UNUSED;
        
        tiles.push(
          <GameTile
            key={`${rowIndex}-${colIndex}`}
            letter={letter}
            status={status}
            isTyping={false}
          />
        );
      }
    }
    // If this is the current input row
    else if (rowIndex === guesses.length && !gameOver) {
      for (let colIndex = 0; colIndex < 5; colIndex++) {
        const letter = currentInput[colIndex] || "";
        const isTyping = letter !== "";
        
        tiles.push(
          <GameTile
            key={`${rowIndex}-${colIndex}`}
            letter={letter}
            status={LETTER_STATUS.UNUSED}
            isTyping={isTyping}
          />
        );
      }
    }
    // Empty rows
    else {
      for (let colIndex = 0; colIndex < 5; colIndex++) {
        tiles.push(
          <GameTile
            key={`${rowIndex}-${colIndex}`}
            letter=""
            status={LETTER_STATUS.UNUSED}
            isTyping={false}
          />
        );
      }
    }
    
    return (
      <div key={rowIndex} className="game-board__row">
        {tiles}
      </div>
    );
  };

  const rows = [];
  for (let i = 0; i < maxRounds; i++) {
    rows.push(renderRow(i));
  }

  return (
    <div className="game-board">
      {rows}
    </div>
  );
}

export default AbsurdleBoard;
