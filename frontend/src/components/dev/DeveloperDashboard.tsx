import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getDevStatusApi, getDevAuditEventsApi, checkBackendHealth } from '../../services/api';
import { DevStatusResponse, AuditEvent } from '../../types/api';
import { ProcessLensLogo } from '../brand/ProcessLensLogo';
import { ThemeToggle } from '../ui/ThemeToggle';
import {
  Terminal,
  Activity,
  Shield,
  Clock,
  Server,
  LogOut,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  HardDrive,
  Key,
} from 'lucide-react';

interface DeveloperDashboardProps {
  onNavigate: (path: string) => void;
}

export const DeveloperDashboard: React.FC<DeveloperDashboardProps> = ({ onNavigate }) => {
  const { user, role, logout } = useAuth();
  const [devStatus, setDevStatus] = useState<DevStatusResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [healthStatus, setHealthStatus] = useState<string>('checking');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDiagnostics = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [health, status, eventsResp] = await Promise.all([
        checkBackendHealth().catch(() => ({ status: 'unavailable', service: 'unknown', version: 'unknown' })),
        getDevStatusApi(),
        getDevAuditEventsApi(),
      ]);
      setHealthStatus(health.status);
      setDevStatus(status);
      setAuditEvents(eventsResp.events || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load developer telemetry.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (role === 'developer') {
      fetchDiagnostics();
    }
  }, [role]);

  const handleLogout = async () => {
    await logout();
    onNavigate('/dev/login');
  };

  // ACCESS DENIED IF NOT DEVELOPER
  if (role !== 'developer') {
    return (
      <div className="pl-auth-page-container">
        <div className="pl-auth-card-wrapper">
          <div className="pl-auth-card pl-dev-denied-card" role="alert">
            <div className="pl-denied-icon-wrap">
              <ShieldAlert size={36} className="text-coral" />
            </div>
            <h2 className="pl-denied-title">Unauthorized Access</h2>
            <p className="pl-denied-desc">
              You must be authenticated with developer privileges to access the engineering dashboard.
            </p>
            <div className="pl-denied-actions">
              <button
                type="button"
                className="pl-btn pl-btn-primary pl-btn-block"
                onClick={() => onNavigate('/')}
              >
                <ArrowLeft size={15} />
                <span>Return to Customer Workspace</span>
              </button>
              <button
                type="button"
                className="pl-btn pl-btn-secondary pl-btn-block mt-2"
                onClick={() => onNavigate('/dev/login')}
              >
                Developer Sign In
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isHealthy = healthStatus === 'ok' || healthStatus === 'healthy';

  return (
    <div className="pl-dev-dashboard-view">
      {/* Top Console Navigation Bar */}
      <header className="pl-app-header">
        <div className="pl-header-container">
          <div className="pl-header-brand-group">
            <ProcessLensLogo variant="compact" size="sm" onClick={() => onNavigate('/')} />
            <div className="pl-dev-badge-strip">
              <Terminal size={13} className="text-cyan" />
              <span className="dev-brand-title">ProcessLens DevConsole</span>
              <span className="pl-env-pill">{devStatus?.environment?.toUpperCase() || 'DEVELOPMENT'}</span>
            </div>
          </div>

          <div className="pl-header-actions-group">
            <ThemeToggle />

            <div className="pl-user-menu">
              <div className="pl-user-info">
                <span className="pl-status-dot-active" />
                <span className="pl-user-email">{user?.email}</span>
                <span className="pl-role-tag role-dev">DEVELOPER</span>
              </div>

              <button
                type="button"
                className="pl-btn-secondary-compact"
                onClick={() => onNavigate('/')}
                title="Inspect Customer Workspace View"
              >
                <ExternalLink size={13} />
                <span>Customer View</span>
              </button>

              <button
                type="button"
                className="pl-btn-secondary-compact"
                onClick={fetchDiagnostics}
                disabled={isLoading}
                title="Refresh Telemetry"
              >
                <RefreshCw size={13} className={isLoading ? 'spinning' : ''} />
                <span>Refresh</span>
              </button>

              <button
                type="button"
                className="pl-btn-signout"
                onClick={handleLogout}
                title="Log Out Developer Session"
              >
                <LogOut size={13} />
                <span className="signout-label">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Developer Workspace */}
      <main className="pl-dev-content-container">
        {error && (
          <div className="pl-auth-alert pl-auth-alert-error mb-4" role="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        {/* Console Header Banner */}
        <div className="pl-dev-banner">
          <div>
            <h1 className="pl-dev-banner-title">Engineering Diagnostics &amp; Operational Telemetry</h1>
            <p className="pl-dev-banner-sub">
              Deterministic runtime health, token revocation metrics, and transactional security audit trail.
            </p>
          </div>
          <div className="pl-dev-health-indicator">
            <span className={`pl-health-dot ${isHealthy ? 'healthy' : 'unhealthy'}`} />
            <span>
              Backend Health: <strong className="font-mono">{isHealthy ? 'HEALTHY' : 'DEGRADED'}</strong>
            </span>
          </div>
        </div>

        {/* Telemetry Metric Cards */}
        <div className="pl-metrics-grid mb-6">
          <div className="pl-metric-card pl-metric-cyan">
            <div className="pl-metric-header">
              <div className="pl-metric-label-group">
                <Server size={14} className="text-cyan" />
                <span className="pl-metric-label">Server Version</span>
              </div>
            </div>
            <div className="pl-metric-body font-mono">
              <span className="pl-metric-value">v{devStatus?.version || '0.1.0'}</span>
            </div>
            <div className="pl-metric-caption">Python {devStatus?.python_version || '3.14.2'}</div>
          </div>

          <div className="pl-metric-card pl-metric-teal">
            <div className="pl-metric-header">
              <div className="pl-metric-label-group">
                <Clock size={14} className="text-teal" />
                <span className="pl-metric-label">Server Uptime</span>
              </div>
            </div>
            <div className="pl-metric-body font-mono">
              <span className="pl-metric-value">{devStatus?.uptime_seconds ?? 0}s</span>
            </div>
            <div className="pl-metric-caption">Elapsed server process lifetime</div>
          </div>

          <div className="pl-metric-card pl-metric-amber">
            <div className="pl-metric-header">
              <div className="pl-metric-label-group">
                <HardDrive size={14} className="text-amber" />
                <span className="pl-metric-label">Ingestion File Limit</span>
              </div>
            </div>
            <div className="pl-metric-body font-mono">
              <span className="pl-metric-value">{devStatus?.max_file_size_mb || 10} MB</span>
            </div>
            <div className="pl-metric-caption">Max upload payload size</div>
          </div>

          <div className="pl-metric-card pl-metric-purple">
            <div className="pl-metric-header">
              <div className="pl-metric-label-group">
                <Shield size={14} className="text-purple" />
                <span className="pl-metric-label">CORS Origins</span>
              </div>
            </div>
            <div className="pl-metric-body font-mono">
              <span className="pl-metric-value">{devStatus?.cors_origins_configured ?? 1}</span>
            </div>
            <div className="pl-metric-caption">Strict origin whitelist configured</div>
          </div>
        </div>

        {/* Security & Authentication Cryptographic Architecture Specifications */}
        <div className="pl-dev-panel mb-6">
          <div className="pl-dev-panel-header">
            <div className="pl-dev-panel-title">
              <Key size={16} className="text-cyan" />
              <span>Cryptographic &amp; Authentication Architecture</span>
            </div>
          </div>
          <div className="pl-specs-grid">
            <div className="pl-spec-item">
              <span className="pl-spec-label">Password Hashing Algorithm:</span>
              <code className="pl-spec-code">scrypt:32768:8:1</code>
            </div>
            <div className="pl-spec-item">
              <span className="pl-spec-label">Session Token Transport:</span>
              <code className="pl-spec-code">HMAC-SHA256 URLSafeTimedSerializer</code>
            </div>
            <div className="pl-spec-item">
              <span className="pl-spec-label">Session Cookie Security:</span>
              <code className="pl-spec-code">HttpOnly; SameSite=Lax; Secure in Prod</code>
            </div>
            <div className="pl-spec-item">
              <span className="pl-spec-label">Cross-Origin Abuse Defense:</span>
              <code className="pl-spec-code">CSRF Origin Verification for Cookie POSTs</code>
            </div>
          </div>
        </div>

        {/* Security Audit Events Table */}
        <div className="pl-dev-panel">
          <div className="pl-dev-panel-header">
            <div className="pl-dev-panel-title">
              <Activity size={16} className="text-cyan" />
              <span>Authentication &amp; Security Audit Log</span>
            </div>
            <span className="text-xs text-muted font-mono">{auditEvents.length} recorded events</span>
          </div>

          <div className="pl-table-wrapper">
            <table className="pl-table" aria-label="Security Audit Log">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action / Event</th>
                  <th>Identity / Masked Email</th>
                  <th>Client IP</th>
                  <th>Details</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-6 text-muted">
                      No security audit events recorded in current server runtime window.
                    </td>
                  </tr>
                ) : (
                  auditEvents.map((evt) => (
                    <tr key={evt.id}>
                      <td className="font-mono text-xs">{evt.timestamp}</td>
                      <td>
                        <span className="pl-action-tag font-mono">{evt.event_type}</span>
                      </td>
                      <td className="font-mono text-xs">{evt.email_masked}</td>
                      <td className="font-mono text-xs">{evt.client_ip}</td>
                      <td className="text-xs">{evt.details || '—'}</td>
                      <td>
                        <span className="pl-badge pl-badge-teal pl-badge-sm">
                          <CheckCircle2 size={11} className="mr-1 inline" /> VERIFIED
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
};
