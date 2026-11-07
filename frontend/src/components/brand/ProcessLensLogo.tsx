import React from 'react';

export interface ProcessLensLogoProps {
  variant?: 'full' | 'compact' | 'icon';
  size?: 'sm' | 'md' | 'lg' | number;
  showSubtitle?: boolean;
  theme?: 'light' | 'dark' | 'auto';
  className?: string;
  onClick?: () => void;
}

export const ProcessLensLogo: React.FC<ProcessLensLogoProps> = ({
  variant = 'compact',
  size = 'md',
  showSubtitle = false,
  theme = 'auto',
  className = '',
  onClick,
}) => {
  // Height determinations based on size prop and variant
  // Full logo aspect ratio is ~3.92:1, icon is 1:1
  const heightMap: Record<string, number> = {
    sm: variant === 'icon' ? 24 : 28,
    md: variant === 'icon' ? 32 : 36,
    lg: variant === 'icon' ? 44 : 52,
  };

  const height = typeof size === 'number' ? size : (heightMap[size] || heightMap.md);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (onClick && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onClick();
    }
  };

  if (variant === 'icon') {
    return (
      <div
        className={`processlens-brand-wrapper ${onClick ? 'cursor-pointer' : ''} ${className}`}
        onClick={onClick}
        onKeyDown={handleKeyDown}
        role={onClick ? 'button' : 'img'}
        aria-label="ProcessLens — Operational Intelligence"
        tabIndex={onClick ? 0 : undefined}
      >
        <img
          src="/processlens-icon.png"
          alt="ProcessLens"
          className="brand-logo-img"
          style={{
            height: `${height}px`,
            width: `${height}px`,
            objectFit: 'contain',
          }}
        />
      </div>
    );
  }

  // If showSubtitle is true, use the full logo asset with tagline.
  // Otherwise use the clean notagline logo asset.
  const hasTagline = showSubtitle;
  const lightSrc = hasTagline ? '/processlens-logo.png' : '/processlens-logo-notagline.png';
  const darkSrc = hasTagline ? '/processlens-logo-dark.png' : '/processlens-logo-dark-notagline.png';

  return (
    <div
      className={`processlens-brand-wrapper ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={onClick ? 'button' : 'img'}
      aria-label="ProcessLens — Operational Intelligence"
      tabIndex={onClick ? 0 : undefined}
    >
      {theme === 'light' ? (
        <img
          src={lightSrc}
          alt="ProcessLens"
          className="brand-logo-img brand-logo-light"
          style={{
            height: `${height}px`,
            width: 'auto',
            maxWidth: '100%',
            objectFit: 'contain',
          }}
        />
      ) : theme === 'dark' ? (
        <img
          src={darkSrc}
          alt="ProcessLens"
          className="brand-logo-img brand-logo-dark"
          style={{
            height: `${height}px`,
            width: 'auto',
            maxWidth: '100%',
            objectFit: 'contain',
          }}
        />
      ) : (
        <>
          <img
            src={lightSrc}
            alt="ProcessLens"
            className="brand-logo-img brand-logo-light"
            style={{
              height: `${height}px`,
              width: 'auto',
              maxWidth: '100%',
              objectFit: 'contain',
            }}
          />
          <img
            src={darkSrc}
            alt="ProcessLens"
            className="brand-logo-img brand-logo-dark"
            style={{
              height: `${height}px`,
              width: 'auto',
              maxWidth: '100%',
              objectFit: 'contain',
            }}
          />
        </>
      )}
    </div>
  );
};
