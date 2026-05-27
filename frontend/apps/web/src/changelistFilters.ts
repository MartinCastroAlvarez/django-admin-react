// Preserve the operator's changelist filters across the
// list → detail/add → save/delete round-trip (#441), mirroring Django
// admin's `preserve_filters` / the `_changelist_filters` query param.
//
// The list view keeps its state (search `q`, `list_filter` values, `page`,
// `ordering`, `all`) in the URL. When the operator opens a row or the add
// form, we stash that whole query string under a single
// `_changelist_filters` param on the target URL. On the way back (save,
// delete, cancel, breadcrumb) we read it and re-apply it to the list URL,
// landing the operator on the exact filtered view they left — instead of a
// bare, unfiltered list.
//
// This lives in the URL (not router `location.state`) on purpose: it
// survives a reload / deep-link of the detail page, exactly like Django's
// `_changelist_filters`.

export const CHANGELIST_FILTERS_PARAM = '_changelist_filters';

/**
 * Append the current changelist query string to a detail/add target path
 * as `?_changelist_filters=<encoded>`. Returns `targetPath` unchanged when
 * there are no filters to preserve (so we never emit a noisy empty param).
 *
 * `currentSearch` is the list's raw query string — `URLSearchParams.toString()`
 * or `location.search` (a leading `?` is tolerated).
 */
export function withPreservedFilters(targetPath: string, currentSearch: string): string {
  const cleaned = currentSearch.startsWith('?') ? currentSearch.slice(1) : currentSearch;
  if (!cleaned) return targetPath;
  // Encode the whole query string as a single param value; `URLSearchParams`
  // percent-encodes the `=`/`&` so it round-trips intact.
  const param = new URLSearchParams();
  param.set(CHANGELIST_FILTERS_PARAM, cleaned);
  return `${targetPath}?${param.toString()}`;
}

/**
 * Resolve the "back to the list" URL, restoring the preserved changelist
 * filters from the current page's `_changelist_filters` param. Returns the
 * bare `listPath` when nothing was preserved.
 *
 * `search` is the current (detail/add) page's `URLSearchParams`.
 */
export function listPathWithPreservedFilters(
  listPath: string,
  search: URLSearchParams,
): string {
  const preserved = search.get(CHANGELIST_FILTERS_PARAM);
  if (!preserved) return listPath;
  // `preserved` is itself a query string (e.g. "status=active&page=2").
  // It only ever becomes the query part of the fixed, same-origin
  // `listPath`, so it can't redirect anywhere else.
  return `${listPath}?${preserved}`;
}

/**
 * Carry the preserved-filters param *forward* onto another detail/add
 * target (e.g. "Save and add another", "Save as new → continue editing")
 * so a later save/delete still returns to the original filtered list.
 * Appends to `targetPath`, which may already carry its own query (e.g.
 * `?edit=1`).
 */
export function carryPreservedFilters(targetPath: string, search: URLSearchParams): string {
  const preserved = search.get(CHANGELIST_FILTERS_PARAM);
  if (!preserved) return targetPath;
  const sep = targetPath.includes('?') ? '&' : '?';
  const param = new URLSearchParams();
  param.set(CHANGELIST_FILTERS_PARAM, preserved);
  return `${targetPath}${sep}${param.toString()}`;
}
