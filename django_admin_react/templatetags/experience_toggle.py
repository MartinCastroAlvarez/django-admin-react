"""Template tag for the reverse escape-hatch strip (#584).

Used by the package's override of ``admin/base_site.html`` to render a
thin, persistent, non-dismissable strip at the top of every Django
admin page linking the same path under the React admin's mount.

The tag is a no-op (renders nothing) unless **both** prefixes are
configured: ``DJANGO_ADMIN_REACT["LEGACY_ADMIN_URL_PREFIX"]`` and
``DJANGO_ADMIN_REACT["REACT_ADMIN_URL_PREFIX"]``. Reverse direction
stays off when only the SPA-side prefix is known — we never guess
the consumer's chosen SPA mount.

URL construction mirrors the SPA-side ``legacyUrlFor`` (#582):
preserves ``request.GET`` (query string) and lets the SPA's route
decide its own trailing-slash semantics (React Router accepts both
shapes; no enforced trailing slash on the React side, where the
legacy side required one because of ``catch_all_view``).
"""

from __future__ import annotations

from typing import Any

from django import template
from django.http import HttpRequest

# `conf` is itself the settings module — it exposes resolved values
# via PEP-562 `__getattr__`. Importing the module + reading attributes
# off it matches the pattern in `views.py` (`from .. import conf as
# dar_conf`).
from django_admin_react import conf as dar_conf

register = template.Library()


def _normalise_prefix(value: str | None) -> str | None:
    """Strip leading/trailing slashes and require a non-empty result.

    Matches the SPA-side normalisation in
    ``views._resolve_legacy_admin_prefix`` — both call sites must
    agree, otherwise the strips on either side compute different URLs.
    """
    if not isinstance(value, str):
        return None
    trimmed = value.strip().strip("/")
    return trimmed or None


@register.inclusion_tag(
    "django_admin_react/_experience_toggle_strip.html",
    takes_context=True,
)
def experience_toggle_strip(context: dict[str, Any]) -> dict[str, Any]:
    """Render the reverse strip on the legacy admin's pages (#584).

    Renders nothing when:

    - Either prefix is unset.
    - ``request`` is not in the context (a render driven by a
      management command, an exception page that omits the request).
    - The current request path does not start with the legacy
      prefix (defensive — the strip should only appear under the
      legacy admin's URL space, never under an unrelated app that
      happens to share the package's ``admin/base_site.html``
      template via a misconfiguration).
    """
    legacy = _normalise_prefix(dar_conf.LEGACY_ADMIN_URL_PREFIX)
    react = _normalise_prefix(dar_conf.REACT_ADMIN_URL_PREFIX)
    request: HttpRequest | None = context.get("request")
    if not (legacy and react and request is not None):
        return {"visible": False}

    legacy_root = "/" + legacy + "/"
    react_root = "/" + react + "/"
    path: str = request.path
    if not path.startswith(legacy_root):
        return {"visible": False}

    tail = path[len(legacy_root):]
    query = request.META.get("QUERY_STRING", "") if hasattr(request, "META") else ""
    target = react_root + tail + (("?" + query) if query else "")
    return {"visible": True, "target": target, "react_root": react_root}
