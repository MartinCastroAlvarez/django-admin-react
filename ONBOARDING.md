# Onboarding

> The whole reason this project exists: a Django developer should
> install one package and feel like they got a modern admin UI for
> free. This file is the **five-minute path** to that experience,
> plus the failure modes you might hit on the way.

Owner: `claude-pm-ux-opus47` (Product / UX).
Last reviewed: 2026-05-25.

If you take longer than five minutes to finish §1 on a clean Django 5
project, that is a **P0 onboarding bug**. Please open an issue.

---

## 1. The five-minute path

### Prerequisites

- Python ≥ 3.10.
- Django ≥ 5.0 already installed in your project.
- A staff user (`is_staff=True`) you can log in as.

You do **not** need Node, pnpm, or any JavaScript tooling. The
package ships the pre-built React bundle inside the Python wheel.

### Step 1 — Install (30 seconds)

```bash
pip install django-admin-react
```

> Until v0.1.0 ships on PyPI, install from source:
>
> ```bash
> pip install "git+https://github.com/MartinCastroAlvarez/django-admin-react@main"
> ```

### Step 2 — Add to `INSTALLED_APPS` (15 seconds)

```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_admin_rest_api",   # ← the JSON REST API (sibling package, auto-installed as a dependency)
    "django_admin_react",      # ← this package — the React SPA
    # ... your own apps
]
```

That's the whole settings change. No `MIDDLEWARE` change required —
we rely on the same session and CSRF middleware Django's admin uses.

> **Why two apps?** `pip install django-admin-react` pulls in
> [`django-admin-rest-api`](https://pypi.org/project/django-admin-rest-api/)
> automatically (it's a declared dependency). The two `INSTALLED_APPS`
> entries are the **only** thing you do differently — the API and the
> SPA are otherwise transparent to your project. See
> [`PRODUCT_VISION.md`](PRODUCT_VISION.md) for why we ship as two
> packages.

### Step 3 — Mount the URLs wherever you want (15 seconds)

```python
# urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Option A — replace the HTML admin entirely:
    path("admin/", include("django_admin_react.urls")),

    # Option B — keep both, side-by-side:
    path("admin/", admin.site.urls),
    path("admin/react/", include("django_admin_react.urls")),

    # Option C — any prefix you like:
    # path("staff/", include("django_admin_react.urls")),
]
```

The package never hardcodes its mount path. The SPA reads it from
the request and builds links relative to wherever you put it.

### Step 4 — Run (10 seconds)

```bash
python manage.py runserver
```

### Step 5 — Log in (4 minutes for first-time exploration)

Open `http://127.0.0.1:8000/<your-mount>/` and log in with your
existing staff credentials. You should see:

- A sidebar listing every app that has at least one model
  registered with the configured `AdminSite`.
- For each app, a list of models filtered by your
  `has_module_permission` and `has_view_permission`.
- A list page per model, paginated, with the columns from
  `ModelAdmin.get_list_display`.
- A detail page per object that mirrors `ModelAdmin.get_fields`.

If your existing `ModelAdmin` classes already configure
`list_display`, `search_fields`, `readonly_fields`, `exclude`, and
`has_*_permission`, the SPA picks all of that up automatically.

You do **not** need to register your models with the React app.
There is nothing to register. The React app reads `admin.site._registry`
on every request.

---

## 2. What you get without writing any React code

| You change                                      | The SPA reflects                                         |
| ----------------------------------------------- | -------------------------------------------------------- |
| Add a `ModelAdmin` for a new model              | The model appears in the sidebar on the next request.    |
| Edit `list_display`                             | New columns appear on the list page; old ones disappear. |
| Edit `search_fields`                            | A search box appears (or disappears).                    |
| Edit `readonly_fields` / `get_readonly_fields`  | Fields become read-only labels in the detail form.       |
| Edit `exclude` / `get_exclude`                  | Fields disappear from the detail form.                   |
| Override `has_add_permission`                   | The "Add" button is hidden when it returns `False`.      |
| Override `has_change_permission`                | The detail form is read-only when it returns `False`.    |
| Override `has_delete_permission`                | The "Delete" button is hidden when it returns `False`.   |
| Override `has_view_permission`                  | The model disappears from the sidebar.                   |
| Override `get_queryset`                         | Your filtering is applied — both for list and for detail.|

Everything you customise on the Django side propagates to the React
side on the next request. No frontend rebuild. No client-side
configuration.

---

## 3. Optional configuration

If you don't add this block, sensible defaults apply. You only need
the keys you want to override.

```python
# settings.py
DJANGO_ADMIN_REACT = {
    "ADMIN_SITE": "django.contrib.admin.site",  # dotted path
    "DEFAULT_PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 200,
    "ENABLE_PROFILING": False,
}
```

| Key                  | Default                          | Effect                                                       |
| -------------------- | -------------------------------- | ------------------------------------------------------------ |
| `ADMIN_SITE`         | `"django.contrib.admin.site"`    | Dotted path to your `AdminSite`. Override if you registered a custom site. |
| `DEFAULT_PAGE_SIZE`  | `25`                             | Rows per page on a list view if the user doesn't override.    |
| `MAX_PAGE_SIZE`      | `200`                            | Hard cap on page size; client requests above this are clamped.|
| `ENABLE_PROFILING`   | `False`                          | Reserved (no effect in v1).                                  |

We will not add more keys casually. Each new setting needs to be
defended in [`docs/agents/open-questions.md`](docs/agents/open-questions.md).

---

## 4. Authentication

The package uses Django's session middleware. Whoever is logged in
at `/admin/` is logged in at `/admin/react/` (or wherever you
mounted it). There is no second login flow.

Default access rule:

```text
request.user.is_active AND request.user.is_staff
AND admin_site.has_permission(request)
```

If you have customised your `AdminSite.has_permission` (e.g., to
allow non-staff users with a specific role), the package follows
your decision — we never override it.

If a user is not allowed:

- Anonymous → redirect to `settings.LOGIN_URL` (default `/admin/login/`).
- Authenticated but not allowed → JSON `403` with the package's
  canonical error envelope.

---

## 5. Common pitfalls

Three real ones a Django dev is likely to hit. Each takes < 60 s to
diagnose if you read this list first.

### 5.1 "I see a JSON 403 instead of the SPA"

**Cause.** You're logged in but not `is_staff`, or your custom
`AdminSite.has_permission` returned `False`.

**Fix.** Make the user staff (`u.is_staff = True; u.save()`) and
retry. If you've customised `AdminSite.has_permission`, double-check
its logic for the current user.

### 5.2 "I get redirected to `/admin/login/` but I just want to use a different login"

**Cause.** The package uses `settings.LOGIN_URL` (Django's standard
key). It does not ship its own login page.

**Fix.** Set `LOGIN_URL` in your settings:

```python
LOGIN_URL = "/accounts/login/"
```

That's the same key the HTML admin honours. Everything else flows
through your auth backend.

### 5.3 "The sidebar is empty"

**Cause.** Either:

- You haven't run `python manage.py migrate` and `admin.site.autodiscover()`
  hasn't picked up your `admin.py` files yet (rare in dev mode), or
- Your current user lacks `has_module_permission` for any app.

**Fix.** Confirm:

```bash
python manage.py shell -c "from django.contrib import admin; print(list(admin.site._registry.keys()))"
```

If that list is empty, your `admin.py` files aren't being
imported — check your app's `apps.py` is in `INSTALLED_APPS`. If
the list is non-empty but the SPA still says "no models", the
current user doesn't have permission for any of them — check
`has_module_permission` and `has_view_permission`.

### 5.4 "I'm behind a reverse proxy that strips `/admin/react/`"

**Cause.** The package derives the mount path from `request.path`.
If the proxy strips the prefix, the SPA builds wrong links.

**Fix.** Use Django's `FORCE_SCRIPT_NAME` (or your proxy's
`X-Forwarded-Prefix` handling) to restore the path. Detailed steps
in Django's deployment docs.

---

## 6. Reverse-proxy / production deployment

The package serves static assets out of
`django_admin_react/static/admin_react/`. In production:

```bash
python manage.py collectstatic --no-input
```

Then serve `STATIC_ROOT/admin_react/` like any other Django static
asset (CDN, WhiteNoise, nginx, etc.). The package does **not**
require WhiteNoise.

`SECURE_PROXY_SSL_HEADER`, `SECURE_HSTS_SECONDS`, `CSRF_TRUSTED_ORIGINS`,
and friends apply as usual — the SPA respects Django's CSRF and
session cookies exactly like the HTML admin does.

---

## 7. What you should **not** do

To keep this experience plug-and-play, please do not:

- Edit any file under `frontend/` (it's the source of the bundle
  shipped in the wheel; consumers should never need it).
- Register models "with the React app". There is no such
  registration — the package reads your existing
  `admin.site._registry`.
- Disable CSRF on the package's endpoints.
- Override the package's API URLs. The shape is documented in
  [`docs/api-contract.md`](docs/api-contract.md) and is the
  contract the SPA depends on.

If you find yourself wanting to do any of these, open an issue
first — it likely means we missed something that should be a
first-class `ModelAdmin` extension instead.

---

## 8. What's next

- [`PRODUCT_VISION.md`](PRODUCT_VISION.md) — why this exists and
  what it tries to be.
- [Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
  — what's coming, by Phase.
- [`docs/api-contract.md`](docs/api-contract.md) — the wire
  protocol the SPA uses (relevant only if you're curious or
  contributing).
- [`docs/ux/`](docs/ux/) — UX rules that govern the shipped UI.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to contribute back.

---

## 9. Telling us when it didn't take five minutes

If installation took longer than five minutes on a clean project,
that is a bug worth reporting. The fastest way:

1. Open `https://github.com/MartinCastroAlvarez/django-admin-react/issues/new`
2. Title: `onboarding: <step that took too long>`
3. Body: copy the commands you ran and the time each step took. We
   measure ourselves against this number; your data shapes v1.x.
