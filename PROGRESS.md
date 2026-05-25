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

Real screenshots will land in the PR that lights up the React UI
(PR #6 / #7 per `PLAN.md` §2). Until then the README ships ASCII
mockups that match the API contract exactly so reviewers can sanity-
check the expected layout against `docs/api-contract.md`.

---

## How to use this file

- The Merger appends a row to the milestone table on every merge.
- The Merger updates the "Quality gates" snapshot with the commit
  SHA that passed each tool.
- The Author can pre-mark a milestone as 🟡 when opening a PR; the
  Merger flips it to ✅ on merge.
- Do not log secrets, customer data, or anything that should not be
  in a public open-source repo.
