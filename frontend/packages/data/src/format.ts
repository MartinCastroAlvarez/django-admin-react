// Wire-value formatters.
//
// The `FieldValue` type from the wire contract is a tagged union of
// primitives, FK envelopes, and FK-envelope lists. Every page that
// renders a cell or a field reads through one of these helpers, so
// the formatting story stays consistent across the SPA.

import type { FieldValue, ForeignKeyValue, HtmlValue } from '@dar/api';

const EMPTY_PLACEHOLDER = '—';

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
 * Render a wire-shape value as a display string.
 *
 * - ``null`` / ``undefined`` → em-dash placeholder.
 * - booleans → "Yes" / "No" (matches Django admin's default).
 * - ForeignKey envelopes → their `label` (the related object's `str()`).
 * - Arrays of FK envelopes → comma-joined labels (M2M placeholder).
 * - Everything else → ``String(value)``.
 *
 * Consumers that want a richer rendering (e.g., a link to the
 * related detail page) can branch on the type themselves; this
 * helper is the safe-but-boring default.
 */
export function renderValue(value: FieldValue | undefined): string {
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
  if (isHtmlValue(value)) return value.html.replace(/<[^>]*>/g, '');
  if (isForeignKeyValue(value)) return value.label;
  return String(value);
}
