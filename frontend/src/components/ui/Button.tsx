import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'subtle' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'secondary',
  size = 'md',
  iconLeft,
  iconRight,
  isLoading = false,
  className = '',
  disabled,
  ...rest
}) => {
  return (
    <button
      className={`pl-btn pl-btn-${variant} pl-btn-${size} ${isLoading ? 'is-loading' : ''} ${className}`}
      disabled={disabled || isLoading}
      {...rest}
    >
      {isLoading ? (
        <span className="pl-btn-spinner" />
      ) : (
        iconLeft && <span className="pl-btn-icon-left">{iconLeft}</span>
      )}
      <span className="pl-btn-text">{children}</span>
      {!isLoading && iconRight && <span className="pl-btn-icon-right">{iconRight}</span>}
    </button>
  );
};
