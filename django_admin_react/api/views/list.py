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
from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import model_permissions
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.serializers import label_for
from django_admin_react.api.serializers import safe_get_field
from django_admin_react.api.serializers import serialize_fk_value
from django_admin_react.api.serializers import serialize_value
from django_admin_react.api.views.actions import actions_payload
from django_admin_react.api.writes import not_found_response

# Query params the list view manages itself (pagination / sort / search);
# any *other* key is a list_filter or date_hierarchy lookup, i.e. the list
# is narrowed. Used to decide whether the unfiltered ``full_count`` could
# differ from ``total`` (#311) — and so whether the extra COUNT(*) is worth
# running at all. ``all`` is Django's ``ALL_VAR`` "Show all" flag, not a
# filter lookup, so it must not flip the list into the narrowed branch.
_COUNT_RESERVED_PARAMS = frozenset({"page", "page_size", "ordering", "q", "all"})

# Django's ``ALL_VAR`` — the query param its changelist uses for the
# "Show all N" link (#385). Its mere presence requests show-all; the value
# is ignored, mirroring Django.
_ALL_VAR = "all"


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

        list_display = list(model_admin.get_list_display(request))
        queryset = model_admin.get_queryset(request)
        # Apply ``list_select_related`` up front so FK columns don't issue
        # one query per row (Django changelist parity / N+1 fix).
        queryset = _apply_select_related(queryset, model_admin, list_display)
        # The admin's unfiltered base — captured before search / list_filter
        # / date narrowing — for the ``show_full_result_count`` parity below.
        base_queryset = queryset

        q = request.GET.get("q", "") or ""
        if q and model_admin.search_fields:
            queryset, may_have_duplicates = model_admin.get_search_results(request, queryset, q)
            if may_have_duplicates:
                queryset = queryset.distinct()

        queryset = _apply_list_filters(queryset, model_admin, request)

        queryset_before_date_filter = queryset
        date_field = getattr(model_admin, "date_hierarchy", None)
        if date_field:
            queryset = _apply_date_filter(queryset, date_field, _parse_date_active(request))

        queryset = _apply_ordering(queryset, model_admin, request)

        total = queryset.count()

        # ``show_full_result_count`` parity (#311): when the list is
        # narrowed (search / list_filter / date_hierarchy), surface the
        # unfiltered base count so the SPA can show "X of Y". Honour
        # ``ModelAdmin.show_full_result_count`` (default True) — Django's
        # opt-out for tables where the extra COUNT(*) is too expensive,
        # in which case we send ``null``. When the view isn't narrowed the
        # full count equals ``total``, so skip the redundant query.
        show_full = getattr(model_admin, "show_full_result_count", True)
        narrowed = bool(q) or any(k not in _COUNT_RESERVED_PARAMS for k in request.GET)
        if not show_full:
            full_count: int | None = None
        elif narrowed:
            full_count = base_queryset.count()
        else:
            full_count = total

        # "Show all N" parity (#385): Django's changelist drops pagination
        # when the ``all`` param (its ``ALL_VAR``) is present AND the result
        # count is at/below ``list_max_show_all`` (default 200). Above that
        # cap the flag is ignored and the list paginates normally — the
        # guard that stops a crawler forcing a huge unbounded materialise.
        list_max_show_all = int(getattr(model_admin, "list_max_show_all", 200))
        show_all = _ALL_VAR in request.GET and total <= list_max_show_all

        if show_all:
            # One page holding every row: page 1, page_size = total. The
            # ``max(total, 1)`` keeps page_size positive for an empty list
            # (a 0-size page would slice to nothing, but there's nothing to
            # show anyway).
            page = 1
            page_size = max(total, 1)
        else:
            page_size = _clamp_page_size(request.GET.get("page_size"))
            page = _clamp_page(request.GET.get("page"))
        start = (page - 1) * page_size
        end = start + page_size

        columns = _columns_payload(model_admin, list_display, request)

        results = [
            _row_for(obj, model_admin, list_display, request, admin_site)
            for obj in queryset[start:end]
        ]

        body: dict[str, Any] = {
            "app_label": model._meta.app_label,
            # ``model_name`` stays lowercase (Django convention; used in URLs).
            # The SPA should render ``verbose_name_plural`` for list view
            # titles, falling back to ``object_name`` when the consumer
            # has not customised ``Meta.verbose_name``. Lowercased
            # ``model_name`` was previously the only signal, which is
            # why list views displayed names like
            # ``Packagemodeldisclaimerdisplayed`` instead of the
            # original ``PackageModelDisclaimerDisplayed``.
            "model_name": model._meta.model_name,
            "object_name": model._meta.object_name,
            "verbose_name": str(model._meta.verbose_name),
            "verbose_name_plural": str(model._meta.verbose_name_plural),
            # Name of the primary-key field (usually ``id``). The SPA uses
            # it to identify the pk column among ``columns`` so it can pin
            # it first, never truncate it, and keep it from being hidden —
            # the pk is the row's identity and must always be readable in
            # full. May or may not appear in ``list_display``; when it
            # doesn't, the SPA simply has nothing to pin.
            "pk_field": model._meta.pk.name,
            "permissions": model_permissions(model_admin, request),
            "columns": columns,
            # list_display_links (#251): the column name(s) that link to the
            # detail page — ``ModelAdmin.get_list_display_links`` (defaults to
            # the first column; ``[]`` when the admin set
            # ``list_display_links = None`` to disable linking). The SPA links
            # exactly these columns. Callable list_display entries are dropped
            # (only string column names round-trip).
            "list_display_links": [
                name
                for name in (model_admin.get_list_display_links(request, list_display) or ())
                if isinstance(name, str)
            ],
            "search_fields": list(model_admin.search_fields or ()),
            # ModelAdmin.search_help_text (#445): shown under the search box,
            # matching Django's changelist. Empty string when unset.
            "search_help_text": str(getattr(model_admin, "search_help_text", "") or ""),
            "filters": filters_payload(model_admin, request, admin_site=admin_site),
            "actions": actions_payload(model_admin, request),
            "page": page,
            "page_size": page_size,
            "total": total,
            # Unfiltered base count when the list is narrowed (else == total);
            # ``null`` when ``show_full_result_count`` is False. The SPA shows
            # "<total> of <full_count>" when they differ (#311).
            "full_count": full_count,
            # ``ModelAdmin.list_max_show_all`` (default 200): the SPA offers a
            # "Show all N" control only when ``total`` is at/below this cap,
            # matching Django's changelist (#385).
            "list_max_show_all": list_max_show_all,
            # empty_value_display (#251): the admin's placeholder for empty
            # cells (ModelAdmin override → AdminSite default "-"), so the SPA
            # renders it instead of a hardcoded em-dash.
            "empty_value_display": str(model_admin.get_empty_value_display()),
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
    # ``list_display`` may include callables (display methods); only the
    # plain field-name strings are valid ordering tokens.
    return {name for name in model_admin.get_list_display(request) or () if isinstance(name, str)}


def _columns_payload(
    model_admin: ModelAdmin,
    list_display: list[Any],
    request: HttpRequest,
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

    ``request`` is threaded through so ``get_sortable_by`` (and its
    fallback to ``get_list_display``) can honour third-party admin
    wrappers — e.g. ``django-admin-flexlist`` — that read
    ``request.user`` inside their ``get_list_display`` overrides.
    Calling them with ``None`` would crash the endpoint.
    """
    sortable = set(getattr(model_admin, "get_sortable_by", lambda r: ())(request) or ())
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
    list_display: list[Any],
    request: HttpRequest,
    admin_site: Any = None,
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
        fields[name] = _serialize_list_value(obj, name, value, admin_site, request)
    return {"pk": obj.pk, "label": label_for(obj), "fields": fields}


def _apply_select_related(queryset: Any, model_admin: ModelAdmin, list_display: list[Any]) -> Any:
    """Apply ``ModelAdmin.list_select_related``, mirroring Django's changelist.

    - ``True``           → ``select_related()`` (follow every FK).
    - a list / tuple     → ``select_related(*list_select_related)``.
    - ``False`` (default)→ ``select_related()`` only when ``list_display``
      includes a forward FK / one-to-one field — Django's automatic
      behavior that avoids an N+1 on FK columns.

    Never overrides a ``select_related`` the admin's ``get_queryset``
    already configured.
    """
    if getattr(queryset.query, "select_related", False):
        return queryset
    lsr = getattr(model_admin, "list_select_related", False)
    if lsr is True:
        return queryset.select_related()
    if lsr:
        return queryset.select_related(*lsr)
    if _has_related_field_in_list_display(model_admin, list_display):
        return queryset.select_related()
    return queryset


def _has_related_field_in_list_display(model_admin: ModelAdmin, list_display: list[Any]) -> bool:
    """True if any ``list_display`` entry is a forward FK / one-to-one field.

    Only forward single-valued relations benefit from ``select_related``;
    many-to-many (needs ``prefetch_related``) and method/callable columns
    are skipped.
    """
    from django.core.exceptions import FieldDoesNotExist

    meta = model_admin.model._meta
    for name in list_display:
        try:
            field = meta.get_field(name)
        except FieldDoesNotExist:
            continue
        if getattr(field, "many_to_one", False) or getattr(field, "one_to_one", False):
            return True
    return False


def _serialize_list_value(
    obj: Model,
    name: str,
    value: Any,
    admin_site: Any = None,
    request: HttpRequest | None = None,
) -> Any:
    """Serialize a single ``list_display`` cell.

    FK fields go through the FK envelope (``{"id", "label"}``);
    everything else goes through the conservative serializer with
    ``str()`` fallback. Callable list_display entries (e.g.
    ``@admin.display``) have already been resolved to a plain value
    by ``lookup_field``. The model_field reference is forwarded so
    consumer-registered custom serializers (see #60 /
    ``register_field_type``) take precedence over the default dispatch.
    ``request`` is forwarded so the FK ``to`` link is gated on the
    target's per-user view permission (#301).
    """
    model_field = safe_get_field(obj, name)
    if isinstance(model_field, ForeignKey):
        return serialize_fk_value(value, admin_site=admin_site, request=request)
    # A field with ``choices`` displays its human label, not the stored
    # value (Django's ``display_for_field`` parity — e.g. ``1`` → "High").
    # The changelist is a read-only display surface; ``list_editable``
    # carries the raw value through its own path, so mapping here is safe.
    if model_field is not None:
        flatchoices = getattr(model_field, "flatchoices", None)
        if flatchoices:
            label = dict(flatchoices).get(value)
            if label is not None:
                return str(label)
    return serialize_value(value, field=model_field)
