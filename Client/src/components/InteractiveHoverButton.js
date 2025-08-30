/**
 * Interactive Hover Button Component
 * 
 * A visually engaging button component that responds to hover with dynamic transitions,
 * adapting smoothly between light and dark modes for enhanced user interactivity.
 */

import React from 'react';
import './InteractiveHoverButton.css';

const InteractiveHoverButton = ({ 
  children, 
  onClick, 
  className = '',
  variant = 'primary',
  disabled = false,
  ...props 
}) => {
  const getButtonClassName = () => {
    const baseClass = 'interactive-hover-button';
    const variantClass = `${baseClass}--${variant}`;
    const disabledClass = disabled ? `${baseClass}--disabled` : '';
    
    return `${baseClass} ${variantClass} ${disabledClass} ${className}`.trim();
  };

  return (
    <button
      className={getButtonClassName()}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      <span className="interactive-hover-button__content">
        {children}
      </span>
      <div className="interactive-hover-button__hover-effect"></div>
    </button>
  );
};

export default InteractiveHoverButton;
