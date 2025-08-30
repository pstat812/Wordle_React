/**
 * Dropdown Menu Component
 * 
 * A dropdown menu that appears from the top right corner with smooth animations.
 */

import React, { useState, useRef, useEffect } from 'react';
import InteractiveHoverButton from './InteractiveHoverButton';
import './DropdownMenu.css';

const DropdownMenu = ({ 
  options = [],
  disabled = false 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const toggleDropdown = () => {
    if (!disabled) {
      setIsOpen(!isOpen);
    }
  };

  const handleOptionClick = (option) => {
    setIsOpen(false);
    if (option.onClick) {
      option.onClick();
    }
  };

  return (
    <div className="dropdown-menu" ref={dropdownRef}>
      <InteractiveHoverButton
        variant="menu"
        onClick={toggleDropdown}
        disabled={disabled}
        className="dropdown-menu__trigger"
      >
        ⋯
      </InteractiveHoverButton>
      
      {isOpen && (
        <div className="dropdown-menu__content">
          <div className="dropdown-menu__arrow"></div>
          <div className="dropdown-menu__options">
            {options.map((option, index) => (
              <button
                key={option.id || index}
                className={`dropdown-menu__option ${option.className || ''}`}
                onClick={() => handleOptionClick(option)}
                disabled={option.disabled}
              >
                {option.icon && (
                  <span className="dropdown-menu__option-icon">
                    {option.icon}
                  </span>
                )}
                <span className="dropdown-menu__option-text">
                  {option.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DropdownMenu;
