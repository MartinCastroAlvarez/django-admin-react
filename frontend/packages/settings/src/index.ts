// @dar/settings — the Settings dialog + the appearance (theme) state it
// owns. Isolated so the modal can grow its own per-user preference
// surface without touching the app shell or the sidebar.

export { SettingsModal } from './SettingsModal';
// Theme state lives in @dar/customization (the home for all
// localStorage-backed UI customization); re-exported here so the app
// shell + Settings modal keep importing it from @dar/settings.
export {
  applyTheme,
  getStoredTheme,
  initTheme,
  resolveTheme,
  setTheme,
  systemTheme,
  type Theme,
} from '@dar/customization';
