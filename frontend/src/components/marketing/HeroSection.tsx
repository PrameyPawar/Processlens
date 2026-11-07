import React from 'react';
import { ShieldCheck, CheckCircle2 } from 'lucide-react';

interface HeroSectionProps {
  onNavigate?: (path: string) => void;
  isAuthenticated?: boolean;
}

export const HeroSection: React.FC<HeroSectionProps> = () => {
  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, selector: string) => {
    e.preventDefault();
    const el = document.querySelector(selector);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <main id="top" className="qhero-main">
      <div>
        {/* Orange pulsing tagline */}
        <span className="qhero-tagline-pulse">
          OPERATIONS INTELLIGENCE
        </span>

        {/* Large split title with glitch effect on second line */}
        <h1 className="qhero-title-wrap">
          <span className="qhero-title-row1">FIND THE FRICTION.</span>
          <span className="qhero-glitch" data-text="FIX WHAT MATTERS.">
            FIX WHAT MATTERS.
          </span>
        </h1>
      </div>

      {/* Editorial Subtitle */}
      <p className="qhero-subtitle">
        ProcessLens turns operational event data into a clear, evidence-backed picture of
        how work flows, where bottlenecks emerge, and which improvements deserve attention first.
      </p>

      {/* Quordix Hero Button with sliding arrow icon */}
      <a
        href="#product-preview"
        className="qhero-btn"
        onClick={(e) => handleScrollTo(e, '#product-preview')}
      >
        <span>Explore the Product</span>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" />
        </svg>
      </a>

      {/* Microcopy Trust Signals */}
      <div className="qhero-microcopy">
        <span>
          <CheckCircle2 size={14} style={{ color: '#0F766E' }} />
          Evidence-led analysis
        </span>
        <span style={{ opacity: 0.4 }}>•</span>
        <span>
          <ShieldCheck size={14} style={{ color: '#0369A1' }} />
          Transparent prioritisation
        </span>
        <span style={{ opacity: 0.4 }}>•</span>
        <span>No invented metrics</span>
      </div>
    </main>
  );
};
