# PM/UX — DECISIONS

Append-only log of decisions made by the PM/UX role. Newest on top.
Repo-wide architectural decisions also link from
[`docs/agents/decisions.md`](../../docs/agents/decisions.md) with a
`[PM]` tag.

---

## 2026-05-26 — Late-sprint decisions

Authoring session: `claude-pm-ux-opus47-2026-05-26`.

1. **Reviews land as `--comment`, not `--approve`** — codified in
   [`AGENT.md`](AGENT.md) §9.5.1. All agents auth as one GitHub
   login; GitHub blocks self-approve. The autonomy-policy counts
   the body substance + agent-id role, not the GitHub UI state.
   Mergers read body verdicts.
2. **Periodic GitHub sweep cadence is mandatory** — codified in
   [`AGENT.md`](AGENT.md) §9.5.2. PM/UX sweeps PRs / Issues /
   Discussions / Project board each session block, not just on
   direct prompts. The natural-stopping rule applies: when the
   sweep finds nothing actionable, say so explicitly.
3. **Session-expiry envelope ships at HTTP 403, not 401** — accepting
   the merged decision in PR #95. My original PR #79 proposal
   (HTTP 401) was wire-incompatible with the package's existing
   posture (all permission/auth failures at 403, `error.code` for
   nuance). The PR #79 supplement now layers on top of §6.1
   (`?next=`, optional warning endpoints, modal UX flow).
4. **`docs/agents/product-manager/STATUS.md` and `NEXT_STEPS.md`
   are required** — AGENT.md §11 referenced both since session
   start but they were missing; PR #112 creates them.
5. **v0.1.0a2 ships without the release-gate mandate firing** —
   the mandate (memory entry: pm-release-gate-mandate) applies to
   v0.1.0 **stable**, not alpha. Alpha releases proceed at the
   Releaser's discretion subject to the autonomy-policy Tier 6
   rules.
6. **PR #100 (Architect's M2M, original) was closed and superseded
   by PR #107** — PM/UX-angle approve via comment review was
   carried forward by the Architect into the rebased PR.
7. **`ACCEPTANCE.md` §2 refresh is a recurring PM/UX duty** — every
   sprint where backend features land, PM/UX refreshes §2 against
   what shipped (promote §2.10 non-goals into §2.9 E-rows, add
   §2.7 N-rows, etc.). PR #104 is the 2026-05-26 sprint instance.

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
12. **No `--force` push to `main`. No CI/CD (per repo-owner direction).**
    Local linters via `scripts/lint.sh` are the gate.
    — [`docs/agents/decisions.md`](../../docs/agents/decisions.md) (engineering)
13. **`docs/agents/` handoff convention adopted** — durable role state
    survives session loss. — [`docs/agents/decisions.md`](../DECISIONS.md)

---

> Append future PM/UX decisions above this line, newest on top.
> One-to-two lines each; link out for detail. Tag cross-role
> decisions with `[PM+Architect]`, `[PM+Security]`, etc.
