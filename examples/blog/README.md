# examples/blog — Blog demo app

A minimal CMS-like app: posts, comments, categories, and tags.
Demonstrates `SlugField`, choice-based status workflows, and
auto-populated slugs.

## What's here

- `models.py` — `Category`, `Tag`, `Post`, `Comment`.
- `admin.py` — `ModelAdmin` subclasses with `prepopulated_fields`,
  `date_hierarchy`, status filters.
- `tests/test_admin.py` — smoke test.

## Why this app demonstrates the design

- **Slug autogeneration** (`prepopulated_fields`): `Post.slug` is
  populated from `Post.title` in the admin form. The React UI mirrors
  this by computing the slug client-side on input until the user types
  in the slug field manually.
- **Choice fields** (`Post.status`): exercise the `type: "choice"`
  metadata path in `docs/api-contract.md` §4.
- **Self-referential moderation** (`Comment.is_approved`): typical
  admin checkbox. The React UI renders an inline toggle in the list
  view.
- **`PROTECT` author**: deleting a `User` is blocked if they authored a
  `Post`. The API surfaces this as `409 conflict`.

## Running

When `examples/project/` is wired up:

```bash
cd examples/project
poetry run python manage.py migrate
poetry run python manage.py runserver
```
