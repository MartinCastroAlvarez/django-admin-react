"""GET /api/v1/<app>/<model>/ — list view.

Wire contract: ``docs/api-contract.md`` §3.

Hard rules followed (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_view_permission`` controls visibility.
- Rule 10: Queryset starts at ``ModelAdmin.get_queryset(request)`` —
           never ``Model.objects.all()`` (B-2).
- Search:  ``ModelAdmin.get_search_results(request, qs, q)``.
- Columns: ``ModelAdmin.get_list_display(request)``.
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.utils import label_for_field
from django.contrib.admin.utils import lookup_field
from django.db.models import ForeignKey
from django.db.models import Model
from django.db.models import QuerySet
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react import conf
from django_admin_react.api.dates import apply_filter as _apply_date_filter
from django_admin_react.api.dates import date_hierarchy_payload
from django_admin_react.api.dates import parse_active as _parse_date_active
from django_admin_react.api.filters import apply_filters as _apply_list_filters
from django_admin_react.api.filters import filters_payload
from django_admin_react.api.views.actions import actions_payload
from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import model_permissions
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.serializers import label_for
from django_admin_react.api.serializers import safe_get_field
from django_admin_react.api.serializers import serialize_fk_value
from django_admin_react.api.serializers import serialize_value
from django_admin_react.api.writes import not_found_response


class ListView(View):
    """``GET /api/v1/<app_label>/<model_name>/`` — paginated list."""

    http_method_names = ["get"]

    def get(  # noqa: D401
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Return a paginated list of rows for one model (contract §3).

        Gates, in order:

        1. ``is_admin_user`` — 403 if not authenticated active staff.
        2. ``resolve_model`` — 404 if the model isn't registered with
           the admin site or the user can't view it. Returning 404
           (not 403) is deliberate so the endpoint never reveals
           "this model exists but you can't see it" (rule 12 /
           ACCEPTANCE §4.3 S-11).
        3. ``ModelAdmin.get_queryset(request)`` provides the starting
           queryset — never ``Model.objects.all()`` (rule 10 / B-2).

        Then applies search, ordering, page-size clamp, and serializes
        each row through the conservative serializer.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        model, model_admin = resolved

        queryset = model_admin.get_queryset(request)

        q = request.GET.get("q", "") or ""
        if q and model_admin.search_fields:
            queryset, may_have_duplicates = model_admin.get_search_results(request, queryset, q)
            if may_have_duplicates:
                queryset = queryset.distinct()

        queryset = _apply_list_filters(queryset, model_admin, request)

        queryset_before_date_filter = queryset
        date_field = getattr(model_admin, "date_hierarchy", None)
        if date_field:
            queryset = _apply_date_filter(
                queryset, date_field, _parse_date_active(request)
            )

        queryset = _apply_ordering(queryset, model_admin, request)

        total = queryset.count()

        page_size = _clamp_page_size(request.GET.get("page_size"))
        page = _clamp_page(request.GET.get("page"))
        start = (page - 1) * page_size
        end = start + page_size

        list_display = list(model_admin.get_list_display(request))
        columns = _columns_payload(model_admin, list_display)

        results = [_row_for(obj, model_admin, list_display, request) for obj in queryset[start:end]]

        body: dict[str, Any] = {
            "app_label": model._meta.app_label,
            "model_name": model._meta.model_name,
            "permissions": model_permissions(model_admin, request),
            "columns": columns,
            "search_fields": list(model_admin.search_fields or ()),
            "filters": filters_payload(model_admin, request),
            "actions": actions_payload(model_admin, request),
            "page": page,
            "page_size": page_size,
            "total": total,
            "results": results,
        }
        date_hierarchy = date_hierarchy_payload(
            model_admin, queryset_before_date_filter, queryset, request
        )
        if date_hierarchy is not None:
            body["date_hierarchy"] = date_hierarchy
        response = JsonResponse(body, status=200)
        # No-store: per-user, permission-gated payload must never be
        # cached by intermediate proxies or the browser. Extends
        # ACCEPTANCE.md §4.6 S-30 (defined for 4xx) to 200 responses.
        response["Cache-Control"] = "no-store"
        return response


def _clamp_page(raw: str | None) -> int:
    """Parse ``?page=`` into a positive integer, defaulting to 1.

    Garbage input (non-integer, negative, missing) returns 1. The
    endpoint never raises on a bad query string — that would let a
    crawler send "?page=abc" to trigger a 500.
    """
    try:
        n = int(raw) if raw is not None else 1
    except (TypeError, ValueError):
        return 1
    return max(1, n)


def _clamp_page_size(raw: str | None) -> int:
    """Parse ``?page_size=`` and clamp to ``[1, conf.MAX_PAGE_SIZE]``.

    The clamp is a denial-of-service guard: without an upper bound a
    client could pass ``?page_size=10_000_000`` and force the
    database to materialise ten million rows.
    """
    default = int(conf.DEFAULT_PAGE_SIZE)
    maximum = int(conf.MAX_PAGE_SIZE)
    try:
        n = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        n = default
    if n < 1:
        return default
    return min(n, maximum)


def _apply_ordering(
    queryset: QuerySet,
    model_admin: ModelAdmin,
    request: HttpRequest,
) -> QuerySet:
    """Apply ``?ordering=`` if every token is in the admin's allowed set.

    Unknown tokens are silently dropped (per contract §7 and §3.4 C-5).
    """
    raw = request.GET.get("ordering", "")
    if not raw:
        return queryset
    allowed = _allowed_ordering(model_admin, request)
    tokens = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        bare = token.lstrip("-")
        if bare in allowed:
            tokens.append(token)
    if not tokens:
        return queryset
    return queryset.order_by(*tokens)


def _allowed_ordering(model_admin: ModelAdmin, request: HttpRequest) -> set[str]:
    """Return the field-name set the admin allows for ordering.

    ``ModelAdmin.get_sortable_by(request)`` (Django ≥ 2.1) is the
    canonical source; falls back to ``list_display`` if not overridden.
    """
    get_sortable_by = getattr(model_admin, "get_sortable_by", None)
    if callable(get_sortable_by):
        return set(get_sortable_by(request) or ())
    return set(model_admin.get_list_display(request) or ())


def _columns_payload(
    model_admin: ModelAdmin,
    list_display: list[str],
) -> list[dict[str, Any]]:
    """Build the ``columns[]`` payload for the list response.

    Each entry has ``{name, label, sortable, editable}``. Labels
    resolve through Django's ``label_for_field`` so admin-customised
    labels (verbose name, ``short_description``, etc.) are honored.
    ``editable`` is derived from ``ModelAdmin.list_editable`` — the
    SPA renders the cell as an in-place editor when ``True`` and
    submits changes via the bulk PATCH endpoint (Issue #61). The
    ``except`` fallback to the bare name is defensive — corrupt
    admin registrations should never 500 the endpoint.
    """
    sortable = set(getattr(model_admin, "get_sortable_by", lambda r: ())(None) or ())
    editable = set(getattr(model_admin, "list_editable", ()) or ())
    payload = []
    for name in list_display:
        try:
            label = label_for_field(name, model_admin.model, model_admin)
        except Exception:  # pragma: no cover — defensive
            label = name
        payload.append(
            {
                "name": name,
                "label": str(label),
                "sortable": name in sortable,
                "editable": name in editable,
            }
        )
    return payload


def _row_for(
    obj: Model,
    model_admin: ModelAdmin,
    list_display: list[str],
    request: HttpRequest,
) -> dict[str, Any]:
    """Build one ``results[]`` entry for the list response.

    Each row is ``{pk, label, fields: {name: serialized_value}}``.
    Cell values go through ``lookup_field`` (so admin
    ``@admin.display`` callables resolve correctly), then through
    the conservative serializer with ``str()`` fallback. The except
    branch is intentional — a misbehaving ``list_display`` callable
    must not break the whole list response (graceful degrade).
    """
    fields: dict[str, Any] = {}
    for name in list_display:
        try:
            _f, _attr, value = lookup_field(name, obj, model_admin)
        except Exception:  # pragma: no cover — defensive
            value = ""
        fields[name] = _serialize_list_value(obj, name, value)
    return {"pk": obj.pk, "label": label_for(obj), "fields": fields}


def _serialize_list_value(obj: Model, name: str, value: Any) -> Any:
    """Serialize a single ``list_display`` cell.

    FK fields go through the FK envelope (``{"id", "label"}``);
    everything else goes through the conservative serializer with
    ``str()`` fallback. Callable list_display entries (e.g.
    ``@admin.display``) have already been resolved to a plain value
    by ``lookup_field``. The model_field reference is forwarded so
    consumer-registered custom serializers (see #60 /
    ``register_field_type``) take precedence over the default dispatch.
    """
    model_field = safe_get_field(obj, name)
    if isinstance(model_field, ForeignKey):
        return serialize_fk_value(value)
    return serialize_value(value, field=model_field)
