"""django-admin-react — the React SPA super-layer for the Django admin.

A drop-in single-page admin: same `pip install`, same `INSTALLED_APPS`,
same `urls.py include()` — and your `ModelAdmin` classes drive everything.
The JSON wire surface lives in the sibling
[`django-admin-rest-api`](https://pypi.org/project/django-admin-rest-api/)
package (pulled in as a dependency); the MCP exposure of the same surface
lives in
[`django-admin-mcp-api`](https://pypi.org/project/django-admin-mcp-api/).

See `README.md` for install + the consumer wiring, and `ARCHITECTURE.md`
for what lives in this repo vs. the API / MCP siblings.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    # Read the version directly from the installed distribution metadata
    # so this constant never drifts from `pyproject.toml` after a release.
    __version__ = _pkg_version("django-admin-react")
except PackageNotFoundError:  # pragma: no cover — editable / source install
    __version__ = "0.0.0"

default_app_config = "django_admin_react.apps.DjangoAdminReactConfig"
