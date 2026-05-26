# Architect review — PR `feat/pm-screenshots`

Posted: 2026-05-26
Reviewer: claude-architect (delegated by PM session for review-gathering cycle)
Tier: 1 originally — docs/screenshots, docs/ux, scripts
Tip commit: `5c7f3ed feat(api): list endpoint + conservative serializer`
PM approval: n/a
Security approval: n/a

## Status: **STALE — superseded by `feat/pm-screenshots-real`**

The PM has shipped a fresher version at `feat/pm-screenshots-real`
that:

- Contains real Playwright screenshots (6 PNGs).
- Has clean PR scope (no copy of the list-endpoint code).
- Has gitignore + script hardening from review feedback.

This older `feat/pm-screenshots` branch **also contains** the list
endpoint code (`django_admin_react/api/views/list.py`, the
`serializers.py` rewrite, and the registry tweaks) — i.e., it
overlaps with `feat/backend-list-detail-endpoints`. That dual scope
is the reason a re-do branch (`-real`) was opened.

## §5.1 checklist (quick)

- [⚠️] Multi-feature scope: PM screenshots + backend list endpoint
  in the same PR. CLAUDE.md §3 "One PR per branch" — ❌.
- The list-endpoint content is duplicated and superseded by PR #4
  (`feat/backend-list-detail-endpoints`).

## Recommendation

**Close.** PM has already shipped the clean re-do at
`feat/pm-screenshots-real`. Reviewing this older one would only
re-litigate the multi-scope issue.

## Verdict

**Close as superseded** (replaced by `feat/pm-screenshots-real`).

— claude-architect
