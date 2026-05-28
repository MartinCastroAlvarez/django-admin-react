// LegacyAdminBanner (#577) — opt-in escape hatch for a progressive
// migration. When the consumer set `DJANGO_ADMIN_REACT[
// "LEGACY_ADMIN_URL_PREFIX"]`, the SPA index template emits
// `<meta name="dar-legacy-admin-prefix" content="...">`. This banner
// reads that meta and renders a thin notice linking the same page
// under the legacy admin's prefix — both admins use the same
// `app_label/model_name/...` URL shape, so it's a straight prefix
// swap with no per-route mapping.
//
// Dismissible per session via sessionStorage (not localStorage) so each
// session shows it once — a user who dismisses today still sees the
// escape hatch tomorrow and doesn't forget it exists.

import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { useLocation } from 'react-router-dom';

const DISMISS_KEY = 'dar.legacyBanner.dismissed';

function readMeta(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`);
  return el?.content?.trim() || null;
}

// The SPA mount (already injected as <meta name="dar-mount">). React
// Router's basename matches this value, so `useLocation().pathname` is
// relative to the mount — but `window.location.pathname` is absolute.
// We need the absolute current path to swap the prefix.
function readMount(): string {
  const m = readMeta('dar-mount');
  // Default fallback matches main.tsx's detectMount behaviour.
  return (m ?? '/').replace(/\/?$/, '/');
}

function readLegacyPrefix(): string | null {
  return readMeta('dar-legacy-admin-prefix');
}

// Build the legacy URL by swapping the SPA mount for the legacy prefix.
// Both admins live under the same origin, so an absolute path is fine.
function legacyUrlFor(currentPath: string, mount: string, legacyPrefix: string): string {
  // currentPath starts with the SPA mount; strip it, then prepend the
  // legacy prefix (also normalised to end in a single slash).
  const tail = currentPath.startsWith(mount) ? currentPath.slice(mount.length) : currentPath.replace(/^\//, '');
  const prefix = legacyPrefix.replace(/^\/?/, '/').replace(/\/?$/, '/');
  return `${prefix}${tail}`;
}

export function LegacyAdminBanner() {
  const legacyPrefix = useMemo(readLegacyPrefix, []);
  const mount = useMemo(readMount, []);
  // useLocation() drives re-render on route change so the link always
  // points at the matching legacy URL for the current page.
  const location = useLocation();
  const [dismissed, setDismissed] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    try {
      return window.sessionStorage.getItem(DISMISS_KEY) === '1';
    } catch {
      // sessionStorage can throw in some embedded contexts (private
      // mode iframes, sandboxed pages). Fall back to "not dismissed"
      // so the escape hatch stays visible.
      return false;
    }
  });

  // Re-check sessionStorage on mount (in case the SPA navigated within
  // the same session after a dismiss in another tab — unlikely but
  // free to verify).
  useEffect(() => {
    try {
      if (window.sessionStorage.getItem(DISMISS_KEY) === '1') setDismissed(true);
    } catch {
      // ignore
    }
  }, []);

  if (!legacyPrefix || dismissed) return null;

  // `window.location.pathname` is absolute; use it to handle deep links
  // that React Router hasn't normalised yet on first paint.
  const currentPath = window.location.pathname;
  const legacyUrl = legacyUrlFor(currentPath, mount, legacyPrefix);

  function dismiss(): void {
    setDismissed(true);
    try {
      window.sessionStorage.setItem(DISMISS_KEY, '1');
    } catch {
      // If sessionStorage is unavailable the dismiss is in-memory only —
      // a page reload brings the banner back. Acceptable degradation.
    }
  }

  return (
    <div
      role="region"
      aria-label="Legacy admin escape hatch"
      // Uses existing notice palette tokens (border + bg + text) so the
      // banner matches the SPA's other info chips. No novel chrome.
      // `location.key` keys the wrapping div so a route change re-runs
      // the URL compute against the new path.
      key={location.key}
      className="mb-4 flex items-center justify-between gap-3 rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-sm text-blue-700"
    >
      <span className="min-w-0 truncate">
        Need the classic experience?{' '}
        <a
          href={legacyUrl}
          target="_self"
          rel="noopener"
          className="font-medium underline hover:no-underline"
        >
          Open this page in the original admin
        </a>
        .
      </span>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss"
        title="Dismiss"
        className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-blue-700 hover:bg-blue-100"
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
