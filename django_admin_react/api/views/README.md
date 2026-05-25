# django_admin_react/api/views/

One module per endpoint, mirroring [`/docs/api-contract.md`](../../../docs/api-contract.md).

| Module         | Endpoint                                          | Lands in PR |
| -------------- | ------------------------------------------------- | ----------- |
| `registry.py`  | `GET    /api/v1/registry/`                        | #3          |
| `list.py`      | `GET    /api/v1/<app>/<model>/`                   | #4          |
| `detail.py`    | `GET    /api/v1/<app>/<model>/<pk>/`              | #4          |
| `create.py`    | `POST   /api/v1/<app>/<model>/`                   | #5          |
| `update.py`    | `PATCH  /api/v1/<app>/<model>/<pk>/`              | #5          |
| `delete.py`    | `DELETE /api/v1/<app>/<model>/<pk>/`              | #5          |

Each view must:

1. Authenticate via the package's default permission helper
   (staff + `AdminSite.has_permission`).
2. Resolve the target `ModelAdmin` via `admin.site._registry`.
3. Delegate to the appropriate `ModelAdmin.*` method (see
   `ARCHITECTURE.md` §4.1).
4. Serialize through `api/serializers.py` only.
