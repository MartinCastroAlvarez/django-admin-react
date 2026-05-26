"""``GET /api/v1/<app>/<model>/autocomplete/`` — autocomplete endpoint.

Wire contract: ``docs/api-contract.md`` §3.2.

Powers ``autocomplete_fields`` and ``raw_id_fields`` (#59) — a
high-cardinality FK picker needs server-side search rather than
materialising every related row into a ``<select>``.

The endpoint is gated by the **target** model's
``ModelAdmin.has_view_permission`` — i.e. a user can autocomplete
into ``auth.User`` only if their admin permission to *view* users
allows it. The endpoint mirrors Django's stock ``AdminSite.autocomplete_view``
gate:

1. ``is_admin_user`` — 403 (or ``session_expired``) if not staff.
2. ``resolve_model`` — 404 if the target isn't in the admin registry
   or the user can't view it.
3. ``ModelAdmin.search_fields`` — 400 if the target admin doesn't
   declare any (autocomplete requires search). The admin's own UI
   raises ``ImproperlyConfigured`` in the same case; the API
   surfaces it as a 400 so the SPA can show "this FK isn't
   autocompletable" inline.
4. ``ModelAdmin.get_search_results(request, qs, q)`` — the actual
   search; the package never re-implements search semantics.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_view_permission`` controls visibility.
- Rule 10: Queryset starts at ``ModelAdmin.get_queryset(request)`` —
           never ``Model.objects.all()`` (B-2).
- Rule 12: Sensitive-field denylist still applies to the label fallback
           if the target's ``__str__`` ever leaks a sensitive value
           (defense-in-depth).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react import conf
from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.serializers import label_for
from django_admin_react.api.writes import bad_request
from django_admin_react.api.writes import not_found_response

# Autocomplete results live or die on response latency. A page cap
# keeps a hostile ``?page_size=10000`` from materialising the full
# table on a typeahead keystroke. Hard upper bound: 50.
_AUTOCOMPLETE_MAX_PAGE_SIZE = 50
_AUTOCOMPLETE_DEFAULT_PAGE_SIZE = 20


class AutocompleteView(View):
    """``GET /api/v1/<app_label>/<model_name>/autocomplete/?q=<term>``."""

    http_method_names = ["get"]

    def get(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Return a typeahead-friendly slice of the target queryset.

        Gates run in the same order as every other read endpoint
        (auth → resolve → permission); the additional gate here is
        the target admin's ``search_fields`` being non-empty, since
        autocomplete without search is not a meaningful operation.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        _model, model_admin = resolved

        if not model_admin.search_fields:
            return bad_request(
                "The target admin does not declare search_fields; " "autocomplete is not available."
            )

        q = (request.GET.get("q") or "").strip()
        page = _clamp_page(request.GET.get("page"))
        page_size = _clamp_page_size(request.GET.get("page_size"))

        queryset = model_admin.get_queryset(request)
        if q:
            queryset, may_have_duplicates = model_admin.get_search_results(request, queryset, q)
            if may_have_duplicates:
                queryset = queryset.distinct()

        queryset = queryset.order_by("pk")
        start = (page - 1) * page_size
        # Fetch one extra so we can answer ``has_more`` without a
        # ``COUNT(*)`` — that's a meaningful win on a typeahead.
        rows = list(queryset[start : start + page_size + 1])
        has_more = len(rows) > page_size
        rows = rows[:page_size]

        body = {
            "results": [{"id": obj.pk, "label": label_for(obj)} for obj in rows],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "has_more": has_more,
            },
        }
        response = JsonResponse(body, status=200)
        # Per-user, permission-gated, search-term-specific payload —
        # never let a proxy / browser cache it across users.
        response["Cache-Control"] = "no-store"
        return response


def _clamp_page(raw: str | None) -> int:
    """Parse ``?page=`` to a positive int, defaulting to 1.

    Garbage input falls back to 1 — typeahead must never 500 on a
    crawler hitting ``?page=abc`` mid-typing.
    """
    try:
        n = int(raw) if raw is not None else 1
    except (TypeError, ValueError):
        return 1
    return max(1, n)


def _clamp_page_size(raw: str | None) -> int:
    """Parse ``?page_size=`` and clamp to ``[1, _AUTOCOMPLETE_MAX_PAGE_SIZE]``.

    The package-wide ``MAX_PAGE_SIZE`` (200 by default) is too high
    for a typeahead: every keystroke would scan and materialise 200
    rows, defeating the point. The autocomplete-specific cap is 50.
    A hostile ``?page_size=10000`` is silently clamped to the
    autocomplete max.
    """
    default = _AUTOCOMPLETE_DEFAULT_PAGE_SIZE
    maximum = _AUTOCOMPLETE_MAX_PAGE_SIZE
    # Respect the consumer's MAX_PAGE_SIZE if they set it lower than
    # our autocomplete max — that's a explicit tighter cap.
    maximum = min(maximum, int(conf.MAX_PAGE_SIZE))
    try:
        n = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        n = default
    if n < 1:
        return default
    return min(n, maximum)
