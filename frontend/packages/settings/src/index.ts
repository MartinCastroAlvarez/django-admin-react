// @dar/settings — the Settings dialog + the appearance (theme) state it
// owns. Isolated so the modal can grow its own per-user preference
// surface without touching the app shell or the sidebar.

export { SettingsModal } from './SettingsModal';
export {
  applyTheme,
  getStoredTheme,
  initTheme,
  resolveTheme,
  setTheme,
  systemTheme,
  type Theme,
} from './theme';
