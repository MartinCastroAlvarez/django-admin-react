# @dar/settings

The **Settings dialog** and the user-preference state it owns.

## What lives here

- `SettingsModal.tsx` — the dialog opened from the sidebar cog. Built on
  the shared `@dar/ui` `Modal` so it matches every other confirm/overlay
  in the SPA. Today it holds the appearance (light / dark) toggle; it is
  the home for future per-user UI preferences.
- `theme.ts` — the light/dark preference: read/resolve (saved choice →
  system default), persist to the `dar:theme` localStorage key, and
  apply by toggling the `.dark` class on `<html>`. `initTheme()` is
  called once by the app before first paint (no flash).

## What does NOT belong here

- Model-aware logic or anything that talks to the API. This package is
  pure UI preference; it imports only `@dar/ui` (+ React / lucide).
- The sidebar chrome that *opens* the modal — that's `@dar/sidebar`.
- The `.dark` utility remap CSS — that stays in the app's `index.css`
  (Tailwind layer), since it's global styling, not component logic.

## Pointers

- Rendered by `@dar/sidebar` (the cog button) and bootstrapped by
  `apps/web/src/main.tsx` (`initTheme`).
- Data-flow rule: a UI package never imports `@dar/api` (CLAUDE.md §7).
