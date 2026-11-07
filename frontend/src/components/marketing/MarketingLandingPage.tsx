import React from 'react';
import '../../styles/marketing.css';
import { ProcessNetworkBackground } from './ProcessNetworkBackground';
import { MarketingNavbar } from './MarketingNavbar';
import { HeroSection } from './HeroSection';
import { ProductPreview } from './ProductPreview';
import { ProblemSection } from './ProblemSection';
import { HowItWorksSection } from './HowItWorksSection';
import { EvidenceSection } from './EvidenceSection';
import { UseCasesSection } from './UseCasesSection';
import { TrustSection } from './TrustSection';
import { FinalCTASection } from './FinalCTASection';
import { MarketingFooter } from './MarketingFooter';

interface MarketingLandingPageProps {
  onNavigate: (path: string) => void;
  isAuthenticated: boolean;
}

export const MarketingLandingPage: React.FC<MarketingLandingPageProps> = ({
  onNavigate,
  isAuthenticated,
}) => {
  return (
    <div className="pl-marketing-root">
      {/* Layer 0: Interactive Dot-Grid Background with mouse-glow and drifting particles */}
      <ProcessNetworkBackground />

      {/* Layer 1: Quordix-inspired Floating Rounded Navbar */}
      <MarketingNavbar onNavigate={onNavigate} isAuthenticated={isAuthenticated} />

      {/* Layer 2: Oversized Typography Hero with Glitch Animation */}
      <HeroSection onNavigate={onNavigate} isAuthenticated={isAuthenticated} />

      {/* Product Preview Section with Quickstart Sample Analysis */}
      <ProductPreview onNavigate={onNavigate} isAuthenticated={isAuthenticated} />

      {/* Problem & Value Cards Section */}
      <ProblemSection />

      {/* 4-Step Process Pipeline */}
      <HowItWorksSection />

      {/* Epistemic Evidence Dossier Showcase */}
      <EvidenceSection />

      {/* Enterprise Operational Use Cases */}
      <UseCasesSection />

      {/* Trust, Data Handling & Analytical Limitations */}
      <TrustSection />

      {/* Closing Call to Action */}
      <FinalCTASection onNavigate={onNavigate} isAuthenticated={isAuthenticated} />

      {/* Clean Marketing Footer */}
      <MarketingFooter onNavigate={onNavigate} />
    </div>
  );
};

export default MarketingLandingPage;
