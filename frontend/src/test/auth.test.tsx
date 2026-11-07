import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CustomerLogin } from '../components/auth/CustomerLogin';
import { DevLogin } from '../components/auth/DevLogin';
import { DeveloperDashboard } from '../components/dev/DeveloperDashboard';
import { AuthProvider } from '../context/AuthContext';
import * as api from '../services/api';

describe('Phase 11.6: Frontend Authentication & Role Authorization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -------------------------------------------------------------
  // 1. Customer Login Component Tests
  // -------------------------------------------------------------
  it('renders Customer Login form with accessible inputs and show/hide password toggle', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <CustomerLogin onNavigate={onNavigate} />
      </AuthProvider>
    );

    expect(screen.getByRole('button', { name: /Customer Sign In/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Work Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In to Workspace/i })).toBeInTheDocument();

    // Test Show/Hide password toggle
    const passwordInput = screen.getByLabelText('Password') as HTMLInputElement;
    expect(passwordInput.type).toBe('password');

    const toggleBtn = screen.getByRole('button', { name: /Show password/i });
    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe('text');

    fireEvent.click(screen.getByRole('button', { name: /Hide password/i }));
    expect(passwordInput.type).toBe('password');
  });

  it('does not expose built-in customer demo credentials', () => {
    const onNavigate = vi.fn();
    render(<AuthProvider initialUser={null}><CustomerLogin onNavigate={onNavigate} /></AuthProvider>);
    expect(screen.queryByRole('button', { name: /Pilot Customer Credentials/i })).not.toBeInTheDocument();
  });

  it('submits Customer login and navigates to customer workspace on success', async () => {
    const onNavigate = vi.fn();
    vi.spyOn(api, 'loginApi').mockResolvedValue({
      access_token: 'fake_cust_token',
      token_type: 'bearer',
      expires_in_seconds: 28800,
      user: {
        id: 'usr_cust_1',
        email: 'customer@processlens.com',
        name: 'Jane Doe',
        role: 'customer',
        created_at: '2026-01-01T00:00:00Z',
      },
    });

    render(
      <AuthProvider initialUser={null}>
        <CustomerLogin onNavigate={onNavigate} />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText(/Work Email/i), { target: { value: 'customer@processlens.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'ProcessLensCustomer2026!' } });
    fireEvent.click(screen.getByRole('button', { name: /Sign In to Workspace/i }));

    await waitFor(() => {
      expect(api.loginApi).toHaveBeenCalledWith({
        email: 'customer@processlens.com',
        password: 'ProcessLensCustomer2026!',
      });
      expect(onNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('displays generic error banner on login failure without leaking user existence', async () => {
    const onNavigate = vi.fn();
    vi.spyOn(api, 'loginApi').mockRejectedValue(new Error('Invalid email or password.'));

    render(
      <AuthProvider initialUser={null}>
        <CustomerLogin onNavigate={onNavigate} />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText(/Work Email/i), { target: { value: 'random@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'WrongPassword!' } });
    fireEvent.click(screen.getByRole('button', { name: /Sign In to Workspace/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/Invalid email or password/i);
    });
  });

  it('switches to registration tab and creates customer account with server-assigned role', async () => {
    const onNavigate = vi.fn();
    vi.spyOn(api, 'registerApi').mockResolvedValue({
      access_token: 'fake_reg_token',
      token_type: 'bearer',
      expires_in_seconds: 28800,
      user: {
        id: 'usr_cust_2',
        email: 'newuser@factory.co.uk',
        name: 'John Smith',
        role: 'customer',
        created_at: '2026-01-01T00:00:00Z',
      },
    });

    render(
      <AuthProvider initialUser={null}>
        <CustomerLogin onNavigate={onNavigate} />
      </AuthProvider>
    );

    // Switch to register tab
    fireEvent.click(screen.getByRole('button', { name: /Create Account/i }));

    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByText(/Account role will be assigned as/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Full Name/i), { target: { value: 'John Smith' } });
    fireEvent.change(screen.getByLabelText(/Work Email/i), { target: { value: 'newuser@factory.co.uk' } });
    fireEvent.change(screen.getByLabelText(/^Password/i), { target: { value: 'SecurePass2026!' } });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), { target: { value: 'SecurePass2026!' } });

    fireEvent.click(screen.getByRole('button', { name: /Create Customer Account/i }));

    await waitFor(() => {
      expect(api.registerApi).toHaveBeenCalledWith({
        name: 'John Smith',
        email: 'newuser@factory.co.uk',
        password: 'SecurePass2026!',
      });
      expect(onNavigate).toHaveBeenCalledWith('/');
    });
  });

  // -------------------------------------------------------------
  // 2. Developer Login Component Tests
  // -------------------------------------------------------------
  it('renders Developer Login with restricted access warning notice', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <DevLogin onNavigate={onNavigate} />
      </AuthProvider>
    );

    expect(screen.getByText(/ENGINEERING PORTAL/i)).toBeInTheDocument();
    expect(screen.getByText(/Developer & Ops Console/i)).toBeInTheDocument();
    expect(screen.getByText(/Restricted Access Environment/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Authorize Developer Console/i })).toBeInTheDocument();
  });

  it('displays access-denied card if an authenticated customer navigates to developer login', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider
        initialUser={{
          id: 'usr_cust_1',
          email: 'customer@processlens.com',
          name: 'Customer User',
          role: 'customer',
          created_at: '2026-01-01T00:00:00Z',
        }}
      >
        <DevLogin onNavigate={onNavigate} />
      </AuthProvider>
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Developer Privileges Required/i)).toBeInTheDocument();
    expect(screen.getByText(/customer@processlens.com/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Return to Customer Workspace/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Return to Customer Workspace/i }));
    expect(onNavigate).toHaveBeenCalledWith('/');
  });

  it('submits Developer login and navigates to developer dashboard on success', async () => {
    const onNavigate = vi.fn();
    vi.spyOn(api, 'loginApi').mockResolvedValue({
      access_token: 'fake_dev_token',
      token_type: 'bearer',
      expires_in_seconds: 28800,
      user: {
        id: 'usr_dev_1',
        email: 'dev@processlens.internal',
        name: 'System Developer',
        role: 'developer',
        created_at: '2026-01-01T00:00:00Z',
      },
    });

    render(
      <AuthProvider initialUser={null}>
        <DevLogin onNavigate={onNavigate} />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText(/Developer Identity/i), { target: { value: 'dev@processlens.internal' } });
    fireEvent.change(screen.getByLabelText(/Authorization Key \/ Password/i), { target: { value: 'unit-test-password' } });
    fireEvent.click(screen.getByRole('button', { name: /Authorize Developer Console/i }));

    await waitFor(() => {
      expect(api.loginApi).toHaveBeenCalledWith({
        email: 'dev@processlens.internal',
        password: 'unit-test-password',
      });
      expect(onNavigate).toHaveBeenCalledWith('/dev/dashboard');
    });
  });

  // -------------------------------------------------------------
  // 3. Developer Dashboard Component Tests
  // -------------------------------------------------------------
  it('renders Developer Dashboard with system telemetry, security specs, and audit log', async () => {
    const onNavigate = vi.fn();
    vi.spyOn(api, 'checkBackendHealth').mockResolvedValue({
      status: 'ok',
      service: 'processlens-backend',
      version: '0.1.0',
    });
    vi.spyOn(api, 'getDevStatusApi').mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      environment: 'development',
      python_version: '3.14.2',
      uptime_seconds: 142.5,
      cors_origins_configured: 5,
      llm_provider_configured: false,
      max_file_size_mb: 10,
    });
    vi.spyOn(api, 'getDevAuditEventsApi').mockResolvedValue({
      events: [
        {
          id: 'evt_1',
          timestamp: '2026-10-16T12:00:00Z',
          event_type: 'LOGIN_SUCCESS',
          email_masked: 'd***@processlens.internal',
          client_ip: '127.0.0.1',
          details: 'Role: developer',
        },
      ],
    });

    render(
      <AuthProvider
        initialUser={{
          id: 'usr_dev_1',
          email: 'dev@processlens.internal',
          name: 'Lead Developer',
          role: 'developer',
          created_at: '2026-01-01T00:00:00Z',
        }}
      >
        <DeveloperDashboard onNavigate={onNavigate} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/ProcessLens DevConsole/i)).toBeInTheDocument();
      expect(screen.getByText(/HEALTHY/i)).toBeInTheDocument();
      expect(screen.getByText(/v0.1.0/i)).toBeInTheDocument();
      expect(screen.getByText(/142.5s/i)).toBeInTheDocument();
      expect(screen.getByText(/10 MB/i)).toBeInTheDocument();
      expect(screen.getByText(/scrypt:32768:8:1/i)).toBeInTheDocument();
      expect(screen.getByText(/HMAC-SHA256 URLSafeTimedSerializer/i)).toBeInTheDocument();
      expect(screen.getByText(/d\*\*\*@processlens\.internal/i)).toBeInTheDocument();
    });

    // Test Customer View button
    fireEvent.click(screen.getByRole('button', { name: /Customer View/i }));
    expect(onNavigate).toHaveBeenCalledWith('/');
  });
});
