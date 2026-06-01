import type { InputHTMLAttributes, ReactNode } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: ReactNode;
  helpText?: ReactNode;
  error?: ReactNode;
}

/**
 * Text input primitive with an optional label, help text, and error
 * message. Generates a stable-per-render `id` when none is supplied so the
 * label's `htmlFor` always resolves. Forwards all native input attributes.
 */
export function Input({ label, helpText, error, id, className = '', ...rest }: InputProps) {
  const inputId = id ?? `dar-input-${Math.random().toString(36).slice(2, 8)}`;
  return (
    <div className="flex flex-col gap-1">
      {label ? (
        <label htmlFor={inputId} className="text-sm font-medium text-gray-700">
          {label}
        </label>
      ) : null}
      <input
        id={inputId}
        className={`block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:border-blue-500 ${error ? 'border-red-500' : ''} ${className}`}
        {...rest}
      />
      {helpText && !error ? <span className="text-xs text-gray-500">{helpText}</span> : null}
      {error ? <span className="text-xs text-red-600">{error}</span> : null}
    </div>
  );
}
