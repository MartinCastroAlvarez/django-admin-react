# Architect-owned decisions

> Append-only. Newest on top. Each entry links to the corresponding
> cross-agent record in
> [`docs/agents/decisions.md`](../../docs/agents/decisions.md) when
> applicable.

---

## 2026-05-25

- **`ACCEPTANCE.md` §3 is the engineering bar.** Every criterion is
  binary (yes / no) and verifiable by a documented command or file
  read. Subjective language is not used. Cross-reference: this PR.
- **Coverage thresholds** (codified in §3.5 / T-2):
  - overall ≥ 90 %
  - `permissions.py` and `serializers.py`: 100 % statements + 100 %
    branches
  - `views/*`: ≥ 95 %
  Reason: these are the surfaces where a one-line regression has the
  worst blast radius.
- **Source-of-truth files for engineering** (codified in §3 head
  paragraph): `ARCHITECTURE.md`, `PLAN.md`, `TESTING.md` (to write),
  `API_CONTRACT.md` (top-level pointer to write).
- **`scripts/lint.sh` is the merge gate, `scripts/build.sh` is the
  release gate.** No GitHub Actions per repo-owner direction. To be
  revisited before leaving pre-alpha (recorded as an open question).
- **Architect does not edit §2 (PM) or §4 (Security) of
  `ACCEPTANCE.md`.** Boundary recorded here for future sessions.

---

## Pre-2026-05-25 (inherited from `docs/agents/decisions.md`)

Decisions made before this folder existed are tracked in
[`docs/agents/decisions.md`](../../docs/agents/decisions.md). The
architecture-owned subset is, in order:

- ModelAdmin is the only source of truth.
- Frontend packages: `@dar/ui`, `@dar/api`, `@dar/data`, `@dar/list`,
  `@dar/details`, `@dar/models`, `@dar/shell` (closed set; no
  "mega-monster" package).
- `@dar/data` is the only package that imports `@dar/api`; UI
  packages go through `@dar/data`.
- Settings live under a single optional dict
  `settings.DJANGO_ADMIN_REACT`.
- Mount point is consumer-chosen; the package hardcodes no URL.
- Conservative serializer with `str()` fallback.
- The PyPI artifact ships pre-built React assets — no Node required
  on the consumer side.
- Poetry for Python, pnpm for frontend. No mixing.
- v1 is small: inlines, custom actions, bulk actions, custom widgets,
  autocomplete, raw_id, and any React-side extension API are
  explicitly deferred.

If any of those needs revisiting, open an entry in
[`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) and propose a follow-up PR;
do not silently change the implementation.
