// Action-handler redirect routing (#620). Django ModelAdmin actions
// can return any HttpResponse (HttpResponseRedirect, file streams,
// HTML pages); the API extracts the response's Location header into
// the JSON envelope's `redirect` field. Before this fix the SPA piped
// `redirect` straight into React Router's `navigate` — which is
// scoped to the SPA mount, so any redirect pointing OUTSIDE the SPA
// silently no-op'd: legacy `/admin/.../` URLs, hijack/impersonate
// flows, signed S3 download URLs all looked broken from the operator's
// POV. This helper picks the right navigation primitive per URL.
import type { NavigateFunction } from 'react-router-dom';

/**
 * Follow a redirect returned by a ModelAdmin action.
 *
 * - Same origin AND under the SPA mount → React Router `navigate`
 *   (no full reload; the operator stays in the SPA).
 * - Anything else (off-origin, or same-origin outside the mount) →
 *   `window.location.assign` (full browser navigation; the only way
 *   to reach a non-SPA page).
 *
 * `mount` is the SPA's URL prefix (e.g. `/admin-react/`), already
 * read once at boot from the `<meta name="dar-mount">` tag in
 * `main.tsx` — pass it through; this helper doesn't query the DOM
 * so it stays unit-testable.
 *
 * If the redirect URL is unparseable (a defensive case — the API
 * should always emit a real URL) we fall back to `window.location
 * .assign` and let the browser report the failure to the user.
 */
export interface FollowRedirectArgs {
  redirect: string;
  mount: string;
  navigate: NavigateFunction;
  /** Current page origin (`http://localhost:3000` etc.). Defaults to
   *  `window.location.origin` in production; the test injects a known
   *  value because jsdom's `window.location.origin` is hard-coded. */
  currentOrigin?: string;
  /** Full-page navigation. Defaults to `window.location.assign` in
   *  production; the test injects a spy because jsdom's
   *  `window.location.assign` is non-configurable on most jsdom
   *  versions and resists `vi.spyOn`. */
  assignLocation?: (url: string) => void;
}

export function followActionRedirect(args: FollowRedirectArgs): void {
  const { redirect, mount, navigate } = args;
  const origin = args.currentOrigin ?? window.location.origin;
  const assignLocation = args.assignLocation ?? ((url: string) => window.location.assign(url));
  let parsed: URL;
  try {
    parsed = new URL(redirect, origin);
  } catch {
    assignLocation(redirect);
    return;
  }
  const sameOrigin = parsed.origin === origin;
  const inSpaMount = parsed.pathname.startsWith(mount);
  if (sameOrigin && inSpaMount) {
    // BrowserRouter is initialised with `basename={mount}` (main.tsx)
    // so React Router routes are relative to that. Strip the mount
    // prefix before passing — otherwise the basename auto-prepends
    // and we get `/admin-react/admin-react/...` which 404s.
    const relative = parsed.pathname.slice(mount.length - 1) + parsed.search + parsed.hash;
    navigate(relative);
  } else {
    assignLocation(redirect);
  }
}
