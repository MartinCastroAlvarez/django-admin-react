"""Permission helpers.

The package's default permission gate is:

    user.is_active and user.is_staff and admin_site.has_permission(request)

Per-operation gates always go through the relevant
``ModelAdmin.has_*_permission(request, obj=None)`` method.

Implementation lands in PR #3.
"""
