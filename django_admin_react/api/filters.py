"""``list_filter`` taxonomy + application for the list endpoint.

Wire contract: ``docs/api-contract.md`` §11 (added in this PR — see
`feat/list-filter-architect`).

Surfaces the five-type closed filter vocabulary in the list response
and applies the request's filter selections to the queryset through
Django's own ``ChangeList`` machinery.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  ``ModelAdmin.get_list_filter(request)`` is the only source
           of truth for which filters exist. Never declare filters
           outside the admin (B-7).
- Rule 10: Filter application starts from the queryset *already*
           produced by ``ModelAdmin.get_queryset(request)`` — we
           narrow it further, never broaden.
- Rule 12: Unknown filter keys are silently ignored, never 400. A
           hostile ``?bogus=42`` must not produce an error oracle.

Why ``ChangeList``: ``SimpleListFilter`` subclasses have custom
``queryset(request, qs)`` methods. Iterating ``list_filter`` ourselves
and trying to AND ``Q`` objects bypasses those methods and silently
breaks every custom filter a consumer has ever written. Only
``ChangeList.get_filters`` instantiates each filter spec correctly.

URL grammar is admin-parity (see ``docs/api-contract.md`` §11):
``?<field>__exact=…``, ``?<field>__id__exact=…``, ``?<field>__year=…``,
``?<parameter_name>=…`` for ``SimpleListFilter``. A URL copied from
the legacy admin lands on the same row set in the SPA.
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.filters import FieldListFilter
from django.contrib.admin.filters import RelatedFieldListFilter
from django.contrib.admin.filters import SimpleListFilter
from django.contrib.admin.options import ModelAdmin
from django.db.models import BooleanField
from django.db.models import DateField
from django.db.models import ForeignKey
from django.db.models import QuerySet
from django.http import HttpRequest


def filters_payload(
    model_admin: ModelAdmin,
    request: HttpRequest,
) -> list[dict[str, Any]]:
    """Build the ``filters[]`` descriptor list for the list response.

    Each entry is one of the five closed types:

    - ``boolean`` for ``BooleanField`` filters.
    - ``choices`` for ``CharField`` / ``IntegerField`` with ``choices``.
    - ``foreignkey`` for FK / OneToOne filters.
    - ``date_range`` for ``DateField`` / ``DateTimeField`` filters.
    - ``custom`` for ``SimpleListFilter`` subclasses.

    Filter entries whose Django spec class falls outside this
    vocabulary are silently dropped — the SPA only ever learns five
    layouts (closed vocabulary, see contract §11).
    """
    specs = _filter_specs(model_admin, request)
    out: list[dict[str, Any]] = []
    for spec in specs:
        descriptor = _classify(spec, request, model_admin)
        if descriptor is not None:
            out.append(descriptor)
    return out


def apply_filters(
    queryset: QuerySet,
    model_admin: ModelAdmin,
    request: HttpRequest,
) -> QuerySet:
    """Narrow ``queryset`` by the active ``?filter=…`` query params.

    Iterates the same filter specs ``ChangeList`` would build for this
    request and calls each ``spec.queryset(request, qs)``. A spec that
    returns ``None`` (meaning "no active selection on me") leaves the
    queryset untouched; an active spec narrows.

    Unknown URL parameters never reach a spec — Django's filter
    machinery only consults the params each spec declares in
    ``expected_parameters()``. So ``?bogus=42`` is a no-op, not a
    400 (contract §11.3).
    """
    specs = _filter_specs(model_admin, request)
    for spec in specs:
        narrowed = spec.queryset(request, queryset)
        if narrowed is not None:
            queryset = narrowed
    return queryset


# --------------------------------------------------------------------------- #
# Internals                                                                   #
# --------------------------------------------------------------------------- #
def _filter_specs(
    model_admin: ModelAdmin,
    request: HttpRequest,
) -> list[FieldListFilter | SimpleListFilter]:
    """Return the list of filter-spec instances for this request.

    Construction matches what ``ChangeList.get_filters`` does
    internally: each entry in ``list_filter`` is either a
    ``SimpleListFilter`` subclass (callable) or a field name (with an
    optional explicit filter class). Each is instantiated with the
    request's ``GET`` so the spec can read its own params and decide
    whether to narrow the queryset.

    A construction failure on any one filter is swallowed (returns
    an empty list rather than 500-ing the whole list endpoint) —
    consistent with the rest of the package's "garbage input never
    raises" posture (rule 12).
    """
    list_filter = list(model_admin.get_list_filter(request) or ())
    if not list_filter:
        return []
    model = model_admin.model
    # Multi-valued params — Django's ``FieldListFilter`` family expects
    # ``{key: [value, ...]}`` (mirrors ``ChangeList.params``). Passing a
    # single string would break ``__in`` lookups and per-spec
    # ``params.pop()`` semantics.
    lookup_params = {key: request.GET.getlist(key) for key in request.GET}
    specs: list[FieldListFilter | SimpleListFilter] = []
    for entry in list_filter:
        spec = _instantiate_spec(entry, request, lookup_params, model, model_admin)
        if spec is not None:
            specs.append(spec)
    return specs


def _instantiate_spec(
    entry: Any,
    request: HttpRequest,
    lookup_params: dict[str, list[str]],
    model: Any,
    model_admin: ModelAdmin,
) -> FieldListFilter | SimpleListFilter | None:
    """Instantiate one filter spec, swallowing any construction error.

    Mirrors the construction branches in
    ``django.contrib.admin.views.main.ChangeList.get_filters``:

    - Callable and a subclass of ``SimpleListFilter`` → instantiate
      with ``(request, params, model, model_admin)``.
    - Tuple ``(field_name, filter_class)`` → field-path resolution.
    - Bare field name → resolve the model field and pick its default
      filter class via ``FieldListFilter.create``.
    """
    try:
        if callable(entry) and isinstance(entry, type) and issubclass(entry, SimpleListFilter):
            return entry(request, lookup_params, model, model_admin)
        if isinstance(entry, list | tuple):
            field_name, filter_class = entry
        else:
            field_name, filter_class = entry, None
        field = model._meta.get_field(field_name)
        if filter_class is None:
            return FieldListFilter.create(
                field, request, lookup_params, model, model_admin, field_name
            )
        return filter_class(field, request, lookup_params, model, model_admin, field_name)
    except Exception:
        return None


def _classify(
    spec: FieldListFilter | SimpleListFilter,
    request: HttpRequest,
    model_admin: ModelAdmin,
) -> dict[str, Any] | None:
    """Convert one filter spec to its closed-vocabulary descriptor.

    Returns ``None`` for any spec that does not map to one of the
    five v1 types — keeping the contract honest (the SPA only ever
    learns five layouts). ``request`` and ``model_admin`` are
    threaded through for ``SimpleListFilter.lookups(request,
    model_admin)`` — Django's ``ListFilter`` does not store them on
    ``self``.
    """
    if isinstance(spec, SimpleListFilter):
        return _custom_descriptor(spec, request, model_admin)

    field = getattr(spec, "field", None)
    if field is None:
        return None

    name = field.name
    label = str(getattr(spec, "title", "") or name)

    if isinstance(field, BooleanField):
        return {"type": "boolean", "name": name, "label": label}

    if isinstance(field, ForeignKey) or isinstance(spec, RelatedFieldListFilter):
        related = field.related_model
        descriptor: dict[str, Any] = {"type": "foreignkey", "name": name, "label": label}
        if related is not None:
            meta = related._meta
            descriptor["to"] = {"app_label": meta.app_label, "model_name": meta.model_name}
        return descriptor

    if isinstance(field, DateField):
        return {"type": "date_range", "name": name, "label": label}

    if getattr(field, "choices", None):
        choices = [{"value": v, "label": str(lbl)} for v, lbl in field.choices]
        return {"type": "choices", "name": name, "label": label, "choices": choices}

    return None


def _custom_descriptor(
    spec: SimpleListFilter,
    request: HttpRequest,
    model_admin: ModelAdmin,
) -> dict[str, Any] | None:
    """Descriptor for a ``SimpleListFilter`` subclass.

    Surfaces the ``lookups()`` output as the available options.
    Returns ``None`` if the lookups call fails — a broken
    ``SimpleListFilter`` should not 500 the list endpoint.
    """
    try:
        raw_lookups = list(spec.lookups(request, model_admin) or ())
    except Exception:
        return None
    lookups = [{"value": v, "label": str(lbl)} for v, lbl in raw_lookups]
    return {
        "type": "custom",
        "name": spec.parameter_name,
        "label": str(getattr(spec, "title", "") or spec.parameter_name),
        "lookups": lookups,
    }
