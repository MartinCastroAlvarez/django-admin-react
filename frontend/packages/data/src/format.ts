// Wire-value formatters.
//
// The `FieldValue` type from the wire contract is a tagged union of
// primitives, FK envelopes, and FK-envelope lists. Every page that
// renders a cell or a field reads through one of these helpers, so
// the formatting story stays consistent across the SPA.

import type { FieldType, FieldValue, FileValue, ForeignKeyValue, HtmlValue } from '@dar/api';

const EMPTY_PLACEHOLDER = '—';

/**
 * Format a `date` / `datetime` / `time` wire value (an ISO 8601 string)
 * into a readable, locale-aware string for *display* (#413). Returns
 * `null` when the value isn't a temporal type or can't be parsed, so the
 * caller falls back to the raw string — never throwing on odd input.
 *
 * Timezone note: `datetime` is rendered in the **viewer's local timezone**
 * (the SPA-idiomatic choice — `toLocaleString` converts the instant). The
 * backend sends offset-aware ISO for `USE_TZ=True`, so the instant is
 * unambiguous; a naive datetime (no offset) is treated as wall-clock. A
 * `date` is rendered from its Y-M-D parts (no `Date(string)` parse) to
 * avoid the UTC-midnight day-shift in negative-offset zones.
 */
export function formatTemporal(value: FieldValue | undefined, type: FieldType): string | null {
  if (typeof value !== 'string' || value === '') return null;
  if (type === 'datetime') {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  }
  if (type === 'date') {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
    if (!m) return null;
    const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleDateString(undefined, { dateStyle: 'medium' });
  }
  if (type === 'time') {
    const m = /^(\d{2}):(\d{2})/.exec(value);
    if (!m) return null;
    const d = new Date();
    d.setHours(Number(m[1]), Number(m[2]), 0, 0);
    return d.toLocaleTimeString(undefined, { timeStyle: 'short' });
  }
  return null;
}

/**
 * True when the value is a ForeignKey envelope (`{ id, label }`) — the
 * related object's pk + `str()`. Callers render it as a link so FK
 * cells read as navigable, matching Django admin's `list_display` FK
 * columns.
 */
export function isForeignKeyValue(value: unknown): value is ForeignKeyValue {
  return typeof value === 'object' && value !== null && 'id' in value && 'label' in value;
}

/**
 * True when the value is the backend's safe-HTML envelope (a
 * `ModelAdmin` display method that returned a Django `SafeString`).
 * The caller renders `.html` as markup; a plain string never matches
 * this guard, so untrusted text stays escaped.
 */
export function isHtmlValue(value: unknown): value is HtmlValue {
  return (
    typeof value === 'object' &&
    value !== null &&
    'html' in value &&
    typeof (value as HtmlValue).html === 'string'
  );
}

/**
 * True when the value is a `FileField`/`ImageField` envelope
 * (`{ name, url, size }`). The caller renders it as a download link /
 * thumbnail rather than stringifying the object.
 */
export function isFileValue(value: unknown): value is FileValue {
  return (
    typeof value === 'object' &&
    value !== null &&
    'name' in value &&
    'url' in value &&
    typeof (value as FileValue).name === 'string'
  );
}

/**
 * Render a wire-shape value as a display string.
 *
 * - ``null`` / ``undefined`` → em-dash placeholder.
 * - booleans → "Yes" / "No" (matches Django admin's default).
 * - ForeignKey envelopes → their `label` (the related object's `str()`).
 * - Arrays of FK envelopes → comma-joined labels (M2M placeholder).
 * - `date` / `datetime` / `time` (when `type` is given) → localized
 *   display string (#413); unparseable values fall back to the raw string.
 * - Everything else → ``String(value)``.
 *
 * Consumers that want a richer rendering (e.g., a link to the
 * related detail page) can branch on the type themselves; this
 * helper is the safe-but-boring default.
 */
export function renderValue(value: FieldValue | undefined, type?: FieldType): string {
  if (value === null || value === undefined) return EMPTY_PLACEHOLDER;
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) {
    return value
      .map((entry) => (isForeignKeyValue(entry) ? entry.label : String(entry)))
      .join(', ');
  }
  // Safe-HTML envelope: when only a string is needed (e.g. a title),
  // strip tags to a plain-text approximation. Markup rendering is the
  // caller's job via `isHtmlValue` + dangerouslySetInnerHTML.
  if (isHtmlValue(value)) return stripTags(value.html);
  if (isForeignKeyValue(value)) return value.label;
  if (isFileValue(value)) return value.name;
  if (type) {
    const temporal = formatTemporal(value, type);
    if (temporal !== null) return temporal;
  }
  return String(value);
}

/**
 * Strip HTML tags to a plain-text approximation, safely.
 *
 * Used only to render markup as *text* (e.g. a `title` attribute);
 * React escapes the returned string when it's a text child, so this is
 * not itself a security boundary. The implementation is deliberately:
 *
 * - **ReDoS-free** — the character class `[^<>]` excludes *both* angle
 *   brackets, so the match is linear (no ambiguous overlap that a
 *   crafted input could force into polynomial backtracking).
 * - **Complete** — a single pass can leave a residual tag on
 *   overlapping/nested input like `<<b>script>`; looping until the
 *   string is stable guarantees no tag survives.
 *
 * (Replaces the prior `replace(/<[^>]*>/g, '')`, which CodeQL flagged
 * for both polynomial-ReDoS and incomplete multi-character
 * sanitization.)
 */
function stripTags(html: string): string {
  let previous: string;
  let stripped = html;
  do {
    previous = stripped;
    stripped = stripped.replace(/<[^<>]*>/g, '');
  } while (stripped !== previous);
  return stripped;
}
