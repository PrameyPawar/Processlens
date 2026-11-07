import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { MarketingLandingPage } from '../components/marketing/MarketingLandingPage';
import { AuthProvider } from '../context/AuthContext';

describe('Phase 11.10: ProcessLens Premium Marketing Landing Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. Renders Hero section with distinctive editorial headline and brand eyebrow', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    expect(screen.getByText('OPERATIONS INTELLIGENCE')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Find the friction/i);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Fix what matters/i);
    expect(
      screen.getByText(/ProcessLens turns operational event data into a clear, evidence-backed picture/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/No invented metrics/i)).toBeInTheDocument();
  });

  it('2. Renders floating navigation bar with working links and Sign In action', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    const nav = screen.getByRole('navigation', { name: /Main Navigation/i });
    expect(nav).toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: 'Product' })).toHaveAttribute('href', '#product-preview');
    expect(within(nav).getByRole('link', { name: 'How It Works' })).toHaveAttribute('href', '#how-it-works');
    expect(within(nav).getByRole('link', { name: 'Use Cases' })).toHaveAttribute('href', '#use-cases');
    expect(within(nav).getByRole('link', { name: 'Trust & Evidence' })).toHaveAttribute('href', '#trust-evidence');

    const signInBtn = within(nav).getByRole('button', { name: /Sign In/i });
    fireEvent.click(signInBtn);
    expect(onNavigate).toHaveBeenCalledWith('/login');
  });

  it('3. Renders Interactive Product Preview with honest KPI metrics and tab switching', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    // KPI Summary Ribbon
    expect(screen.getByText('750')).toBeInTheDocument();
    expect(screen.getByText('100.0%')).toBeInTheDocument();
    expect(screen.getByText('36.9h')).toBeInTheDocument();
    expect(screen.getByText('53.3h')).toBeInTheDocument();

    // Default Tab: Recommended Investigation
    expect(screen.getByText(/Rank #1 Priority Opportunity/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Quote Received → PO Released/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Transparent Economics:/i)).toBeInTheDocument();

    // Switch to Detected Bottlenecks Tab
    const bottlenecksTab = screen.getByRole('tab', { name: /Detected Bottlenecks & Signals/i });
    fireEvent.click(bottlenecksTab);
    expect(screen.getByText(/Identified Process Bottlenecks/i)).toBeInTheDocument();
    expect(screen.getByText(/Standard Production Path/i)).toBeInTheDocument();

    // Switch to Evidence Dossier Tab
    const evidenceTab = screen.getByRole('tab', { name: /Epistemic Evidence Dossier/i });
    fireEvent.click(evidenceTab);
    expect(screen.getByText(/Epistemic Ledger \(Grounding Audit\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Verifiable Derivation/i)).toBeInTheDocument();
  });

  it('4. Renders Problem section with 3 distinct operational reality cards', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    expect(screen.getByRole('heading', { name: /Work rarely breaks in just one place/i })).toBeInTheDocument();
    expect(screen.getByText(/See the bottlenecks/i)).toBeInTheDocument();
    expect(screen.getByText(/Find the underlying signals/i)).toBeInTheDocument();
    expect(screen.getByText(/Prioritise the next move/i)).toBeInTheDocument();
  });

  it('5. Renders 4-step deterministic pipeline in How It Works', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    expect(screen.getByText(/STEP 01/i)).toBeInTheDocument();
    expect(screen.getByText(/Bring your data/i)).toBeInTheDocument();
    expect(screen.getByText(/STEP 02/i)).toBeInTheDocument();
    expect(screen.getByText(/Reconstruct the process/i)).toBeInTheDocument();
    expect(screen.getByText(/STEP 03/i)).toBeInTheDocument();
    expect(screen.getByText(/Surface findings/i)).toBeInTheDocument();
    expect(screen.getByText(/STEP 04/i)).toBeInTheDocument();
    expect(screen.getByText(/Prioritise with evidence/i)).toBeInTheDocument();
  });

  it('6. Renders Evidence & Grounding section with epistemic ledger claims', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    expect(screen.getByRole('heading', { name: /Recommendations should have receipts/i })).toBeInTheDocument();
    expect(screen.getByText(/Purchase Order Release Automation/i)).toBeInTheDocument();
    expect(screen.getByText(/Epistemic Grounding Standard/i)).toBeInTheDocument();
    expect(screen.getAllByText('FACT').length).toBeGreaterThan(0);
    expect(screen.getAllByText('ASSUMPTION').length).toBeGreaterThan(0);
    expect(screen.getAllByText('UNKNOWN').length).toBeGreaterThan(0);
  });

  it('7. Renders Use Cases grid with 4 enterprise operational applications', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    expect(screen.getByText(/Manufacturing & Production Workflows/i)).toBeInTheDocument();
    expect(screen.getByText(/Procurement & Order-to-Cash/i)).toBeInTheDocument();
    expect(screen.getByText(/Service Delivery & Ticket Resolution/i)).toBeInTheDocument();
    expect(screen.getByText(/Automation Opportunity Discovery/i)).toBeInTheDocument();
  });

  it('8. Renders Trust and Analytical Rigour section without fabricated compliance claims', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    expect(screen.getByRole('heading', { name: /Grounded analysis. Honest limitations/i })).toBeInTheDocument();
    expect(screen.getByText(/Deterministic Metrics/i)).toBeInTheDocument();
    expect(screen.getByText(/Data-Quality Auditing/i)).toBeInTheDocument();
    expect(screen.getByText(/Epistemic Discipline/i)).toBeInTheDocument();
    expect(screen.getByText(/Authenticated, Transient Analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/does not persist customer datasets or implement tenant-isolated data workspaces/i)).toBeInTheDocument();
  });

  it('9. Renders Final Call to Action and Footer with working routes', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider initialUser={null}>
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={false} />
      </AuthProvider>
    );

    expect(screen.getByRole('heading', { name: /Know where to improve next/i })).toBeInTheDocument();
    const ctaSignInBtn = screen.getByRole('button', { name: /Sign In to Workspace/i });
    fireEvent.click(ctaSignInBtn);
    expect(onNavigate).toHaveBeenCalledWith('/login');

    // Footer Links
    expect(screen.getByText(/Developer Console/i)).toBeInTheDocument();
    expect(screen.getByText(/© 2026 ProcessLens/i)).toBeInTheDocument();
  });

  it('10. Shows "Go to Workspace" when user is already authenticated', () => {
    const onNavigate = vi.fn();
    render(
      <AuthProvider
        initialUser={{
          id: 'usr_123',
          email: 'customer@processlens.com',
          name: 'Jane Doe',
          role: 'customer',
          created_at: '2026-01-01T00:00:00Z',
        }}
      >
        <MarketingLandingPage onNavigate={onNavigate} isAuthenticated={true} />
      </AuthProvider>
    );

    const workspaceBtn = screen.getAllByRole('button', { name: /Go to Workspace/i })[0];
    expect(workspaceBtn).toBeInTheDocument();
    fireEvent.click(workspaceBtn);
    expect(onNavigate).toHaveBeenCalledWith('/');
  });
});
