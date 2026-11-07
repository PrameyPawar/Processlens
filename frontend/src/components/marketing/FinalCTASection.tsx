import React from 'react';
import { FileSpreadsheet } from 'lucide-react';

interface FinalCTASectionProps {
  onNavigate: (path: string) => void;
  isAuthenticated: boolean;
}

export const FinalCTASection: React.FC<FinalCTASectionProps> = ({ onNavigate, isAuthenticated }) => {
  const handleScrollToPreview = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const el = document.querySelector('#product-preview');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="mkt-final-cta">
      <div className="mkt-container">
        <div className="mkt-cta-box">
          <h2 className="mkt-cta-title">
            Know where to improve next.
          </h2>
          <p className="mkt-cta-desc">
            Start with the operational data you already have. Investigate the signals that matter.
            Make your next improvement decision with verifiable evidence.
          </p>

          <div className="mkt-cta-actions">
            {isAuthenticated ? (
              <button
                type="button"
                className="qhero-btn"
                onClick={() => onNavigate('/')}
              >
                <span>Go to Operational Workspace</span>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" />
                </svg>
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="qhero-btn"
                  onClick={() => onNavigate('/login')}
                >
                  <span>Sign In to Workspace</span>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" />
                  </svg>
                </button>

                <a
                  href="#product-preview"
                  className="qhero-nav-cta"
                  style={{ padding: '15px 30px', fontSize: '0.95rem' }}
                  onClick={handleScrollToPreview}
                >
                  <FileSpreadsheet size={16} />
                  Review Sample Analysis
                </a>
              </>
            )}
          </div>

          <div className="mkt-cta-note">
            CSV input • Automated schema checks • In-memory processing • No persistent dataset workspace
          </div>
        </div>
      </div>
    </section>
  );
};
