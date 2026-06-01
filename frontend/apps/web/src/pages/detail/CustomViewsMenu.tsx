import { useEffect, useRef, useState } from 'react';
import { ChevronDown, ExternalLink } from 'lucide-react';

import { type CustomView } from '@dar/data';

/**
 * Custom admin views (#439): bespoke admin pages the consumer wired via
 * ModelAdmin.get_urls(). The SPA can't render the Django template, so it
 * links out — a real anchor that opens the legacy-admin-rendered page in
 * a new tab. A single view renders as one button; several collapse into
 * an unobtrusive "More" dropdown so the toolbar stays tidy. Closes on
 * outside-click / Escape.
 */
export function CustomViewsMenu({ views }: { views: CustomView[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDocClick = (e: MouseEvent): void => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const linkClass =
    'flex items-center gap-1.5 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 whitespace-nowrap';

  // Single view → render it inline as one button (no need for a menu).
  if (views.length === 1) {
    const v = views[0] as CustomView;
    return (
      <a
        href={v.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <ExternalLink className="h-4 w-4" aria-hidden /> {v.label}
      </a>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        More
        <ChevronDown
          className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 z-10 mt-1 min-w-[12rem] overflow-hidden rounded-md border border-gray-200 bg-white py-1 shadow-lg"
        >
          {views.map((v) => (
            <a
              key={v.name}
              href={v.url}
              target="_blank"
              rel="noopener noreferrer"
              role="menuitem"
              className={linkClass}
              onClick={() => setOpen(false)}
            >
              <ExternalLink className="h-4 w-4 shrink-0" aria-hidden /> {v.label}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
