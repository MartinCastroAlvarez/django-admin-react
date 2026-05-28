// Central registry of every localStorage key that holds a UI
// *customization* — a per-device preference the operator sets (theme,
// hidden columns, saved filters, collapsed sections).
//
// This is deliberately separate from the server-data cache
// (`dar:registry:v1`, `dar:list:v1`, `dar:detail:v1:*`) owned by
// `@dar/data`: that's cached API responses, not preferences. Keeping the
// preference keys in one place means they can't drift between the code
// that writes them and the logout purge that has to decide which survive.

/** The `dar:` prefix shared by everything this SPA stores (cache + prefs). */
export const CUSTOMIZATION_NAMESPACE = 'dar:';

/** Theme (light / dark). The one preference that survives logout. */
export const THEME_KEY = 'dar:theme';

/** Collapsed sidebar app-group labels (a Set of app labels). */
export const NAV_COLLAPSE_KEY = 'dar:nav-collapsed';

/** Pinned/favourited models on the home page (a Set of `app/model` keys). */
export const PINNED_MODELS_KEY = 'dar:pinned-models';

/** Hidden list columns for one model (a Set of column names). */
export function columnsKey(appLabel: string, modelName: string): string {
  return `dar:cols:${appLabel}:${modelName}`;
}

/** Drag-resized list column widths for one model ({ column: px }). */
export function columnWidthsKey(appLabel: string, modelName: string): string {
  return `dar:colwidths:${appLabel}:${modelName}`;
}

/**
 * Locked (frozen) non-pk list columns for one model (a Set of column
 * names). The pk column is implicitly always locked (never stored in
 * this set). Locked columns must form a contiguous prefix starting
 * from the pk — the modal's lock/unlock actions enforce that by
 * setting / clearing every column between the pk and the target.
 *
 * Persisted separately from `columnsKey` (hidden) and the column-order
 * list so the three preferences can evolve independently.
 */
export function lockedColsKey(appLabel: string, modelName: string): string {
  return `dar:colslocked:${appLabel}:${modelName}`;
}

/** Persisted `list_filter` selections for one model. */
export function filtersKey(appLabel: string, modelName: string): string {
  return `dar:filters:${appLabel}:${modelName}`;
}

/** Collapsed state of one detail-page fieldset section. */
export function detailCollapseKey(
  appLabel: string,
  modelName: string,
  index: number,
  title: string,
): string {
  return `dar:detail-collapsed:${appLabel}:${modelName}:${index}-${title}`;
}

/**
 * Customization keys that survive logout — pure display preferences with
 * no session or data content. Everything else under the namespace
 * (cached data AND per-model prefs that reveal what the previous user was
 * viewing) is purged on sign-out; see `@dar/data`'s cache purge.
 */
export const PRESERVED_ON_LOGOUT: readonly string[] = [THEME_KEY];
