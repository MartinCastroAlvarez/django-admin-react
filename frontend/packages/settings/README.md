# @dar/settings

The **identity dropdown panel** (theme + sign out) and the
user-preference state it owns.

## What lives here

- `AccountMenu.tsx` — the dropdown panel rendered inside the sidebar's
  email-with-caret button (`#578`). Holds the appearance (light / dark)
  toggle and the Sign out action. The component is the **panel body
  only**; the consumer wraps it in the shared `@dar/ui` `Popover` so
  outside-click + Escape close behaviour is inherited from the same
  primitive the list-page Actions menu uses.
- `theme.ts` — the light/dark preference: read/resolve (saved choice →
  system default), persist to the `dar:theme` localStorage key, and
  apply by toggling the `.dark` class on `<html>`. `initTheme()` is
  called once by the app before first paint (no flash).

## What does NOT belong here

- Model-aware logic or anything that talks to the API. This package is
  pure UI preference; it imports only `@dar/ui` (+ React / lucide).
- The sidebar chrome that *mounts* the panel — that's `@dar/sidebar`.
- The `.dark` utility remap CSS — that stays in the app's `index.css`
  (Tailwind layer), since it's global styling, not component logic.

## Pointers

- Rendered by `@dar/sidebar` (the identity dropdown) and bootstrapped by
  `apps/web/src/main.tsx` (`initTheme`).
- Data-flow rule: a UI package never imports `@dar/api` (CLAUDE.md §7).

## History

- v1.0.3: replaced the prior `SettingsModal` with `AccountMenu`. The
  modal-around-two-controls was heavier than warranted; the dropdown
  is the right primitive for a profile menu.
