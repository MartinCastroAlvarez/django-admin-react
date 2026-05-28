// LegacyAdminBanner (#577, #582, #583) — opt-in escape hatch for a
// progressive migration. When the consumer set `DJANGO_ADMIN_REACT[
// "LEGACY_ADMIN_URL_PREFIX"]`, the SPA index template emits
// `<meta name="dar-legacy-admin-prefix" content="...">`. This banner
// reads that meta and renders a thin persistent strip at the top of
// every page linking the same path under the legacy admin's prefix.
//
// **Persistent + subtle** (#583): the strip cannot be dismissed by
// the user (a session dismiss defeats the point — operators wired
// the setting precisely to keep the escape hatch discoverable on
// every page). Style is a thin neutral chrome row, not an
// attention-grabbing notice block. Operators control existence via
// `LEGACY_ADMIN_URL_PREFIX` in settings.py.
//
// **URL construction** (#582) preserves the entire current location —
// path + search + hash — so a user on a filtered changelist crosses
// over to the legacy admin's matching filtered view. The pathname
// always ends in a trailing slash before the query string so the
// legacy admin's URL conf resolves it (Django admin URLs are built
// with `path("<app>/<model>/", ...)`; missing slash → catch_all_view
// 404 instead of resolving the changelist).

import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';

function readMeta(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`);
  return el?.content?.trim() || null;
}

// The SPA mount (already injected as <meta name="dar-mount">).
function readMount(): string {
  const m = readMeta('dar-mount');
  return (m ?? '/').replace(/\/?$/, '/');
}

function readLegacyPrefix(): string | null {
  return readMeta('dar-legacy-admin-prefix');
}

// Build the legacy URL from the current absolute href by swapping the
// SPA mount for the legacy prefix. Preserves path + search + hash and
// always ends the pathname with `/` before the query string so the
// legacy admin's URL conf resolves it instead of 404ing through
// `catch_all_view` (#582).
export function legacyUrlFor(currentHref: string, mount: string, legacyPrefix: string): string {
  // `URL` does the heavy lifting: it normalises //, computes pathname /
  // search / hash for us, and tolerates whatever the SPA's router has
  // produced. The origin is irrelevant — we only return the path.
  const url = new URL(currentHref, 'http://_');
  const mountNorm = mount.startsWith('/') ? mount : `/${mount}`;
  const legacyNorm =
    '/' + legacyPrefix.replace(/^\/+/, '').replace(/\/+$/, '') + '/';
  // Tail = everything in the SPA path AFTER the mount prefix. If the
  // current path doesn't actually start with the mount, we still want
  // a stable answer (the legacy admin root) — use an empty tail.
  const tail = url.pathname.startsWith(mountNorm)
    ? url.pathname.slice(mountNorm.length)
    : '';
  let pathname = legacyNorm + tail;
  if (!pathname.endsWith('/')) pathname += '/';
  return pathname + url.search + url.hash;
}

export function LegacyAdminBanner() {
  const legacyPrefix = useMemo(readLegacyPrefix, []);
  const mount = useMemo(readMount, []);
  // useLocation drives a re-render on route change so the link always
  // points at the matching legacy URL for the current page.
  const location = useLocation();

  if (!legacyPrefix) return null;

  // window.location.* is the source of truth for path + search + hash
  // — React Router's `location` only mirrors path + search (no hash),
  // and `useLocation` updates after the URL bar so reading it directly
  // is consistent. `location.key` is in the dependency tree implicitly
  // via the React re-render, so the URL recomputes on each navigation.
  const currentHref = window.location.href;
  const legacyUrl = legacyUrlFor(currentHref, mount, legacyPrefix);
  void location; // silences unused-var; the read above is what we need

  return (
    <div
      role="region"
      aria-label="Experience toggle"
      // Thin persistent strip (#583), not a notice block:
      // - one line tall (~28px including padding),
      // - muted neutral surface (uses bg-gray-50 / border-gray-200,
      //   already in the .dark remap), no info-blue,
      // - no `×` / dismiss control,
      // - whole-line click target via the inner anchor.
      className="-mx-6 -mt-6 mb-4 border-b border-gray-200 bg-gray-50 px-6 py-1 text-xs text-gray-600 lg:-mx-6 lg:-mt-6"
    >
      <a
        href={legacyUrl}
        target="_self"
        rel="noopener"
        className="inline-flex items-center gap-1 hover:text-gray-900 hover:underline"
      >
        <span>Looking for the classic admin?</span>
        <span className="font-medium">Open this page in {`/${legacyPrefix}`.replace(/\/$/, '')}/</span>
      </a>
    </div>
  );
}
