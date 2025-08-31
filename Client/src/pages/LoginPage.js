/**
 * Login Page Component for User Authentication
 * 
 * interface for user authentication
 * 
 */

import React, { useState } from 'react';
import Header from '../components/Header';
import RegisterModal from '../components/RegisterModal';
import Alert from '../components/Alert';
import './LoginPage.css';

function LoginPage({ onLogin, showAlert, hideAlert, alert, isDarkMode, onToggleDarkMode }) {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [showRegisterModal, setShowRegisterModal] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.username.trim() || !formData.password) {
      showAlert('Please enter both username and password', 'warning');
      return;
    }

    setLoading(true);
    
    try {
      await onLogin(formData.username.trim(), formData.password);
    } catch (error) {
      showAlert(error.message || 'Login failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSuccess = () => {
    setShowRegisterModal(false);
    // Show success message
    setTimeout(() => {
      showAlert('Account created successfully! You can now log in.', 'success');
    }, 100);
  };

  const handleRegisterError = (error) => {
    showAlert(error, 'error');
  };

  return (
    <div className="login-page">
      {/* Alert System */}
      <Alert
        message={alert.message}
        type={alert.type}
        isVisible={alert.isVisible}
        onClose={hideAlert}
        autoCloseDelay={alert.autoCloseDelay}
      />
      
      <div className="login-page__container">
        <Header 
          isDarkMode={isDarkMode}
          onToggleDarkMode={onToggleDarkMode}
          showUserInfo={false}
          showLogout={false}
        />
        
        <main className="login-page__main">
          <div className="login-form">
            <form onSubmit={handleSubmit} className="login-form__form">
              <div className="login-form__field">
                <label htmlFor="username" className="login-form__label">
                  Username
                </label>
                <input
                  type="text"
                  id="username"
                  name="username"
                  value={formData.username}
                  onChange={handleInputChange}
                  className="login-form__input"
                  placeholder="Enter your username"
                  disabled={loading}
                  autoComplete="username"
                />
              </div>

              <div className="login-form__field">
                <label htmlFor="password" className="login-form__label">
                  Password
                </label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  className="login-form__input"
                  placeholder="Enter your password"
                  disabled={loading}
                  autoComplete="current-password"
                />
              </div>

              <button
                type="submit"
                className={`login-form__button login-form__button--login ${loading ? 'login-form__button--loading' : ''}`}
                disabled={loading || !formData.username.trim() || !formData.password}
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            <div className="login-form__divider">
            </div>

            <button
              type="button"
              className="login-form__button login-form__button--register"
              onClick={() => setShowRegisterModal(true)}
              disabled={loading}
            >
              Create Account
            </button>
          </div>
        </main>

        <footer className="login-page__footer">
        </footer>
      </div>

      {/* Registration Modal */}
      <RegisterModal
        isOpen={showRegisterModal}
        onClose={() => setShowRegisterModal(false)}
        onSuccess={handleRegisterSuccess}
        onError={handleRegisterError}
      />
    </div>
  );
}

export default LoginPage;
