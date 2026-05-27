// @dar/customization — the single home for UI customization that is
// stored/loaded from localStorage: the persistence primitive, the key
// registry, and the theme. Consumers (sidebar, list, detail, settings)
// import from here instead of hand-rolling localStorage access.

export { readString, writeString, removeKey, readJSON, writeJSON } from './storage';

export {
  CUSTOMIZATION_NAMESPACE,
  THEME_KEY,
  NAV_COLLAPSE_KEY,
  PRESERVED_ON_LOGOUT,
  columnsKey,
  filtersKey,
  detailCollapseKey,
} from './keys';

export { usePersistedState, usePersistedSet } from './use-persisted-state';

export {
  type Theme,
  getStoredTheme,
  systemTheme,
  resolveTheme,
  applyTheme,
  setTheme,
  initTheme,
} from './theme';
