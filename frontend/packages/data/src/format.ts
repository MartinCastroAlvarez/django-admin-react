// Wire-value formatters.
//
// The `FieldValue` type from the wire contract is a tagged union of
// primitives, FK envelopes, and FK-envelope lists. Every page that
// renders a cell or a field reads through one of these helpers, so
// the formatting story stays consistent across the SPA.

import type { FieldValue, ForeignKeyValue } from '@dar/api';

const EMPTY_PLACEHOLDER = '—';

function isForeignKeyValue(value: unknown): value is ForeignKeyValue {
  return typeof value === 'object' && value !== null && 'id' in value && 'label' in value;
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
  if (isForeignKeyValue(value)) return value.label;
  return String(value);
}
