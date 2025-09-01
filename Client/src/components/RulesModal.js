/**
 * Rules Modal Component
 *
 * Displays comprehensive game rules for multiplayer Wordle including spell mechanics.
 * Non-transparent modal that works in both light and dark modes.
 */

import React from 'react';
import './RulesModal.css';

function RulesModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="rules-modal-overlay">
      <div className="rules-modal">
        <div className="rules-modal__header">
          <h2>Multiplayer Wordle Rules</h2>
          <button className="rules-modal__close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="rules-modal__content">
          <section className="rules-section">
            <h3>🎮 Basic Game Rules</h3>
            <ul>
              <li>Two players compete to guess the same secret 5-letter word first</li>
              <li>Each player has 6 attempts to guess the word</li>
              <li>The first player to guess the word correctly wins</li>
              <li>If both players exhaust their attempts without guessing, it's a draw</li>
              <li>Players take turns guessing simultaneously</li>
              <li><span className="color-hint green">Green</span>: Letter is correct and in the right position</li>
              <li><span className="color-hint yellow">Yellow</span>: Letter exists in the word but in wrong position</li>
              <li><span className="color-hint gray">Gray</span>: Letter does not exist in the word</li>
            </ul>
          </section>

        

          <section className="rules-section">
            <h3>✨ Spell System</h3>

            <div className="spell-card">
              <div className="spell-header">
                <span className="spell-name">FLASH</span>
                <span className="spell-cooldown">1 use per game</span>
              </div>
              <p>Whiten your opponent's screen for 3 seconds, temporarily blinding them and making it difficult to see their game board.</p>
            </div>

            <div className="spell-card">
              <div className="spell-header">
                <span className="spell-name">WRONG</span>
                <span className="spell-cooldown">1 use per game</span>
              </div>
              <p>Replace the next 5 letters your opponent types with random letters, causing confusion and potentially invalid guesses.</p>
            </div>

            <div className="spell-card">
              <div className="spell-header">
                <span className="spell-name">BLOCK</span>
                <span className="spell-cooldown">1 use per game</span>
              </div>
              <p>Disable your opponent's keyboard and virtual keyboard for 3 seconds, preventing them from typing or making guesses.</p>
            </div>
          </section>

          <section className="rules-section">
            <ul>
              <li>Spells are activated by typing the spell name as a guess</li>
              <li>Each spell can only be used once per game</li>
              <li>You can only cast spells when you haven't finished your attempts</li>
            </ul>
          </section>


        </div>
      </div>
    </div>
  );
}

export default RulesModal;
