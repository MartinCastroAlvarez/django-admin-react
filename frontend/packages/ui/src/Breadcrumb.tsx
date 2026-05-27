// Breadcrumb — generic, router-agnostic navigation trail (#355).
//
// The host composes the item list (e.g. Home › Tenants › Acme); a linked
// crumb carries `to`. To stay framework-agnostic (CLAUDE.md §7) @dar/ui
// doesn't depend on a router: a linked crumb renders through the optional
// `linkComponent` (pass react-router's `Link` for SPA navigation) and
// falls back to a plain `<a href>` otherwise. The final crumb is always
// the current page — unlinked, marked `aria-current="page"`.

import type { ReactNode } from 'react';

export interface BreadcrumbItem {
  label: ReactNode;
  /** When set (and not the last item), the crumb is a link to this path. */
  to?: string;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  /**
   * Render a navigable crumb. Pass a router-aware wrapper (e.g.
   * `(to, className, label) => <Link to={to} className={className}>{label}</Link>`)
   * for SPA navigation. Defaults to a plain `<a href>` (full reload).
   * A callback rather than a component keeps @dar/ui router-agnostic.
   */
  renderLink?: (to: string, className: string, label: ReactNode) => ReactNode;
}

const LINK_CLASS = 'text-blue-600 hover:underline';

export function Breadcrumb({ items, renderLink }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className="text-sm text-gray-500">
      <ol className="flex flex-wrap items-center gap-1.5">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          const linked = item.to !== undefined && !last;
          return (
            <li key={i} className="flex items-center gap-1.5">
              {i > 0 && (
                <span aria-hidden="true" className="text-gray-300">
                  /
                </span>
              )}
              {linked ? (
                renderLink ? (
                  renderLink(item.to as string, LINK_CLASS, item.label)
                ) : (
                  <a href={item.to} className={LINK_CLASS}>
                    {item.label}
                  </a>
                )
              ) : (
                <span
                  className={last ? 'text-gray-700' : undefined}
                  aria-current={last ? 'page' : undefined}
                >
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
