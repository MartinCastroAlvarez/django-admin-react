# examples/hr — HR demo app

An HR-style domain with departments, roles, employees, time-off
requests, and a **restricted** performance-review model.

## What's here

- `models.py` — `Department`, `Role`, `Employee`, `TimeOffRequest`,
  `PerformanceReview`.
- `admin.py` — exercises three high-value contract points:
  1. **Module-level permission gating**:
     `PerformanceReviewAdmin.has_module_permission` returns `False` for
     non-superusers. The React UI's registry endpoint must omit this
     model entirely for non-superusers — not even hint that it exists.
  2. **Per-method permission gating**: all five `has_*_permission`
     methods are explicitly restricted. Even a malicious client that
     guesses the URL gets `403`.
  3. **Field-level visibility based on user**:
     `EmployeeAdmin.get_readonly_fields` / `get_exclude` add `salary`
     for non-superusers. The serializer must respect the resolved
     exclude list **per request**, not statically.

## Why this app demonstrates the design

This is the most important test case for the security claims in
`SECURITY.md` §3. If `PerformanceReview` or `Employee.salary` ever
leaks to a non-superuser through any endpoint, the package has a
serious bug.

## Required test coverage

When PR #3 / #4 / #5 land, these tests **must** be added in
`tests/test_project/` (or wherever the integration suite lives):

- A staff (non-superuser) calling `GET /api/v1/registry/` does **not**
  see `hr.performancereview`.
- A staff (non-superuser) calling `GET /api/v1/hr/performancereview/`
  receives `403` (and a `404`-like body is acceptable to avoid leaking
  existence, but the audit log records the attempt).
- A staff (non-superuser) calling
  `GET /api/v1/hr/employee/<pk>/` receives an object whose `fields`
  dict has no `salary` key.
- A staff (non-superuser) `PATCH`ing `hr/employee/<pk>` with `{"salary":
  9999}` receives `400 bad_request` (unknown field) **and** the value
  is unchanged in the database.
