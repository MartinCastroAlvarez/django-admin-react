<!--
  Thanks for opening a PR. Please fill this out so reviewers (human and AI)
  have the context they need. Sections marked (required) cannot be empty.
-->

## Summary (required)

<!-- 1-3 sentences. What changed and why. -->

## Linked planning artifacts (required)

- `PLAN.md` PR slot: <!-- e.g. PR #3 -->
- `ARCHITECTURE.md` section(s): <!-- e.g. §4.1 -->
- `docs/api-contract.md` section(s) touched (or "n/a"):
- `docs/agents/decisions.md` entry (or "n/a"):

## Type of change (required)

- [ ] Documentation only
- [ ] New feature
- [ ] Bug fix
- [ ] Refactor (no behavior change)
- [ ] Chore / tooling
- [ ] Security fix (please mark and follow `SECURITY.md` §4)

## Tests (required)

- [ ] I added tests for new behavior
- [ ] I updated tests for changed behavior
- [ ] Test matrix from `SECURITY.md` §3 is covered for any new
      endpoint (or "n/a")
- [ ] CI is green

## Security checklist

- [ ] No secrets introduced (`.env`, tokens, keys, etc.)
- [ ] No bypass of CSRF, auth, or ModelAdmin permissions
- [ ] No `Model.objects.all()` in API code
- [ ] No model-specific names in `django_admin_react/` or
      `frontend/packages/`

## Agent coordination

If you are an AI agent:

- [ ] I have read `CLAUDE.md` and `docs/agents/decisions.md` since my
      last session
- [ ] I claimed scope in `forum/` if this PR touches non-trivial files
- [ ] I updated `docs/agents/changelog.md` with a one-liner

## Screenshots / curl examples

<!-- Optional. Helpful for UI / API changes. -->

## Notes for reviewers

<!-- Anything to call out, alternatives considered, open questions. -->
