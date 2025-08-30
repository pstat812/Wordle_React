/**
 * Menu Page Component for Game Mode Selection
 * 
 * This component provides the main menu where users can select between
 * different game modes: Wordle, Absurdle, and Multiplayer.
 */

import React from 'react';
import './MenuPage.css';

function MenuPage({ onGameModeSelect }) {
  const gameModes = [
    {
      id: 'wordle',
      title: 'Wordle',
      description: 'Guess the 5-letter English word in limited attempts.',
      available: true
    },
    {
      id: 'absurdle',
      title: 'Absurdle',
      description: 'Adversarial version of Wordle. Find the correct word using as few attempts as you can.',
      available: true
    },
    {
      id: 'multiplayer',
      title: 'Multiplayer',
      description: 'Challenge friends in real-time. Coming soon!',
      available: false
    }
  ];

  return (
    <div className="menu-page">
      <div className="menu-page__container">
        <header className="menu-page__header">
          <h1 className="menu-page__title">Word Games</h1>
          <p className="menu-page__subtitle">Choose game mode</p>
        </header>

        <main className="menu-page__main">
          <div className="game-modes">
            {gameModes.map((mode) => (
              <div
                key={mode.id}
                className={`game-mode ${!mode.available ? 'game-mode--disabled' : ''}`}
                onClick={() => mode.available && onGameModeSelect(mode.id)}
              >
                <div className="game-mode__content">
                  <h2 className="game-mode__title">{mode.title}</h2>
                  <p className="game-mode__description">{mode.description}</p>
                  {!mode.available && (
                    <span className="game-mode__status">Coming Soon</span>
                  )}
                </div>
                {mode.available && (
                  <div className="game-mode__arrow">→</div>
                )}
              </div>
            ))}
          </div>
        </main>

        <footer className="menu-page__footer">
        </footer>
      </div>
    </div>
  );
}

export default MenuPage;
