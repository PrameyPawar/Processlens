import React from 'react';

export type BadgeVariant =
  | 'cyan'
  | 'teal'
  | 'amber'
  | 'coral'
  | 'purple'
  | 'slate'
  | 'fact'
  | 'estimate'
  | 'assumption'
  | 'unknown';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  title?: string;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'slate',
  size = 'md',
  icon,
  title,
  className = '',
}) => {
  return (
    <span
      className={`pl-badge pl-badge-${variant} pl-badge-${size} ${className}`}
      title={title}
    >
      {icon && <span className="pl-badge-icon">{icon}</span>}
      <span className="pl-badge-text">{children}</span>
    </span>
  );
};
