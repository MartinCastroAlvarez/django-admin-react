"""``POST /api/v1/<app>/<model>/<pk>/password/`` — admin password set/change.

Wire contract: ``docs/api-contract.md`` §5.4.

A thin JSON shell over the admin's **own** password-change form — the
same philosophy as the login endpoint (``views/auth.py``): the package
never invents password handling. Django's ``UserAdmin`` exposes
``change_password_form`` (default ``AdminPasswordChangeForm``); this view
instantiates *that* form, validates it (which runs the configured
``AUTH_PASSWORD_VALIDATORS``), and calls ``form.save()`` — which routes
through ``user.set_password()``, so the password is hashed by Django's
configured hasher and a plaintext value is never persisted.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  The admin's ``change_password_form`` + ``set_password`` are
           the only password machinery — no parallel implementation.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_change_permission(request, obj)`` per-object gate —
           the same permission Django's own ``user_change_password``
           view requires.
- Rule 12: The 404 / 403 bodies leak no app/model/pk oracle.

Security properties (each is load-bearing — see ``tests/test_password.py``):

- **The password is never read back.** The success body is
  ``{"detail": ..., "id": pk}`` — no password, no hash, nothing derived
  from the credential. The model's password field also stays hidden in
  every read response via the sensitive-name denylist.
- **The password is never logged or echoed.** It is read from the JSON
  body, handed straight to the admin form, and never formatted into a
  message or response. Validation errors are mapped by *field name*
  (``password1`` / ``password2``), never by value.
- **CSRF is enforced.** This view is not ``@csrf_exempt``; Django's
  ``CsrfViewMiddleware`` runs before this code, so a forged cross-site
  POST cannot reset a victim's password.
- **Models without the affordance 404.** A model whose admin does not
  declare ``change_password_form`` (i.e. anything but a ``UserAdmin``)
  has no ``/password/`` sub-resource — mirroring Django, whose router
  only registers the password URL on ``UserAdmin``.
- **The acting admin is not logged out.** When a user changes *their
  own* password, ``update_session_auth_hash`` rotates the session auth
  hash so the current session survives — exactly what Django's
  ``user_change_password`` view does.
- **``Cache-Control: no-store``** on every response.

Out of scope (same as login, documented in ``SECURITY.md`` §2):
brute-force throttling. The package never replaces Django's password
*mechanism*, only adds a JSON entry point to it; rate limiting remains
the consumer's job (``django-ratelimit`` / ``django-axes``).
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import password_change_form_class
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.writes import form_errors_to_envelope
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import not_found_response
from django_admin_react.api.writes import parse_json_body
from django_admin_react.api.writes import validation_failed


class SetPasswordView(View):
    """``POST /api/v1/<app_label>/<model_name>/<pk>/password/``."""

    http_method_names = ["post"]

    def post(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        pk: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Set/change one user's password through the admin's own form.

        Gates, in order (mirrors ``update.py`` plus a capability check):

        1. ``is_admin_user`` — 403 if not authenticated active staff.
        2. ``resolve_model`` — 404 if the model is unknown / unviewable.
        3. ``password_change_form_class`` — 404 if this admin has no
           password-change affordance (not a ``UserAdmin``). Done before
           the object load so a non-user model never hits the DB here.
        4. ``load_object_or_none`` — 404 if the pk doesn't resolve under
           the admin's queryset (rule 10) or parse-fails.
        5. ``has_change_permission(request, obj)`` — per-object gate
           (rule 5), the same permission Django's password view requires.

        The body is ``{"password1": "...", "password2": "..."}`` — the
        admin form's own field names, so validation errors map straight
        back by field. ``form.save()`` hashes via ``set_password``; the
        write + the ``LogEntry`` share one transaction.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        model, model_admin = resolved

        form_class = password_change_form_class(model_admin)
        if form_class is None:
            # No password-change affordance on this admin — the
            # ``/password/`` sub-resource does not exist for this model.
            return not_found_response()

        obj = load_object_or_none(model, model_admin, request, pk)
        if obj is None:
            return not_found_response()

        if not model_admin.has_change_permission(request, obj):
            return forbidden_response(request)

        parsed = parse_json_body(request)
        if isinstance(parsed, HttpResponse):
            return parsed

        # The admin form takes the target user positionally; ``data`` is
        # the parsed JSON object. Validation runs ``clean_password2``
        # (match check) and ``AUTH_PASSWORD_VALIDATORS`` automatically.
        form = form_class(obj, data=parsed)
        if not form.is_valid():
            return validation_failed(form_errors_to_envelope(form))

        with transaction.atomic():
            form.save()
            # Mirror Django's ``user_change_password``: when the actor
            # changes their OWN password, keep their session alive by
            # rotating the session auth hash (otherwise the password
            # change would log them straight out).
            if request.user.pk == obj.pk:
                update_session_auth_hash(request, obj)
            # Audit parity: the legacy admin logs a CHANGE with the fixed
            # "Changed password." message (never the value or a diff of
            # the password fields). Match it byte-for-byte.
            model_admin.log_change(request, obj, "Changed password.")

        response = JsonResponse({"detail": "Password set.", "id": obj.pk}, status=200)
        response["Cache-Control"] = "no-store"
        return response
