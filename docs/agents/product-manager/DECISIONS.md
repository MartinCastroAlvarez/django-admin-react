# PM/UX — DECISIONS

Append-only log of decisions made by the PM/UX role. Newest on top.
Repo-wide architectural decisions also link from
[`docs/agents/decisions.md`](../../docs/agents/decisions.md) with a
`[PM]` tag.

---

## 2026-05-26 — Work-priority order codified

Authoring session: `claude-pm-public-flip-2026-05-26`. Direct
repo-owner instruction, captured in `AGENT.md` §3.1.

PM/UX sessions work lanes in this order: **(1) open PRs → (2) open
issues → (3) project board → (4) Discussions → (5) acceptance
criteria.** Open PRs are first because a missing-lane review is the
most expensive thing to leave on the floor — it blocks every chain
of work behind it. ACCEPTANCE.md is last because it's a synthesis
artifact that can only reflect what already merged.

Within each lane, work the highest-impact item first (P0 → P1 → P2).
The PR-review duty (§9.5) operates inside lane 1; the periodic sweep
(§9.5.2) operates across all five lanes.

— recorded in `AGENT.md` §3.1.

---

## 2026-05-25 — Initial product baseline

Authoring session: `claude-pm-ux-opus47`.

1. **`ModelAdmin` is the only extension API in v1.** No React-side
   plugin / extension API. — [`PRODUCT_VISION.md`](../../PRODUCT_VISION.md) §3, §4
2. **Plug-and-play wins over configurability.** Only required
   config: `INSTALLED_APPS` entry + `urls.py include()`.
   — [`PRODUCT_VISION.md`](../../PRODUCT_VISION.md) §3
3. **Dark mode ships in v1.** First-paint flash is not acceptable
   (criterion A-7). — [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §3
4. **Closed component primitive set in `@dar/ui`.** No one-off
   variants in page packages.
   — [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §5
5. **Theming via CSS variables only.** Tailwind config extension is
   advanced ("fork your bundle"); runtime config swap is not in v1.
   — [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §10
6. **Acceptance criteria are measurable.** "Looks nice" / "feels
   fast" / "DX is good" are not criteria.
   — [`ACCEPTANCE.md`](../../ACCEPTANCE.md) intro
7. **`ACCEPTANCE.md` is the v1 release gate.** §5 must be ✅ for any
   tag push.
8. **The PM role can veto** changes that hurt install complexity,
   require React for Django devs, or break `ModelAdmin` mental
   models. — [`AGENT.md`](AGENT.md) §10
9. **`mount` is request-derived** in `/api/v1/registry/`, not
   configured. Documented in `ONBOARDING.md`. Resolves
   Q-2026-05-25-CX-01 (tentative).
10. **Use Lucide icons exclusively.** No emoji in shipped UI.
    — [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §7
11. **Lighthouse-equivalent budget:** FCP < 1.5 s cached, LCP < 2.5 s
    cold on the reference profile (M-class laptop, 10 Mbps).
    — [`PRODUCT_VISION.md`](../../PRODUCT_VISION.md) §7
12. **No `--force` push to `main`.** The lint + test gate runs both
    locally (`scripts/lint.sh`) and in CI (`.github/workflows/ci.yml`,
    added in #452 — the prior "no CI" stance was revisited and reversed).
    — [`docs/agents/decisions.md`](../../docs/agents/decisions.md) (engineering)
13. **`docs/agents/` handoff convention adopted** — durable role state
    survives session loss. — [`docs/agents/decisions.md`](../DECISIONS.md)

---

> Append future PM/UX decisions above this line, newest on top.
> One-to-two lines each; link out for detail. Tag cross-role
> decisions with `[PM+Architect]`, `[PM+Security]`, etc.
