/**
 * Spell Panel Component
 *
 * Displays available spells for multiplayer mode with usage tracking.
 * Shows spell buttons, cooldown status, and handles spell activation.
 */

import React from 'react';
import './SpellPanel.css';

function SpellPanel({ spells, onSpellCast, isDisabled }) {
  const handleSpellClick = (spellName) => {
    if (isDisabled || spells[spellName]?.used) return;
    onSpellCast(spellName);
  };

  const getSpellIcon = (spellName) => {
    switch (spellName) {
      case 'FLASH': return '⚡';
      case 'WRONG': return '🎭';
      case 'BLOCK': return '🚫';
      default: return '✨';
    }
  };

  const getSpellDescription = (spellName) => {
    switch (spellName) {
      case 'FLASH': return 'Blind opponent for 3s';
      case 'WRONG': return 'Replace next 5 letters';
      case 'BLOCK': return 'Disable keyboard for 3s';
      default: return '';
    }
  };

  return (
    <div className="spell-panel">
      <div className="spell-panel__header">
        <h3>🪄 Spells</h3>
        <span className="spell-panel__subtitle">Use once per game</span>
      </div>

      <div className="spell-panel__spells">
        {Object.entries(spells).map(([spellName, spellData]) => (
          <button
            key={spellName}
            className={`spell-btn ${spellData.used ? 'spell-btn--used' : ''} ${isDisabled ? 'spell-btn--disabled' : ''}`}
            onClick={() => handleSpellClick(spellName)}
            disabled={isDisabled || spellData.used}
            title={spellData.used ? 'Already used this game' : getSpellDescription(spellName)}
          >
            <div className="spell-btn__icon">
              {getSpellIcon(spellName)}
            </div>
            <div className="spell-btn__name">
              {spellName}
            </div>
            <div className="spell-btn__status">
              {spellData.used ? '✅ Used' : '⚪ Ready'}
            </div>
          </button>
        ))}
      </div>

      <div className="spell-panel__instructions">
        <p>Type the spell name as your guess to cast it!</p>
      </div>
    </div>
  );
}

export default SpellPanel;
