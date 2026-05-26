import type { PropsWithChildren, ReactNode } from 'react';

export interface CardProps {
  title?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function Card({ title, actions, className = '', children }: PropsWithChildren<CardProps>) {
  return (
    <section className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          {title ? <h2 className="text-base font-semibold text-gray-900">{title}</h2> : <span />}
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
