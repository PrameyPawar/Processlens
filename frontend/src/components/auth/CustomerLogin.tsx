import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ProcessLensLogo } from '../brand/ProcessLensLogo';
import { ThemeToggle } from '../ui/ThemeToggle';
import { Eye, EyeOff, Lock, Mail, User, AlertCircle, ArrowRight } from 'lucide-react';

interface CustomerLoginProps {
  onNavigate: (path: string) => void;
}

export const CustomerLogin: React.FC<CustomerLoginProps> = ({ onNavigate }) => {
  const { login, register, error: authError, clearError } = useAuth();
  const [mode, setMode] = useState<'signin' | 'register'>('signin');

  // Form State
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleToggleMode = (newMode: 'signin' | 'register') => {
    setMode(newMode);
    setLocalError(null);
    clearError();
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (!email || !password) {
      setLocalError('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      const user = await login({ email, password });
      if (user.role === 'developer') {
        onNavigate('/dev/dashboard');
      } else {
        onNavigate('/');
      }
    } catch {
      // Error handled by AuthContext
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (!name || !email || !password) {
      setLocalError('All fields are required.');
      return;
    }
    if (password.length < 12) {
      setLocalError('Password must be at least 12 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register({ name, email, password });
      onNavigate('/');
    } catch {
      // Error handled by AuthContext
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <div className="pl-auth-page-container">
      {/* Top Bar with Navigation & Theme Toggle */}
      <div className="pl-auth-top-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          type="button"
          className="pl-btn-secondary-compact"
          onClick={() => onNavigate('/')}
          style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}
        >
          ← Back to Overview
        </button>
        <ThemeToggle />
      </div>

      <div className="pl-auth-card-wrapper">
        {/* Brand Header with ProcessLensLogo */}
        <div className="pl-auth-brand-header">
          <ProcessLensLogo variant="full" size="lg" showSubtitle />
          <p className="pl-auth-brand-sub">
            Operational Event Data → Evidence → Economics → Decision
          </p>
        </div>

        {/* Auth Card */}
        <div className="pl-auth-card">
          <div className="pl-auth-tabs">
            <button
              type="button"
              className={`pl-auth-tab ${mode === 'signin' ? 'is-active' : ''}`}
              onClick={() => handleToggleMode('signin')}
            >
              Customer Sign In
            </button>
            <button
              type="button"
              className={`pl-auth-tab ${mode === 'register' ? 'is-active' : ''}`}
              onClick={() => handleToggleMode('register')}
            >
              Create Account
            </button>
          </div>

          {/* Feedback Banners */}
          {(localError || authError) && (
            <div className="pl-auth-alert pl-auth-alert-error" role="alert">
              <AlertCircle size={16} />
              <span>{localError || authError}</span>
            </div>
          )}


          {/* SIGN IN FORM */}
          {mode === 'signin' && (
            <form onSubmit={handleSignIn} className="pl-form" noValidate>
              <div className="pl-form-group">
                <label htmlFor="customer-email" className="pl-form-label">Work Email</label>
                <div className="pl-input-wrapper">
                  <Mail size={16} className="pl-input-icon" />
                  <input
                    id="customer-email"
                    type="email"
                    className="pl-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div className="pl-form-group">
                <div className="pl-label-row">
                  <label htmlFor="customer-password" className="pl-form-label">Password</label>
                  <button
                    type="button"
                    className="pl-link-subtle"
                    onClick={() => setLocalError('Password recovery is unavailable in this portfolio demo. Contact the account administrator to reset access.')}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="pl-input-wrapper">
                  <Lock size={16} className="pl-input-icon" />
                  <input
                    id="customer-password"
                    type={showPassword ? 'text' : 'password'}
                    className="pl-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="pl-input-eye-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="pl-btn pl-btn-primary pl-btn-block pl-btn-lg"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <span className="pl-btn-spinner" />
                ) : (
                  <>
                    <span>Sign In to Workspace</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>

            </form>
          )}

          {/* REGISTER FORM */}
          {mode === 'register' && (
            <form onSubmit={handleRegister} className="pl-form" noValidate>
              <div className="pl-auth-sub-desc">
                Account role will be assigned as <strong>customer</strong>. Developer accounts are restricted.
              </div>

              <div className="pl-form-group">
                <label htmlFor="reg-name" className="pl-form-label">Full Name</label>
                <div className="pl-input-wrapper">
                  <User size={16} className="pl-input-icon" />
                  <input
                    id="reg-name"
                    type="text"
                    className="pl-input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Jane Doe"
                    required
                  />
                </div>
              </div>

              <div className="pl-form-group">
                <label htmlFor="reg-email" className="pl-form-label">Work Email</label>
                <div className="pl-input-wrapper">
                  <Mail size={16} className="pl-input-icon" />
                  <input
                    id="reg-email"
                    type="email"
                    className="pl-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane@manufacturing.com"
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div className="pl-form-group">
                <label htmlFor="reg-password" className="pl-form-label">Password (Min 12 Characters)</label>
                <div className="pl-input-wrapper">
                  <Lock size={16} className="pl-input-icon" />
                  <input
                    id="reg-password"
                    type={showPassword ? 'text' : 'password'}
                    className="pl-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="pl-input-eye-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              <div className="pl-form-group">
                <label htmlFor="reg-confirm" className="pl-form-label">Confirm Password</label>
                <div className="pl-input-wrapper">
                  <Lock size={16} className="pl-input-icon" />
                  <input
                    id="reg-confirm"
                    type={showPassword ? 'text' : 'password'}
                    className="pl-input"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="pl-btn pl-btn-primary pl-btn-block pl-btn-lg"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <span className="pl-btn-spinner" />
                ) : (
                  <>
                    <span>Create Customer Account</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Developer Portal Quick Link */}
          <div className="pl-auth-footer-links">
            <span className="text-muted text-xs">Internal engineering access?</span>
            <button
              type="button"
              className="pl-link-dev"
              onClick={() => onNavigate('/dev/login')}
            >
              Developer Console &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
