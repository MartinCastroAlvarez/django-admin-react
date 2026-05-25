# examples/ — demo Django projects

This directory holds full, runnable Django projects that exercise
`django-admin-react` against realistic domains. These projects are
**not** packaged with the PyPI artifact. They are here so that:

1. Contributors have a working environment to develop against.
2. Reviewers can `cd examples/<name> && runserver` and click around.
3. Screenshots / docs can be generated from realistic data.

Each example is a standalone Django project that depends on the
package locally (via Poetry path dependency).

## Planned examples (land in PR #8)

| Folder              | Domain                  | Models                                                            |
| ------------------- | ----------------------- | ----------------------------------------------------------------- |
| `fintech/`          | Banking-style fintech   | `Account`, `Transaction`, `Statement`, `Customer`, `Card`         |
| `library/`          | A small library         | `Author`, `Book`, `Publisher`, `Genre`, `Loan`                    |
| `blog/`             | Multi-author blog       | `Post`, `Comment`, `Tag`, `Category`, `Author`                    |
| `ecommerce/`        | Tiny e-commerce         | `Product`, `Order`, `OrderItem`, `Customer`, `Inventory`          |

Each project demonstrates a different aspect of `ModelAdmin`:

- `fintech` — custom `get_queryset`, conservative permissions,
  read-only `Statement.line_items`.
- `library` — heavy use of `search_fields`, M2M (`Book.authors`)
  surfaced as `unsupported` in v1.
- `blog` — per-author `has_change_permission` (only your own posts).
- `ecommerce` — admin actions (deferred to v1.x; included as a
  forward-compat check).

## Running an example

```bash
cd examples/fintech
poetry install                       # picks up django-admin-react via path dep
poetry run python manage.py migrate
poetry run python manage.py loaddata sample_data.json
poetry run python manage.py createsuperuser
poetry run python manage.py runserver
```

Then visit the URL configured in that project's `urls.py`.

## Rules

- Example projects may use Django freely (signals, custom widgets,
  middleware, …). The point is to stress-test the package.
- Example **models** may have names like `Account`, `Book`,
  `Transaction`. The package code and React packages may **not**.
- Sample data must be synthetic. No real names, emails, accounts, IBANs,
  card numbers, or secrets.
- Each example folder has its own `README.md` explaining its domain,
  how to seed data, and which ModelAdmin features it exercises.

## Status

Example projects are out of scope for PR #1. Folder stubs (this README)
land in PR #1 to keep the layout discoverable. The individual projects
land in PR #8.
