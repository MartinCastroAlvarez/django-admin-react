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
from django.db.models import Model
from django.db.models import QuerySet
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react import conf
from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import model_permissions
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.serializers import serialize_fk_value
from django_admin_react.api.serializers import serialize_value


_NOT_FOUND_BODY: dict[str, dict[str, str]] = {
    "error": {"code": "not_found", "message": "Not found."}
}


def _not_found_response() -> HttpResponse:
    response = JsonResponse(_NOT_FOUND_BODY, status=404)
    response["Cache-Control"] = "no-store"
    return response


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
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response()

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return _not_found_response()
        model, model_admin = resolved

        queryset = model_admin.get_queryset(request)

        q = request.GET.get("q", "") or ""
        if q and model_admin.search_fields:
            queryset, may_have_duplicates = model_admin.get_search_results(
                request, queryset, q
            )
            if may_have_duplicates:
                queryset = queryset.distinct()

        queryset = _apply_ordering(queryset, model_admin, request)

        total = queryset.count()

        page_size = _clamp_page_size(request.GET.get("page_size"))
        page = _clamp_page(request.GET.get("page"))
        start = (page - 1) * page_size
        end = start + page_size

        list_display = list(model_admin.get_list_display(request))
        columns = _columns_payload(model_admin, list_display)

        results = [
            _row_for(obj, model_admin, list_display, request)
            for obj in queryset[start:end]
        ]

        body: dict[str, Any] = {
            "app_label": model._meta.app_label,
            "model_name": model._meta.model_name,
            "permissions": model_permissions(model_admin, request),
            "columns": columns,
            "search_fields": list(model_admin.search_fields or ()),
            "page": page,
            "page_size": page_size,
            "total": total,
            "results": results,
        }
        return JsonResponse(body, status=200)


def _clamp_page(raw: str | None) -> int:
    try:
        n = int(raw) if raw is not None else 1
    except (TypeError, ValueError):
        return 1
    return max(1, n)


def _clamp_page_size(raw: str | None) -> int:
    settings = conf.load()
    default = settings.DEFAULT_PAGE_SIZE
    maximum = settings.MAX_PAGE_SIZE
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
    sortable = set(
        getattr(model_admin, "get_sortable_by", lambda r: ())(None) or ()
    )
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
            }
        )
    return payload


def _row_for(
    obj: Model,
    model_admin: ModelAdmin,
    list_display: list[str],
    request: HttpRequest,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for name in list_display:
        try:
            _f, _attr, value = lookup_field(name, obj, model_admin)
        except Exception:  # pragma: no cover — defensive
            value = ""
        fields[name] = _serialize_list_value(obj, name, value)
    label = _label_for_obj(obj)
    return {"pk": obj.pk, "label": label, "fields": fields}


def _serialize_list_value(obj: Model, name: str, value: Any) -> Any:
    """Serialize a single list_display cell.

    FK fields go through the FK envelope; everything else goes through
    the conservative serializer with ``str()`` fallback. Callable
    list_display values (e.g., ``@admin.display``) are already resolved
    by ``lookup_field`` into a plain value.
    """
    # If the attribute is a real model FK, prefer the {id, label} shape.
    try:
        descriptor = type(obj).__dict__.get(name)
    except Exception:  # pragma: no cover — defensive
        descriptor = None
    if descriptor is not None:
        # Resolve "X_id" implicit FK references too.
        field = getattr(obj._meta.get_field(name) if _has_model_field(obj, name) else None, "field", None)  # type: ignore[arg-type]
        if _has_model_field(obj, name):
            model_field = obj._meta.get_field(name)
            from django.db.models import ForeignKey

            if isinstance(model_field, ForeignKey):
                return serialize_fk_value(value)
    return serialize_value(value)


def _has_model_field(obj: Model, name: str) -> bool:
    try:
        obj._meta.get_field(name)
    except Exception:
        return False
    return True


def _label_for_obj(obj: Model) -> str:
    try:
        return str(obj)
    except Exception:  # pragma: no cover — defensive
        return f"<{obj.__class__.__name__}: {obj.pk}>"
