// Generic button primitive. Tailwind-styled; no business knowledge.
import type { ButtonHTMLAttributes, ReactNode } from 'react';

import { Spinner } from './Spinner';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  children?: ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-primary hover:opacity-90 text-white border border-primary',
  secondary: 'bg-white hover:bg-gray-50 text-gray-900 border border-gray-300',
  danger: 'bg-red-600 hover:bg-red-700 text-white border border-red-600',
  ghost: 'bg-transparent hover:bg-gray-100 text-gray-700 border border-transparent',
};

const BASE_CLASSES =
  'inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md ' +
  'text-sm font-medium transition-colors disabled:opacity-50 ' +
  'disabled:cursor-not-allowed ' +
  // Keyboard-only focus ring (#434). focus-visible (not focus) so the
  // ring shows on Tab but not on mouse click; offset keeps it clear of
  // the button's own border in both themes.
  'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1';

export function Button({
  variant = 'primary',
  loading = false,
  disabled,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={loading || disabled}
      className={`${BASE_CLASSES} ${VARIANT_CLASSES[variant]} ${className}`}
      {...rest}
    >
      {loading ? <Spinner size="sm" /> : null}
      {children}
    </button>
  );
}
