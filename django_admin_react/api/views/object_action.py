"""``POST /api/v1/<app>/<model>/<pk>/action/<name>/`` — run an object action.

Wire contract: ``docs/api-contract.md`` §5 (an addition the human reviewer
must land — see the PR/report note).

Object-level change-page actions are the django-object-actions affordance
(``ModelAdmin.change_actions`` / ``get_change_actions``). This endpoint
runs one named action against a single object. It is the per-object
counterpart to the changelist ``actions`` runner (``views/actions.py``);
both never trust the client-supplied name as a callable lookup.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_change_permission(request, obj)`` per-object gate — object
           actions are change-shaped, matching how django-object-actions
           wires them onto the change view.
- Rule 10: Object loaded through ``ModelAdmin.get_object`` /
           ``get_queryset`` — never ``Model.objects.all()`` (B-2).
- Rule 12: The action ``name`` is verified against the *permitted* set
           (``get_change_actions``) before the callable runs; an unknown /
           non-permitted name is a 404 and the callable never executes.
           Action callables may raise — we catch and return a clean 400
           ``{ok: false, error}`` rather than a 500 (per the issue brief).
- CSRF:    No ``@csrf_exempt`` — Django's middleware enforces.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.object_actions import permitted_action_names
from django_admin_react.api.object_actions import resolve_action_callable
from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import not_found_response


class ObjectActionView(View):
    """``POST /api/v1/<app_label>/<model_name>/<pk>/action/<name>/``."""

    http_method_names = ["post"]

    def post(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        pk: str,
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Run one permitted object action against a single object.

        Gates, in order:

        1. ``is_admin_user`` — 403 if not authenticated active staff.
        2. ``resolve_model`` — 404 if the model is unknown / unviewable.
        3. ``load_object_or_none`` — 404 if the pk doesn't resolve under
           the admin's queryset (rule 10) or parse-fails.
        4. ``has_change_permission(request, obj)`` — per-object gate
           (object actions are change-shaped).
        5. ``permitted_action_names`` — 404 unless ``name`` is in the set
           the admin permits for this user + object (the callable never
           runs for a name not in that set).

        On success the response is ``{ok: true, message?, redirect?}``: if
        the callable returns a redirect ``HttpResponse`` we surface its URL
        as ``redirect`` (the API itself returns 200, never a 302, so the
        SPA controls navigation). If the callable raises, the response is
        ``{ok: false, error}`` with status 400 — never a 500.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        model, model_admin = resolved

        obj = load_object_or_none(model, model_admin, request, pk)
        if obj is None:
            return not_found_response()

        # Object actions are change-shaped — gate on change permission for
        # this object, the same posture django-object-actions takes by
        # wiring the buttons onto the change view.
        if not model_admin.has_change_permission(request, obj):
            return forbidden_response(request)

        # Never trust the URL ``name``: it must be in the admin's own
        # permitted set. ``None`` means the admin exposes no object actions
        # at all → 404 (the endpoint doesn't exist for this model).
        permitted = permitted_action_names(model_admin, request, obj)
        if permitted is None or name not in permitted:
            return not_found_response()

        action_callable = resolve_action_callable(model_admin, name)
        if action_callable is None:
            return not_found_response()

        # The action manages its own writes (it may or may not mutate), so
        # we do NOT force a surrounding ``transaction.atomic()`` — matching
        # django-object-actions, which calls the bound method directly. A
        # raising callable is caught and returned as a clean 400, never a
        # 500 (per the issue brief).
        try:
            result = action_callable(request, obj)
        except Exception:
            # The action callable raised — return a clean 400, never a 500.
            # The exception text can disclose internal detail, so we surface
            # only a generic, safe message (``SECURITY.md`` §3 rule 12); the
            # real cause is in the consumer's server logs, not the wire.
            return _json_response(
                {"ok": False, "error": "The action could not be completed."},
                status=400,
            )

        return _success_response(result)


def _success_response(result: Any) -> HttpResponse:
    """Build the ``{ok: true, message?, redirect?}`` success envelope.

    A redirect ``HttpResponse`` from the callable is surfaced as a
    ``redirect`` URL (we never echo a 302 — the SPA navigates client-side
    without a full-page reload). Any other ``HttpResponse`` is treated as
    "ran successfully" with no extra payload. The django-object-actions
    contract is that an action returns ``None`` (just ran) or an
    ``HttpResponse`` (commonly a redirect).
    """
    body: dict[str, Any] = {"ok": True}
    if isinstance(result, HttpResponse):
        # A redirect response carries a ``Location`` header (3xx). Mirror
        # the changelist action runner (``views/actions.py``): surface the
        # target so the SPA navigates client-side. ``url`` is set on
        # ``HttpResponseRedirect`` subclasses; the header is the fallback.
        target = getattr(result, "url", None) or result.get("Location", None)
        if target:
            body["redirect"] = str(target)
    return _json_response(body, status=200)


def _json_response(body: dict[str, Any], status: int) -> HttpResponse:
    """JSON envelope with the package's standard no-store cache header."""
    response = JsonResponse(body, status=status)
    response["Cache-Control"] = "no-store"
    return response
