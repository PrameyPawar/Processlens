import React from 'react';
import { HealthStatus } from './HealthStatus';
import { ProcessLensLogo } from './brand/ProcessLensLogo';
import { ThemeToggle } from './ui/ThemeToggle';
import { FileUp, LogOut, Terminal, User as UserIcon, ShieldCheck, Database } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { DataQualityReport } from '../types/api';

interface HeaderProps {
  hasActiveData: boolean;
  onReset: () => void;
  onNavigate?: (path: string) => void;
  datasetName?: string;
  dataQualityReport?: DataQualityReport | null;
  onOpenQuality?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  hasActiveData,
  onReset,
  onNavigate,
  datasetName,
  dataQualityReport,
  onOpenQuality,
}) => {
  const { user, role, logout } = useAuth();

  const handleSignOut = async () => {
    onReset();
    await logout();
    if (onNavigate) {
      onNavigate('/login');
    }
  };

  const validPct = dataQualityReport && dataQualityReport.total_rows > 0
    ? (dataQualityReport.valid_rows / dataQualityReport.total_rows) * 100
    : null;

  return (
    <header className="pl-app-header">
      <div className="pl-header-container">
        {/* Left: Brand Identity */}
        <div className="pl-header-brand-group">
          <ProcessLensLogo
            variant="compact"
            size="sm"
            onClick={() => onNavigate && onNavigate('/')}
          />
          <span className="pl-header-subtitle">
            Operational Event Data → Evidence → Economics → SME Process Intelligence &amp; Automation Decision Support
          </span>
        </div>

        {/* Center/Context: Active Dataset & Telemetry Status */}
        {hasActiveData && datasetName && (
          <div className="pl-header-context-group">
            <div className="pl-dataset-pill" title={`Active operational dataset: ${datasetName}`}>
              <Database size={13} className="text-cyan" />
              <span className="pl-dataset-name font-mono">{datasetName}</span>
              {validPct !== null && (
                <button
                  type="button"
                  className={`pl-quality-badge ${validPct === 100 ? 'quality-good' : 'quality-warn'}`}
                  onClick={onOpenQuality}
                  title="Inspect Schema & Telemetry Data Quality Audit"
                  aria-label={`Data Quality: ${validPct.toFixed(1)}% valid rows`}
                >
                  <ShieldCheck size={12} />
                  <span>{validPct.toFixed(1)}% Valid</span>
                </button>
              )}
            </div>

            <button
              type="button"
              className="pl-btn-secondary-compact"
              onClick={onReset}
              title="Upload another CSV event log"
            >
              <FileUp size={13} />
              <span>Upload Another Dataset</span>
            </button>
          </div>
        )}

        {/* Right: Controls, System Health, Theme Toggle & Account */}
        <div className="pl-header-actions-group">
          <HealthStatus />

          <ThemeToggle />

          {user && (
            <div className="pl-user-menu">
              <div className="pl-user-info" title={`Authenticated as ${user.email}`}>
                <UserIcon size={13} className="text-muted" />
                <span className="pl-user-email">{user.email}</span>
                <span className={`pl-role-tag ${role === 'developer' ? 'role-dev' : 'role-customer'}`}>
                  {role === 'developer' ? 'DEV' : 'CLIENT'}
                </span>
              </div>

              {role === 'developer' && onNavigate && (
                <button
                  type="button"
                  className="pl-btn-dev-quick"
                  onClick={() => onNavigate('/dev/dashboard')}
                  title="Open Developer Diagnostic Console"
                >
                  <Terminal size={13} />
                  <span>Dev Console</span>
                </button>
              )}

              <button
                type="button"
                className="pl-btn-signout"
                onClick={handleSignOut}
                title="Sign out of ProcessLens session"
                aria-label="Sign Out"
              >
                <LogOut size={13} />
                <span className="signout-label">Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
