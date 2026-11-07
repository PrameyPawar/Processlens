import React from 'react';
import { ProcessLensLogo } from '../brand/ProcessLensLogo';
import { Terminal } from 'lucide-react';

interface MarketingFooterProps {
  onNavigate: (path: string) => void;
}

export const MarketingFooter: React.FC<MarketingFooterProps> = ({ onNavigate }) => {
  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, selector: string) => {
    e.preventDefault();
    const el = document.querySelector(selector);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer className="mkt-footer">
      <div className="mkt-container">
        <div className="mkt-footer-grid">
          {/* Brand Col */}
          <div>
            <ProcessLensLogo size={24} variant="full" />
            <p className="mkt-footer-brand-desc">
              ProcessLens turns operational event logs into evidence-backed, financially
              understandable, prioritised improvement and automation opportunities.
            </p>
          </div>

          {/* Product Links */}
          <div className="mkt-footer-col">
            <h5>Product</h5>
            <ul>
              <li>
                <a href="#product-preview" onClick={(e) => handleScrollTo(e, '#product-preview')}>
                  Interactive Preview
                </a>
              </li>
              <li>
                <a href="#how-it-works" onClick={(e) => handleScrollTo(e, '#how-it-works')}>
                  How It Works
                </a>
              </li>
              <li>
                <a href="#use-cases" onClick={(e) => handleScrollTo(e, '#use-cases')}>
                  Enterprise Use Cases
                </a>
              </li>
              <li>
                <a href="#trust-evidence" onClick={(e) => handleScrollTo(e, '#trust-evidence')}>
                  Epistemic Grounding
                </a>
              </li>
            </ul>
          </div>

          {/* Platform Access */}
          <div className="mkt-footer-col">
            <h5>Platform</h5>
            <ul>
              <li>
                <a
                  href="/login"
                  onClick={(e) => {
                    e.preventDefault();
                    onNavigate('/login');
                  }}
                >
                  Customer Sign In
                </a>
              </li>
              <li>
                <a
                  href="/dev/login"
                  onClick={(e) => {
                    e.preventDefault();
                    onNavigate('/dev/login');
                  }}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <Terminal size={13} />
                  Developer Console
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mkt-footer-bottom">
          <div>
            © 2026 ProcessLens. Operations intelligence & decision-support platform.
          </div>
          <div>
            Evidence-led discovery • Grounded prioritisation
          </div>
        </div>
      </div>
    </footer>
  );
};
