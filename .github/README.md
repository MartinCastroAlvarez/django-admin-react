# .github/

GitHub-specific configuration: PR/issue templates and CI workflow.

## Files

- `PULL_REQUEST_TEMPLATE.md` — opened with every PR.
- `ISSUE_TEMPLATE/` — bug report, feature request, agent question.
- `ci.yml.draft` — **draft CI workflow** (Python + frontend + secret
  scan + package build). See note below.

## Why `ci.yml.draft` and not `workflows/ci.yml`

GitHub refuses to accept workflow files pushed by a Personal Access
Token that lacks the `workflow` scope. The PAT currently used to
push this repo does not have that scope, so the workflow file is
committed as `ci.yml.draft` at the parent level.

### To activate the workflow

1. Rotate the PAT in the user's local `.git/config` to a token with
   the `workflow` scope, or switch to `gh auth login` / SSH for
   authentication.
2. Move the file into place:
   ```
   git mv .github/ci.yml.draft .github/workflows/ci.yml
   ```
3. Commit and push.

A follow-up PR can do this once the auth setup is in order.

## Workflow status badge (after activation)

```
![CI](https://github.com/MartinCastroAlvarez/django-admin-react/actions/workflows/ci.yml/badge.svg)
```
