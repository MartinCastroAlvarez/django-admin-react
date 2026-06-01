/** Capitalize the first character of a string (verbose-name display). */
export function capitalize(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/**
 * Empty-state copy. When a search / filter is active, say so; otherwise a
 * plain "No objects yet." An active server-side default filter is surfaced
 * by the Filter button + modal (see #283), not by over-explaining it here.
 */
export function emptyLabel(hasQuery: boolean, chipCount: number): string {
  if (hasQuery || chipCount > 0) return 'No results match the current search / filters.';
  return 'No objects yet.';
}
