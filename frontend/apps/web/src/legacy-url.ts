// Legacy-iframe URL validation (#665).
//
// The form-spec endpoint can return `{renderer: "legacy-iframe", legacy_url}`
// to embed the legacy admin change/add page inside the SPA shell (#659). That
// URL flows into both an `<iframe src>` and an `<a href target=_blank>`, so it
// reaches two navigational sinks. The SPA *should* be able to trust the API,
// but every other navigational sink in this codebase validates before using a
// server-supplied URL (`action-redirect.ts` parses + origin/mount-checks the
// action redirect; `views.py` percent-encodes `next`). This is the one
// server-emitted URL that previously reached `src`/`href` unchecked — a
// compromised, buggy, or request-influenced backend could emit a
// `javascript:` URL (executes from the anchor on click) or an off-origin
// `http://attacker/` URL (renders attacker content inside the authenticated
// admin chrome — a high-fidelity phishing surface). We close that with the
// same parse-and-validate discipline used elsewhere.
//
// The legacy admin lives on the SAME origin as the SPA (under its own admin
// prefix, NOT the SPA mount), so the rule is: parse against the current
// origin, require an `http:`/`https:` scheme, and require the parsed origin to
// equal the current origin. Anything else (a non-http(s) scheme like
// `javascript:`/`data:`/`blob:`, or a cross-origin target) is rejected and the
// caller renders an inert error card instead of framing/linking it.

export interface ValidateLegacyUrlArgs {
  url: string;
  /** Current page origin. Defaults to `window.location.origin`; the test
   *  injects a known value (jsdom's origin is fixed). */
  currentOrigin?: string;
}

/**
 * Return a safe, same-origin http(s) URL string, or `null` when the URL is
 * unparseable, uses a non-http(s) scheme, or points off-origin.
 *
 * Returning the *re-serialised* parsed URL (not the raw input) means the value
 * handed to `src`/`href` is exactly what passed validation — no room for a
 * parser-differential between the check and the sink.
 */
export function safeLegacyUrl(args: ValidateLegacyUrlArgs): string | null {
  const origin = args.currentOrigin ?? window.location.origin;
  let parsed: URL;
  try {
    parsed = new URL(args.url, origin);
  } catch {
    return null;
  }
  // Reject `javascript:` / `data:` / `blob:` / `mailto:` etc. outright — only
  // real navigable web schemes are allowed in an iframe/anchor here.
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
  // The legacy admin is same-origin; an off-origin target is never legitimate.
  if (parsed.origin !== origin) return null;
  return parsed.href;
}
