# PROGRESS

Live status of `django-admin-react`. Update this file in the same PR
as any meaningful milestone. The Merger appends a row to the table
below on every merge.

> For per-PR detail see [`docs/agents/changelog.md`](docs/agents/changelog.md).

---

## v1 milestone progress

| Milestone                                                        | Status        | Where               |
| ----------------------------------------------------------------- | ------------- | ------------------- |
| Foundation docs (`ARCHITECTURE`, `PLAN`, `SECURITY`, `CLAUDE`, …) | ✅ Merged     | PR #1 (`5812ad2`)   |
| Autonomous PR ops protocol + autonomy policy                      | ✅ Merged     | PR #4 (`d36ed2c`)   |
| Example Django apps (fintech, library, blog, ecommerce, hr)       | ✅ Merged     | PR #5 (`df0c53c`)   |
| Cleanup: scrub partial-token + drop CI draft                      | ✅ Merged     | PR #7 (`d37495b`)   |
| Local linter stack + `scripts/{lint,build,deploy}.sh`             | ✅ Merged     | PR #8 (`95d6db2`)   |
| `GET /api/v1/registry/` endpoint                                  | 🟡 In flight | `pr/03-registry-endpoint` branch |
| `GET /api/v1/<app>/<model>/` (list)                               | ⬜ Pending    | PR #4 in `PLAN.md` §2 |
| `GET /api/v1/<app>/<model>/<pk>/` (detail)                        | ⬜ Pending    | PR #4 in `PLAN.md` §2 |
| Create / update / delete endpoints                                | ⬜ Pending    | PR #5 in `PLAN.md` §2 |
| Frontend shell (`@dar/web` + Vite + router + auth boundary)     | ⬜ Pending    | PR #6 in `PLAN.md` §2 |
| Frontend pages (`@dar/list`, `@dar/details`, `@dar/models`)       | ⬜ Pending    | PR #7 in `PLAN.md` §2 |
| Frontend forms + `@dar/data` (SWR + debounced mutations)          | ⬜ Pending    | PR #7 in `PLAN.md` §2 |
| Example apps wired to the React admin + screenshots in README     | ⬜ Pending    | PR #8 in `PLAN.md` §2 |
| First PyPI release (`0.1.0`)                                      | ⬜ Pending    | Requires repo-owner approval + token |

Legend: ✅ done · 🟡 in flight · ⬜ pending · ❌ blocked

---

## Quality gates (current snapshot)

The Merger runs these locally before each merge (no CI by design):

| Tool                             | Status        | Latest output (commit)          |
| -------------------------------- | ------------- | -------------------------------- |
| `ruff check`                     | ✅ green      | `95d6db2`                        |
| `ruff format --check`            | ✅ green      | `95d6db2`                        |
| `black --check`                  | ✅ green      | `95d6db2`                        |
| `isort --check-only` (one-per-line) | ✅ green   | `95d6db2`                        |
| `flake8`                         | ✅ green      | `95d6db2`                        |
| `pylint --errors-only`           | ✅ green      | `95d6db2`                        |
| `mypy`                           | ✅ no issues  | `95d6db2`                        |
| `bandit -r django_admin_react`   | ✅ green      | `95d6db2`                        |
| `pytest`                         | ✅ 11 pass, 95% cov | `95d6db2`                  |
| `prettier --check` (frontend)    | ⬜ pending    | wired in PR #6                   |
| `pnpm -r typecheck`              | ⬜ pending    | wired in PR #6                   |
| `pnpm -r lint`                   | ⬜ pending    | wired in PR #6                   |

---

## Screenshots

| Screenshot                                         | Status      | Source                                                              |
| -------------------------------------------------- | ----------- | ------------------------------------------------------------------- |
| `01-admin-login.png`                               | ✅ shipped  | `scripts/screenshots.sh` (PR `feat/pm-screenshots-real`).            |
| `02-admin-index.png`                               | ✅ shipped  | same.                                                                |
| `03-admin-library-list.png`                        | ✅ shipped  | same.                                                                |
| `04-admin-library-list-mobile.png`                 | ✅ shipped  | same.                                                                |
| `05-admin-library-detail.png`                      | ✅ shipped  | same.                                                                |
| `06-registry-api-json.png`                         | ✅ shipped  | same.                                                                |
| React SPA captures (registry / list / detail / mobile / dark / login) | ⬜ pending | Frontend PR #6 / #7. Same script regenerates.   |

The current set shows the **legacy HTML admin** running against
the example apps — i.e., the experience the React UI modernises.
Regenerate via `bash scripts/screenshots.sh`.

---

## v0.1 PM / UX criteria lane

The PM/UX role tracks `ACCEPTANCE.md` §2 against the same milestone
lens as the engineering lane. Live status board:
[`docs/pm-acceptance-status.md`](docs/pm-acceptance-status.md).

Headline numbers (2026-05-26):

- ✅ verified — 10 criteria (mostly §2.1, §2.6, onboarding docs).
- 🟡 partial — 9 criteria (need frontend + PyPI release to flip).
- ⬜ blocked on frontend — the rest (~25), per
  [`PLAN.md`](PLAN.md) §2 PR #6 / #7.

The v0.1 release gate (`ACCEPTANCE.md` §5) cannot pass until the
frontend lands. Every PM doc / spec / screenshot that does **not**
depend on the SPA is shipped or in review.

---

## How to use this file

- The Merger appends a row to the milestone table on every merge.
- The Merger updates the "Quality gates" snapshot with the commit
  SHA that passed each tool.
- The Author can pre-mark a milestone as 🟡 when opening a PR; the
  Merger flips it to ✅ on merge.
- Do not log secrets, customer data, or anything that should not be
  in a public open-source repo.
