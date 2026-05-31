// prepopulated_fields helper (#245 / #629). Pure function so the
// CreatePage form logic is testable without rendering the page —
// CreatePage owns the per-target "user has edited this" set and
// passes it in; this just applies the slugify-from-sources rule
// to every still-untouched target.
//
// Mirrors Django admin's add-form behaviour: typing in a source
// field auto-fills the target until the operator edits the target
// by hand, after which auto-fill stops for that record.
import type { WriteValue } from '@dar/data';

import { slugify } from '../slugify';

export interface PrepopulateArgs {
  /** Current draft values (the function is non-mutating — returns
   *  a NEW object with the updated targets). */
  values: Record<string, WriteValue>;
  /** From `schema.prepopulated_fields`: `{target: [...sourceFields]}`. */
  prepopulated: Record<string, string[]>;
  /** Target field names the operator has edited directly — these
   *  are SKIPPED so a manual edit isn't overwritten. */
  editedTargets: ReadonlySet<string>;
}

export function applyPrepopulate({
  values,
  prepopulated,
  editedTargets,
}: PrepopulateArgs): Record<string, WriteValue> {
  const next = { ...values };
  for (const [target, sources] of Object.entries(prepopulated)) {
    if (editedTargets.has(target)) continue;
    const joined = sources.map((s) => (next[s] == null ? '' : String(next[s]))).join(' ');
    next[target] = slugify(joined);
  }
  return next;
}
