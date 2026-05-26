# Consumer agent — open questions

Open consumer-side questions awaiting a decision. Move accepted
answers to `DECISIONS.md` and link the PR that ratified them.

---

## Q1 — Where should "I broke the SPA at my non-root mount" findings live?

A pilot consumer flagged that the SPA's basename detection was wrong
at non-root mounts (resolved in #113 / #114 fixes). Future
mount-related friction: should it be a new issue, or a comment on a
catch-all "mount support" tracking issue?

**Current default:** file a new issue per *distinct* user-visible
symptom, link it to the open umbrella issue if one exists.

---

## Q2 — Anonymisation when the consumer-specific detail is technically load-bearing

Some consumer findings only reproduce given a specific deployment
shape (e.g. a non-default `ASGI_APPLICATION`, a custom middleware
order). Re-framing it to "generic Django consumer" loses
reproducibility detail.

**Working policy:** keep the technical detail (middleware, settings
shape, deployment topology) but strip *every* business-domain
fingerprint (app name, model names, brand, product). Test: a public
reader should be able to reproduce the bug, but not infer who I am.

Open: is there a stronger formulation? Should I post a sanitised
`settings.py` excerpt in the issue, or describe it in prose?
