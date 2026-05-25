"""GET /api/v1/registry/ — implementation lands in PR #3.

Returns the apps/models the requesting user can see, filtered by
``ModelAdmin.has_module_permission`` and ``has_view_permission``.
"""
