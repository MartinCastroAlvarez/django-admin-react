# Cross-role decisions

Shared decision log across PM / Architect / Security roles. Newest
on top. Each entry: date, summary, owning role, link.

Per-role decision logs live in `agents/<role>/DECISIONS.md`.
Repo-wide architectural decisions also live in
[`docs/agents/decisions.md`](../docs/agents/decisions.md).

This file is for **cross-cutting** decisions that bind more than one
role.

---

## 2026-05-25 — Security acceptance criteria defined (`ACCEPTANCE.md` §4)

Owning role: Security & Compliance Lead (`claude-security-opus47-1`).
Summary: §4 defines 66 binary acceptance criteria (S-1 … S-66)
across authn (4.1), authz (4.2), resource exposure (4.3), queryset
protection (4.4), form & write enforcement (4.5), session / CSRF /
cookies (4.6), serialization safety (4.7), secret management & git
hygiene (4.8), dependency security (4.9), PII / fixtures (4.10),
API hardening (4.11), logging safety (4.12), release & publishing
hygiene (4.13), consumer-side secure defaults (4.14), a mandatory
per-endpoint test matrix (4.15), 8 release-blockers (4.16), and
cross-role dependencies (4.17). Resolves handoff H-2026-05-25-02.
Closely tied to handoffs H-2026-05-25-04 (E2E flow definition from
PM) and H-2026-05-25-05 (Architect sign-off pending B-7).
Affected roles: Security (owner), Architect (S-28 SpaIndexView CSRF,
S-31 serializer denylist, B-6/B-7/B-8 enforced in backend PRs),
PM/UX (S-57–S-61 release docs).
See [`ACCEPTANCE.md`](../ACCEPTANCE.md) §4 and
[`agents/security-expert/AGENT.md`](security-expert/AGENT.md).

---

## 2026-05-25 — Engineering acceptance criteria defined (`ACCEPTANCE.md` §3)

Owning role: Software Architect (`claude-architect`).
Summary: 14 sub-sections of measurable engineering criteria covering
backend, frontend, modularity, API contract, testing (incl.
coverage thresholds: ≥90 % overall, 100 % on `permissions.py` /
`serializers.py`, ≥95 % on `views/*`), lint/typecheck, packaging,
docs, SemVer, extensibility, maintainability boundaries, and an
engineering release checklist (§3.13). Resolves handoff
H-2026-05-25-03.
Affected roles: Architect (owner), PM/UX (depends on §3.5 T-5 E2E
spec for product flows), Security (depends on §3.14 cross-refs).
See [`ACCEPTANCE.md`](../ACCEPTANCE.md) §3 and
[`agents/software-architect/DECISIONS.md`](software-architect/DECISIONS.md).

---

## 2026-05-25 — `agents/` handoff convention adopted

Owning role: `claude-pm-ux-opus47` (PM/UX, scaffolding).
Summary: every long-running agent role keeps durable state in
`agents/<role>/` with `AGENT.md` as the entrypoint, so a replacement
session can resume on read-one-file.
Affected roles: PM/UX, Software Architect, Security Expert.
See [`agents/README.md`](README.md).

---

> Append future cross-role decisions above this line, newest on top.
