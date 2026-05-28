// @dar/settings — per-user UI preferences (appearance) and session
// controls (Sign out), exposed as a dropdown panel mounted from the
// sidebar identity area (#578).

export { AccountMenu, type AccountMenuProps } from './AccountMenu';
// Theme state lives in @dar/customization (the home for all
// localStorage-backed UI customization); re-exported here so the app
// shell + AccountMenu keep importing it from @dar/settings.
export {
  applyTheme,
  getStoredTheme,
  initTheme,
  resolveTheme,
  setTheme,
  systemTheme,
  type Theme,
} from '@dar/customization';
