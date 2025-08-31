/**
 * Registration Modal Component
 * 
 * Modal popup for user registration with form validation
 * and clean, accessible design.
 */

import React, { useState, useEffect } from 'react';
import { registerUser } from '../apiService';
import './RegisterModal.css';

function RegisterModal({ isOpen, onClose, onSuccess, onError }) {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  // Reset form when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setFormData({ username: '', password: '', confirmPassword: '' });
      setErrors({});
      setLoading(false);
    }
  }, [isOpen]);

  // Close modal on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen && !loading) {
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
  }, [isOpen, loading, onClose]);

  const validateForm = () => {
    const newErrors = {};

    // Username validation
    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    } else if (formData.username.trim().length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username.trim())) {
      newErrors.username = 'Username can only contain letters, numbers, and underscores';
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }


    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    const newFormData = {
      ...formData,
      [name]: value
    };

    setFormData(newFormData);

    // Clear specific field error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) {
      return;
    }
    setLoading(true);
    
    try {
      const data = await registerUser(formData.username.trim(), formData.password);

      if (data.success) {
        onSuccess();
      } else {
        // Server returned an error message
        const errorMessage = data.error || data.message || 'Registration failed';

        onError(errorMessage);
      }
    } catch (error) {

      // The apiService will throw an error with the server's error message
      onError(error.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleOverlayClick = (e) => {
    // Prevent modal from closing when clicking on overlay
    // Only allow closing via the Cancel button
    e.preventDefault();
    e.stopPropagation();
  };

  if (!isOpen) return null;

  return (
    <div className="register-modal__overlay" onClick={handleOverlayClick}>
      <div className="register-modal">
        <div className="register-modal__header">
          <h2 className="register-modal__title">Create Account</h2>
        </div>

        <form             onSubmit={handleSubmit} className="register-modal__form">
          <div className="register-modal__field">
            <label htmlFor="register-username" className="register-modal__label">
              Username
            </label>
            <input
              type="text"
              id="register-username"
              name="username"
              value={formData.username}
              onChange={handleInputChange}
              className={`register-modal__input ${errors.username ? 'register-modal__input--error' : ''}`}
              placeholder="Enter a username"
              disabled={loading}
              autoComplete="username"
            />
            {errors.username && (
              <span className="register-modal__error">{errors.username}</span>
            )}
          </div>

          <div className="register-modal__field">
            <label htmlFor="register-password" className="register-modal__label">
              Password
            </label>
            <input
              type="password"
              id="register-password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              className={`register-modal__input ${errors.password ? 'register-modal__input--error' : ''}`}
              placeholder="Enter a password"
              disabled={loading}
              autoComplete="new-password"
            />
            {errors.password && (
              <span className="register-modal__error">{errors.password}</span>
            )}
          </div>

          <div className="register-modal__field">
            <label htmlFor="register-confirm-password" className="register-modal__label">
              Confirm Password
            </label>
            <input
              type="password"
              id="register-confirm-password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleInputChange}
              className={`register-modal__input ${errors.confirmPassword ? 'register-modal__input--error' : ''}`}
              placeholder="Confirm your password"
              disabled={loading}
              autoComplete="new-password"
            />
            {errors.confirmPassword && (
              <span className="register-modal__error">{errors.confirmPassword}</span>
            )}
          </div>

          <div className="register-modal__actions">
            <button
              type="button"
              className="register-modal__button register-modal__button--cancel"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={`register-modal__button register-modal__button--submit ${loading ? 'register-modal__button--loading' : ''}`}
              disabled={loading}
              onClick={async (e) => {
                e.preventDefault(); // Prevent default form submission
                await handleSubmit(e); // Call our handler directly
              }}
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RegisterModal;
