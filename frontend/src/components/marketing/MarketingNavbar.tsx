import React, { useState, useEffect } from 'react';
import { ProcessLensLogo } from '../brand/ProcessLensLogo';
import { UserCheck } from 'lucide-react';

interface MarketingNavbarProps {
  onNavigate: (path: string) => void;
  isAuthenticated: boolean;
}

const NAV_LINKS = [
  { label: 'Product', href: '#product-preview' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Use Cases', href: '#use-cases' },
  { label: 'Trust & Evidence', href: '#trust-evidence' },
];

export const MarketingNavbar: React.FC<MarketingNavbarProps> = ({
  onNavigate,
  isAuthenticated,
}) => {
  const [open, setOpen] = useState(false);

  // Close mobile drawer on ESC
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  const handleAnchorClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    setOpen(false);
    const element = document.querySelector(href);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <>
      <header className="qhero-nav-wrap">
        <nav className="qhero-nav-pill" aria-label="Main Navigation">
          {/* Logo on the left */}
          <a
            href="#top"
            className="qhero-logo-link"
            onClick={(e) => handleAnchorClick(e, '#top')}
            aria-label="ProcessLens Home"
          >
            <ProcessLensLogo size={26} variant="full" theme="light" />
          </a>

          {/* Desktop links */}
          <ul className="qhero-nav-links">
            {NAV_LINKS.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  className="qhero-nav-link"
                  onClick={(e) => handleAnchorClick(e, link.href)}
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>

          {/* Desktop CTA + Sign In + Hamburger */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            {isAuthenticated ? (
              <button
                type="button"
                className="qhero-nav-cta"
                onClick={() => onNavigate('/')}
              >
                <UserCheck size={14} style={{ marginRight: '4px' }} />
                Go to Workspace
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="qhero-nav-link"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                  onClick={() => onNavigate('/login')}
                >
                  Sign In
                </button>
                <a
                  href="#product-preview"
                  className="qhero-nav-cta"
                  onClick={(e) => handleAnchorClick(e, '#product-preview')}
                >
                  Explore Product
                </a>
              </>
            )}

            {/* Mobile hamburger button with animated spans */}
            <button
              className="qhero-hamburger"
              onClick={() => setOpen(!open)}
              aria-label={open ? 'Close menu' : 'Open menu'}
              aria-expanded={open}
            >
              <span
                style={{
                  transform: open ? 'rotate(45deg) translateY(7px)' : 'none',
                }}
              />
              <span style={{ opacity: open ? 0 : 1 }} />
              <span
                style={{
                  transform: open ? 'rotate(-45deg) translateY(-7px)' : 'none',
                }}
              />
            </button>
          </div>
        </nav>
      </header>

      {/* Quordix Mobile Fullscreen Blur Overlay */}
      <div
        className={`qhero-mobile-overlay${open ? ' open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Mobile Navigation"
      >
        {NAV_LINKS.map((link) => (
          <a
            key={link.label}
            href={link.href}
            className="qhero-mobile-link"
            onClick={(e) => handleAnchorClick(e, link.href)}
          >
            {link.label}
          </a>
        ))}

        {isAuthenticated ? (
          <button
            type="button"
            className="qhero-mobile-cta"
            onClick={() => {
              setOpen(false);
              onNavigate('/');
            }}
          >
            Go to Workspace
          </button>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center' }}>
            <button
              type="button"
              className="qhero-mobile-link"
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.25rem' }}
              onClick={() => {
                setOpen(false);
                onNavigate('/login');
              }}
            >
              Customer Sign In
            </button>
            <a
              href="#product-preview"
              className="qhero-mobile-cta"
              onClick={(e) => handleAnchorClick(e, '#product-preview')}
            >
              Explore Product
            </a>
          </div>
        )}
      </div>
    </>
  );
};
