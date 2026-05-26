"""Shared test helpers for the django-admin-react test suite.

This module holds utilities that are *not* pytest fixtures (those live
in ``conftest.py``). The split keeps fixture discovery automatic while
letting regular helpers be imported with ``from tests.helpers import X``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.contrib import admin


@contextmanager
def admin_override(model_cls, **method_returns) -> Iterator[None]:
    """Temporarily replace methods on a registered ``ModelAdmin``.

    Each keyword maps an attribute name on the admin instance to a
    function. The function is bound to the admin for the duration of
    the ``with`` block, then restored on exit.

    Example::

        with admin_override(Group, has_view_permission=lambda self, request, obj=None: False):
            response = client.get(LIST_URL)

    This is the canonical way to test "what does the admin say?"
    without swapping users — the user identity is not the contract;
    the admin's answer is. The contract is enforced by
    ``ModelAdmin.has_*_permission`` (and the related hooks like
    ``get_queryset``, ``save_model``, ``delete_model``); this helper
    lets each test pin those answers per-test.
    """
    model_admin = admin.site._registry[model_cls]
    originals: dict[str, object] = {}
    try:
        for name, fn in method_returns.items():
            originals[name] = getattr(model_admin, name)
            setattr(model_admin, name, fn.__get__(model_admin))
        yield
    finally:
        for name, original in originals.items():
            setattr(model_admin, name, original)
