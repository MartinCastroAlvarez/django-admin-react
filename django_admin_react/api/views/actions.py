"""``POST /api/v1/<app>/<model>/actions/<action_name>/`` — run an admin action.

Wire contract: ``docs/api-contract.md`` §5.4.

Powers Django admin's ``actions = [...]`` mechanism for the SPA. The
caller picks an action by name and a list of pks; the package
re-resolves the action through ``ModelAdmin.get_actions(request)``
(never trusts the action name client-side), then runs it over the
queryset narrowed to those pks **and** the admin's own
``get_queryset(request)`` (so the action cannot touch rows the user
isn't allowed to see).

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_change_permission`` per-action gate (matches the
           legacy admin's posture — actions are change-shaped).
- Rule 10: Queryset starts at ``ModelAdmin.get_queryset(request)``
           and is narrowed by ``pk__in=<pks>`` — never bypasses the
           admin's row-level filtering (B-2).
- Rule 12: Bad input (unknown action name, empty pks) returns 400/404
           with the canonical envelope. Action callables may raise;
           we let those propagate as 500 so the consumer sees the
           real cause in their logs (we don't want to silently swallow
           an admin author's bug).
- CSRF:    No ``@csrf_exempt`` — Django's middleware enforces.
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.utils import model_format_dict
from django.db import transaction
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.writes import bad_request
from django_admin_react.api.writes import not_found_response
from django_admin_react.api.writes import parse_json_body


class ActionView(View):
    """``POST /api/v1/<app>/<model>/actions/<action_name>/``.

    Body: ``{"pks": [<pk>, ...], "confirmed": <bool>}``. ``confirmed``
    is informational only in v1 — the SPA passes it to indicate the
    user has acknowledged a confirmation step; the backend doesn't
    short-circuit on it (the action callable owns confirmation
    semantics).
    """

    http_method_names = ["post"]

    def post(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        action_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        _model, model_admin = resolved

        # Re-resolve the action through the admin — never trust the
        # action_name from the URL until ModelAdmin.get_actions
        # confirms it exists for this user.
        actions = model_admin.get_actions(request) or {}
        # ``actions[name]`` is a ``(callable, name, description)`` tuple
        # per Django admin's convention. ``.get`` + a None check both
        # rejects an unknown action and narrows the optional lookup.
        action_entry = actions.get(action_name)
        if action_entry is None:
            return not_found_response()
        action_callable = action_entry[0]

        # Actions are change-shaped — the legacy admin gates them
        # behind change permission. Match that posture so a user
        # who cannot edit a row cannot run an action on it either.
        if not model_admin.has_change_permission(request):
            return forbidden_response(request)

        parsed = parse_json_body(request)
        if isinstance(parsed, HttpResponse):
            return parsed
        payload: dict[str, Any] = parsed

        pks = payload.get("pks", [])
        if not isinstance(pks, list) or not pks:
            return bad_request("`pks` must be a non-empty list.")

        # The SPA runs its own styled confirm dialog, which stands in
        # for Django's intermediate HTML confirmation page. When it
        # reports the user confirmed, signal that to two-phase actions
        # that gate on the admin's ``post`` flag — most importantly the
        # built-in ``delete_selected``, which only deletes (via
        # ``ModelAdmin.delete_queryset``) when ``request.POST['post']``
        # is set and otherwise just renders the confirmation page.
        # Without this the SPA confirm would no-op: the page would be
        # rendered server-side and nothing deleted.
        if payload.get("confirmed"):
            request.POST = request.POST.copy()
            request.POST["post"] = "yes"

        # Narrow the queryset by both the admin's own get_queryset
        # (Rule 10) AND the pk filter. Order matters: get_queryset
        # FIRST, so the pk filter only sees rows the user could
        # already see — an action cannot reach rows behind
        # ``get_queryset``'s gate.
        queryset = model_admin.get_queryset(request).filter(pk__in=pks)

        with transaction.atomic():
            result = action_callable(model_admin, request, queryset)

        # Django admin's action contract: the callable may return an
        # ``HttpResponse`` (typically a redirect to a confirmation
        # page) — we surface that as a JSON envelope so the SPA can
        # follow it without parsing HTML.
        if isinstance(result, HttpResponse):
            body: dict[str, Any] = {"redirect": result["Location"]} if "Location" in result else {}
            body.update({"executed": True, "action": action_name})
            response = JsonResponse(body, status=200)
        else:
            response = JsonResponse(
                {"executed": True, "action": action_name, "pks": list(pks)},
                status=200,
            )
        response["Cache-Control"] = "no-store"
        return response


def actions_payload(model_admin: Any, request: HttpRequest) -> list[dict[str, Any]]:
    """Build the ``actions`` block of the list response.

    Each entry is ``{name, label, description, requires_confirmation}``.
    ``requires_confirmation`` is conservative: ``True`` only when the
    action's docstring or short_description hints at destructiveness
    (substring match on ``delete``). The SPA may always render a
    confirmation step regardless — this hint is a UX optimisation.
    """
    raw = model_admin.get_actions(request) or {}
    # Django's built-in `delete_selected` (and any action whose
    # `short_description` uses the admin's `%(verbose_name)s` /
    # `%(verbose_name_plural)s` placeholders) ships a *format string*,
    # not a finished label — Django interpolates it at render time via
    # `model_format_dict(opts)`. Do the same here so the SPA shows
    # "Delete selected files", never the raw "%(verbose_name_plural)s".
    fmt = model_format_dict(model_admin.model._meta)
    out: list[dict[str, Any]] = []
    for name, (_callable, _resolved_name, description) in raw.items():
        raw_label = str(description) if description else name
        try:
            label = raw_label % fmt
        except (KeyError, ValueError, TypeError):
            # Not a %-format string, or references a key we don't
            # provide — surface the label verbatim rather than crashing.
            label = raw_label
        requires_conf = "delete" in (label.lower() + " " + name.lower())
        out.append(
            {
                "name": name,
                "label": label,
                "description": label,
                "requires_confirmation": requires_conf,
            }
        )
    return out
