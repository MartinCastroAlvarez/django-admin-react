# docs/screenshots/

Screenshot inventory + naming contract for the README and product
docs.

Owner: PM/UX role ([`docs/agents/product-manager/AGENT.md`](../../docs/agents/product-manager/AGENT.md)).
Producing role: Frontend Engineer (PR #6 / #7 in
[`PLAN.md`](../../PLAN.md)).

The screenshots **do not yet exist** at the time of writing — the
SPA isn't implemented. This file is the contract the frontend PR
fulfils.

---

## 1. Why screenshots are part of acceptance

[`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.3 criterion O-2 requires
the README to show six screenshots. Without them, a Django dev
hitting the GitHub page can't tell what the SPA looks like, which
breaks the cardinal onboarding moment.

---

## 2. Required screenshots for v0.1

| Filename                                                 | Description                                                                                 | Viewport       | Theme |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------- | ----- |
| `01-registry-desktop-light.png`                          | Registry page (sidebar + main) showing the `library` and `fintech` example apps.            | 1440 × 900     | light |
| `02-list-library-author-desktop-light.png`               | List view of `library.Author` — search bar, columns from `list_display`, pagination.        | 1440 × 900     | light |
| `03-detail-library-book-desktop-light.png`               | Detail view of a `library.Book` — fieldsets, ForeignKey field, save button bar.             | 1440 × 900     | light |
| `04-list-library-book-mobile-light.png`                  | Same list as 02 but at mobile width — table collapsed to cards.                             | 375 × 812      | light |
| `05-registry-desktop-dark.png`                           | Registry page in dark mode. Same content as 01.                                             | 1440 × 900     | dark  |
| `06-login-redirect.png`                                  | First visit while logged-out — the Django admin login page after redirect.                  | 1280 × 720     | light |

All six together form the README screenshot grid (§5 below).

### Stretch / nice-to-have (not release-blocking)

| Filename                                                 | Description                                                                                |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `07-create-library-book-mobile-light.png`                | The create form at mobile width.                                                           |
| `08-error-validation-light.png`                          | A failed save with field-level errors visible.                                             |
| `09-empty-state-no-models.png`                           | Registry empty state for a staff user with no view permissions.                            |

---

## 3. Naming convention

```
<NN>-<screen>-<context>-<viewport>-<theme>.png
```

- `NN` — two-digit index matching the order in §2.
- `screen` — `registry`, `list`, `detail`, `create`, `delete-confirm`,
  `login-redirect`, `empty-state`, `error`.
- `context` — model identifier (`library-author`, `library-book`,
  `fintech-account`) when applicable; omit for registry / login.
- `viewport` — `desktop` (≥ 1280 px), `tablet` (768-1023 px),
  `mobile` (< 640 px).
- `theme` — `light` or `dark`.

No PascalCase, no spaces, no emoji in filenames.

---

## 4. Production rules

### 4.1 Source

- Captured against the `examples/library/` and `examples/fintech/`
  apps, seeded with the fixture set defined in
  [`docs/ux/primary-flows.md`](../ux/primary-flows.md).
- Captured at **2x device pixel ratio** (Retina equivalent). The PNG
  files end up at the listed viewport × 2 dimensions; HTML displays
  them at the natural width.
- Captured on Chrome stable. We do not ship Firefox / Safari
  variants — the SPA is browser-agnostic and the screenshots are
  marketing collateral, not test fixtures.

### 4.2 Size budget

- **≤ 200 KB optimised** per file. Run through `pngquant` or
  `oxipng` (lossless).
- Total folder size budget: **≤ 2 MB** in the repo. If we hit it,
  switch the README to link to a hosted gallery.

### 4.3 Privacy and licensing

- Use only the seeded fixture data. No real names, emails, account
  numbers — the fixtures in `examples/` are deliberately
  synthetic.
- The screenshots are MIT-licensed alongside the rest of the repo.

### 4.4 Reproducibility

A `scripts/screenshots.sh` (lands with PR #6) regenerates the full
set from the running test_project. The script:

- Boots the test_project on a known port.
- Seeds the library + fintech fixtures.
- Logs in as a known superuser.
- Walks through the screen list via Playwright.
- Writes the PNGs into this folder.
- Runs `oxipng` on each.

If a screenshot is out of date, regenerate the whole set — never
edit a screenshot manually.

---

## 5. README grid layout

```markdown
## Screenshots

| Registry · Light | Registry · Dark |
| ----------------- | ---------------- |
| ![](docs/screenshots/01-registry-desktop-light.png) | ![](docs/screenshots/05-registry-desktop-dark.png) |

| Author list · Desktop | Book detail · Desktop |
| ---------------------- | ---------------------- |
| ![](docs/screenshots/02-list-library-author-desktop-light.png) | ![](docs/screenshots/03-detail-library-book-desktop-light.png) |

| Book list · Mobile | Login redirect |
| ------------------- | --------------- |
| ![](docs/screenshots/04-list-library-book-mobile-light.png) | ![](docs/screenshots/06-login-redirect.png) |
```

The frontend PR adds this grid to `README.md` (between the
"Install in your Django project" and "Configure" sections — the
top-of-fold spot).

---

## 6. Acceptance cross-reference

| Topic                            | Criterion         |
| -------------------------------- | ----------------- |
| Six screenshots in the README    | O-2               |
| ≤ 200 KB per file                | O-2 / regression  |
| Generated from seeded fixtures   | Doc-2, Q-PM-01    |
| Light + dark variant in the grid | A-7, V-5          |
| Mobile screenshot present        | R-1, R-2          |
