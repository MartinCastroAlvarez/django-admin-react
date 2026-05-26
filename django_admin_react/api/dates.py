"""Date-hierarchy drill-down for the list endpoint.

Wire contract: ``docs/api-contract.md`` §3.1.

When a ``ModelAdmin`` declares ``date_hierarchy = "<field>"``, the list
endpoint:

1. Surfaces metadata (``field``, ``granularity_options``) in the
   response.
2. Reads ``?year=`` / ``?month=`` / ``?day=`` query params and
   narrows the queryset to that date window.
3. Returns ``buckets`` — the next-level drill-down counts the SPA
   needs to render the admin's year → month → day strip.

Hard rules (`SECURITY.md` §3):

- Rule 10: Never starts from ``Model.objects.all()`` — the queryset
  passed in is the one already produced by
  ``ModelAdmin.get_queryset(request)``.
- Rule 12: Garbage input (non-integer query params, out-of-range
  values, unknown field) is silently ignored, never raises — a
  hostile ``?year=abc`` must not produce a 500.

The helper is queryset-shape-agnostic: as long as the field is a
``DateField`` or ``DateTimeField`` on the model, the standard
``__year`` / ``__month`` / ``__day`` ORM lookups work.
"""

from __future__ import annotations

from typing import Any
from typing import Final

from django.contrib.admin.options import ModelAdmin
from django.db.models import Count
from django.db.models import QuerySet
from django.db.models.functions import Extract
from django.db.models.functions import ExtractDay
from django.db.models.functions import ExtractMonth
from django.db.models.functions import ExtractYear
from django.http import HttpRequest

GRANULARITY_OPTIONS: Final[tuple[str, ...]] = ("year", "month", "day")

# Sanity bounds for raw query-param ints. The field-level filter would
# also reject out-of-range values, but rejecting them up front avoids
# round-tripping garbage through the ORM.
_BOUNDS: Final[dict[str, tuple[int, int]]] = {
    "year": (1, 9999),
    "month": (1, 12),
    "day": (1, 31),
}


def _parse_int(raw: str | None, key: str) -> int | None:
    """Parse one query-param int, or return ``None`` if missing/garbage.

    Bounds-checks against ``_BOUNDS[key]`` so a hostile
    ``?month=99999999`` doesn't reach the ORM. Out-of-range values
    are silently dropped, matching the package's "garbage in → safe
    default" posture on query strings.
    """
    if raw is None:
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    low, high = _BOUNDS[key]
    if n < low or n > high:
        return None
    return n


def parse_active(request: HttpRequest) -> dict[str, int | None]:
    """Extract the ``{year, month, day}`` selection from the query string.

    Returns a dict with each key either an ``int`` or ``None``. The
    SPA passes the active drill-down as plain query params:
    ``?year=2025``, ``?year=2025&month=10``, etc. Children of a
    ``None`` ancestor are dropped — e.g., ``?month=10`` without a
    year is meaningless and becomes ``{year: None, month: None}``.
    """
    year = _parse_int(request.GET.get("year"), "year")
    month = _parse_int(request.GET.get("month"), "month") if year is not None else None
    day = _parse_int(request.GET.get("day"), "day") if month is not None else None
    return {"year": year, "month": month, "day": day}


def apply_filter(
    queryset: QuerySet,
    field: str,
    active: dict[str, int | None],
) -> QuerySet:
    """Narrow ``queryset`` to the active year / month / day window.

    Uses Django's ``__year`` / ``__month`` / ``__day`` lookups so the
    filter delegates to the database engine (SQLite, Postgres, MySQL
    all handle these natively). No raw SQL.
    """
    lookups: dict[str, int] = {}
    year, month, day = active.get("year"), active.get("month"), active.get("day")
    if year is not None:
        lookups[f"{field}__year"] = year
    if month is not None:
        lookups[f"{field}__month"] = month
    if day is not None:
        lookups[f"{field}__day"] = day
    if not lookups:
        return queryset
    return queryset.filter(**lookups)


def build_buckets(
    queryset: QuerySet,
    field: str,
    active: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Build the next-level drill-down counts.

    The level depends on the active selection:

    - No year → buckets are years.
    - Year, no month → buckets are months within that year.
    - Year + month, no day → buckets are days within that month.
    - Year + month + day → no further drill (returns ``[]``).

    Each bucket is ``{value: int, count: int}``. The list is sorted
    ascending by ``value``. ``NULL`` values in the date field are
    excluded (they don't appear in any bucket).
    """
    year, month, day = active.get("year"), active.get("month"), active.get("day")
    extractor: type[Extract]
    if year is None:
        extractor, _name = ExtractYear, "year"
    elif month is None:
        extractor, _name = ExtractMonth, "month"
    elif day is None:
        extractor, _name = ExtractDay, "day"
    else:
        return []

    rows = (
        queryset.annotate(_bucket=extractor(field))
        .values("_bucket")
        .annotate(_count=Count("pk"))
        .order_by("_bucket")
    )
    return [{"value": r["_bucket"], "count": r["_count"]} for r in rows if r["_bucket"] is not None]


def date_hierarchy_payload(
    model_admin: ModelAdmin,
    queryset_before_filter: QuerySet,
    queryset_after_filter: QuerySet,  # noqa: ARG001 — reserved; see body
    request: HttpRequest,
) -> dict[str, Any] | None:
    """Build the ``date_hierarchy`` block of the list response, or ``None``.

    Returns ``None`` when:

    - The admin does not declare ``date_hierarchy``, **or**
    - The named field does not exist on the model (defensive — a
      typo in the admin must not crash the list endpoint), **or**
    - The named field is not a ``DateField`` / ``DateTimeField``.

    Otherwise the payload is::

        {
          "field": "created_at",
          "granularity_options": ["year", "month", "day"],
          "active": {"year": 2025, "month": 10, "day": null},
          "buckets": [
            {"value": 1,  "count": 12},
            {"value": 2,  "count":  4},
            ...
          ]
        }

    Buckets are computed from ``queryset_before_filter`` narrowed by
    the *parent* levels of the active selection (not the current
    level), so drilling from year 2025 still shows month buckets
    *within 2025*.
    """
    field_name = getattr(model_admin, "date_hierarchy", None)
    if not field_name:
        return None

    model = model_admin.model
    try:
        field = model._meta.get_field(field_name)
    except Exception:  # pragma: no cover — typo'd date_hierarchy
        return None

    internal_type = field.get_internal_type()
    if internal_type not in {"DateField", "DateTimeField"}:
        return None

    active = parse_active(request)

    bucket_qs = queryset_before_filter
    if active.get("year") is not None:
        bucket_qs = bucket_qs.filter(**{f"{field_name}__year": active["year"]})
    if active.get("month") is not None:
        bucket_qs = bucket_qs.filter(**{f"{field_name}__month": active["month"]})
    # day-level: no further buckets to compute.

    buckets = build_buckets(bucket_qs, field_name, active)

    return {
        "field": field_name,
        "granularity_options": list(GRANULARITY_OPTIONS),
        "active": active,
        "buckets": buckets,
    }
