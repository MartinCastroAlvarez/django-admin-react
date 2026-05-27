# django_admin_react/api/

JSON API package. See [`/docs/api-contract.md`](../../docs/api-contract.md)
for the wire format and [`/ARCHITECTURE.md`](../../ARCHITECTURE.md) §4 for
the design.

## Rules

- Every view consults `ModelAdmin` for permissions, queryset, form,
  serialization. No exceptions.
- No direct `Model.objects.all()` — start from
  `ModelAdmin.get_queryset(request)`.
- Client-provided `app_label`/`model_name` are resolved through
  `admin.site._registry` only.
- CSRF on unsafe methods. Never exempt yourself.
- Conservative serializer with `str()` fallback (see
  `serializers.py`).
- A denylist of sensitive-shaped field names is applied on top of the
  admin form's own exclusion (defense in depth).

## Layout

| File              | Purpose                                                      |
| ----------------- | ------------------------------------------------------------ |
| `urls.py`         | URL patterns for all API endpoints.                          |
| `permissions.py`  | Staff + AdminSite.has_permission gate; per-op delegation.    |
| `registry.py`     | AdminSite introspection helpers.                             |
| `serializers.py`  | Conservative field serialization + denylist.                 |
| `custom_views.py` | Surface a ModelAdmin's custom `get_urls()` routes (#439).    |
| `views/`          | One module per endpoint.                                     |

Implementation status is tracked in `../README.md`.
