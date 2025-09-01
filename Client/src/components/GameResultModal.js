/**
 * Game Result Modal Component
 * 
 * Modal popup that displays the multiplayer game results including
 * winner, target word, and navigation options.
 */

import React, { useEffect } from 'react';
import './GameResultModal.css';

function GameResultModal({ 
  isOpen, 
  onClose, 
  onBackToLobby,
  gameResult,
  targetWord,
  currentUser,
  isMultiplayer = false
}) {
  // Close modal on escape key (disabled in multiplayer mode)
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen && !isMultiplayer) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose, isMultiplayer]);

  const handleOverlayClick = (e) => {
    // Allow closing by clicking overlay (disabled in multiplayer mode)
    if (e.target === e.currentTarget && !isMultiplayer) {
      onClose();
    }
  };

  const handleBackToLobby = () => {
    onClose();
    onBackToLobby();
  };

  if (!isOpen) return null;

  // Determine result display
  const getResultDisplay = () => {
    if (!gameResult) return { title: 'Game Over', emoji: '🎮', className: 'neutral' };

    if (gameResult.game_status === 'draw') {
      return { title: 'Draw!', emoji: '🤝', className: 'draw' };
    }

    if (gameResult.game_status === 'finished' && gameResult.winner) {
      const isWinner = gameResult.winner === currentUser.id;
      return {
        title: isWinner ? 'You Won!' : 'You Lost',
        emoji: isWinner ? '🎉' : '😔',
        className: isWinner ? 'won' : 'lost'
      };
    }

    if (gameResult.game_status === 'abandoned') {
      return { title: 'Game Abandoned', emoji: '🚪', className: 'abandoned' };
    }

    return { title: 'Game Over', emoji: '🎮', className: 'neutral' };
  };

  const resultDisplay = getResultDisplay();

  return (
    <div className="game-result-modal__overlay" onClick={handleOverlayClick}>
      <div className="game-result-modal">
        <div className="game-result-modal__header">
          <div className={`game-result-modal__result game-result-modal__result--${resultDisplay.className}`}>
            <div className="game-result-modal__emoji">{resultDisplay.emoji}</div>
            <h2 className="game-result-modal__title">{resultDisplay.title}</h2>
          </div>
        </div>

        <div className="game-result-modal__content">
          {targetWord && (
            <div className="game-result-modal__word">
              <p className="game-result-modal__word-label">The word was:</p>
              <div className="game-result-modal__word-display">
                {targetWord.split('').map((letter, index) => (
                  <span key={index} className="game-result-modal__word-letter">
                    {letter}
                  </span>
                ))}
              </div>
            </div>
          )}


        </div>

        <div className="game-result-modal__actions">
          <button
            type="button"
            className="game-result-modal__button game-result-modal__button--lobby"
            onClick={handleBackToLobby}
          >
            Back to Lobby
          </button>
          {!isMultiplayer && (
            <button
              type="button"
              className="game-result-modal__button game-result-modal__button--close"
              onClick={onClose}
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default GameResultModal;
