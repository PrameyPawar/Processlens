import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  headerAction?: React.ReactNode;
  surface?: 'main' | 'raised' | 'flat';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  className?: string;
  id?: string;
  ariaLabel?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  headerAction,
  surface = 'main',
  padding = 'md',
  className = '',
  id,
  ariaLabel,
}) => {
  return (
    <div
      id={id}
      className={`pl-card pl-surface-${surface} pl-pad-${padding} ${className}`}
      aria-label={ariaLabel}
    >
      {(title || subtitle || headerAction) && (
        <div className="pl-card-header">
          <div className="pl-card-title-group">
            {title && <h3 className="pl-card-title">{title}</h3>}
            {subtitle && <p className="pl-card-subtitle">{subtitle}</p>}
          </div>
          {headerAction && <div className="pl-card-action">{headerAction}</div>}
        </div>
      )}
      <div className="pl-card-body">{children}</div>
    </div>
  );
};
