import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ProcessLensLogo } from '../brand/ProcessLensLogo';
import { ThemeToggle } from '../ui/ThemeToggle';
import { Terminal, Lock, Mail, Eye, EyeOff, AlertTriangle, AlertCircle, ArrowRight, ShieldAlert, ArrowLeft } from 'lucide-react';

interface DevLoginProps {
  onNavigate: (path: string) => void;
}

export const DevLogin: React.FC<DevLoginProps> = ({ onNavigate }) => {
  const { login, logout, user, error: authError } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [customerDenied, setCustomerDenied] = useState(false);

  useEffect(() => {
    if (user && user.role !== 'developer') {
      setCustomerDenied(true);
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    setCustomerDenied(false);

    if (!email || !password) {
      setLocalError('Developer email and authentication key are required.');
      return;
    }

    setIsSubmitting(true);
    try {
      const authenticatedUser = await login({ email, password });
      if (authenticatedUser.role !== 'developer') {
        setCustomerDenied(true);
      } else {
        onNavigate('/dev/dashboard');
      }
    } catch {
      // Auth error handled by AuthContext
    } finally {
      setIsSubmitting(false);
    }
  };


  const handleReturnToCustomer = () => {
    onNavigate('/');
  };

  const handleSwitchAccount = async () => {
    await logout();
    setCustomerDenied(false);
    setEmail('');
    setPassword('');
  };

  return (
    <div className="pl-auth-page-container pl-dev-auth-page">
      <div className="pl-auth-top-bar">
        <ThemeToggle />
      </div>

      <div className="pl-auth-card-wrapper pl-dev-card-wrapper">
        <div className="pl-auth-brand-header">
          <ProcessLensLogo variant="full" size="lg" />
          <div className="pl-dev-badge-strip">
            <Terminal size={14} className="text-cyan" />
            <span className="dev-system-tag">ENGINEERING PORTAL</span>
            <span className="dev-title font-bold">Developer &amp; Ops Console</span>
          </div>
        </div>

        {/* Security Warning Notice */}
        <div className="pl-dev-notice-banner">
          <AlertTriangle size={16} className="text-amber" />
          <div className="pl-dev-notice-text">
            <strong>Restricted Access Environment:</strong>
            <p>
              Authorised engineering and platform operations only. Recent access attempts and client IPs
              are held in a limited in-memory audit log and do not survive server restarts.
            </p>
          </div>
        </div>

        {customerDenied ? (
          <div className="pl-auth-card pl-dev-denied-card" role="alert">
            <div className="pl-denied-icon-wrap">
              <ShieldAlert size={36} className="text-coral" />
            </div>
            <h2 className="pl-denied-title">Developer Privileges Required</h2>
            <p className="pl-denied-desc">
              Your session is authenticated as <strong>{user?.email}</strong> with role <code>{user?.role}</code>.
              Developer diagnostics, system telemetry, and audit logs are restricted to authorized engineering personnel.
            </p>
            <div className="pl-denied-actions">
              <button
                type="button"
                className="pl-btn pl-btn-primary pl-btn-block"
                onClick={handleReturnToCustomer}
              >
                <ArrowLeft size={15} />
                <span>Return to Customer Workspace</span>
              </button>
              <button
                type="button"
                className="pl-btn pl-btn-secondary pl-btn-block mt-2"
                onClick={handleSwitchAccount}
              >
                Sign Out &amp; Authenticate as Developer
              </button>
            </div>
          </div>
        ) : (
          <div className="pl-auth-card pl-dev-card">
            <div className="pl-dev-card-header">
              <h2 className="pl-dev-heading">Developer Authentication</h2>
              <span className="pl-dev-status-indicator">
                <span className="pl-status-ping" /> RBAC Enforced
              </span>
            </div>

            {(localError || authError) && (
              <div className="pl-auth-alert pl-auth-alert-error" role="alert">
                <AlertCircle size={16} />
                <span>{localError || authError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="pl-form" noValidate>
              <div className="pl-form-group">
                <label htmlFor="dev-email" className="pl-form-label">Developer Identity (Email)</label>
                <div className="pl-input-wrapper">
                  <Mail size={16} className="pl-input-icon" />
                  <input
                    id="dev-email"
                    type="email"
                    className="pl-input font-mono"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="dev@processlens.internal"
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div className="pl-form-group">
                <label htmlFor="dev-password" className="pl-form-label">Authorization Key / Password</label>
                <div className="pl-input-wrapper">
                  <Lock size={16} className="pl-input-icon" />
                  <input
                    id="dev-password"
                    type={showPassword ? 'text' : 'password'}
                    className="pl-input font-mono"
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
                    <span>Authorize Developer Console</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>

              <div className="pl-dev-back-link">
                <button
                  type="button"
                  className="pl-link-subtle"
                  onClick={() => onNavigate('/login')}
                >
                  &larr; Return to Customer Login
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
