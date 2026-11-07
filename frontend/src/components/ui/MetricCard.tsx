import React from 'react';
import { Info } from 'lucide-react';

export interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  unit?: string;
  caption?: string;
  icon?: React.ReactNode;
  variant?: 'cyan' | 'teal' | 'amber' | 'coral' | 'purple' | 'neutral';
  tooltip?: string;
  onClick?: () => void;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  caption,
  icon,
  variant = 'cyan',
  tooltip,
  onClick,
  className = '',
}) => {
  const isInteractive = Boolean(onClick);

  return (
    <div
      className={`pl-metric-card pl-metric-${variant} ${isInteractive ? 'is-interactive hover-lift' : ''} ${className}`}
      onClick={onClick}
      role={isInteractive ? 'button' : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      onKeyDown={
        isInteractive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick!();
              }
            }
          : undefined
      }
      aria-label={typeof value === 'string' || typeof value === 'number' ? `${label}: ${value}${unit ? ` ${unit}` : ''}` : label}
    >
      <div className="pl-metric-header">
        <div className="pl-metric-label-group">
          {icon && <span className="pl-metric-icon" aria-hidden="true">{icon}</span>}
          <span className="pl-metric-label">{label}</span>
        </div>
        {tooltip && (
          <span
            className="pl-metric-tooltip-trigger"
            title={tooltip}
            aria-label={tooltip}
            tabIndex={0}
          >
            <Info size={13} className="text-muted" aria-hidden="true" />
          </span>
        )}
      </div>

      <div className="pl-metric-body">
        <span className="pl-metric-value tabular-nums">{value}</span>
        {unit && <span className="pl-metric-unit">{unit}</span>}
      </div>

      {caption && <div className="pl-metric-caption">{caption}</div>}
    </div>
  );
};
