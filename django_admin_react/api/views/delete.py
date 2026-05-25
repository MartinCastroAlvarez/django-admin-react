"""DELETE /api/v1/<app>/<model>/<pk>/ — implementation lands in PR #5.

Checks ``has_delete_permission(request, obj)`` and then calls
``ModelAdmin.delete_model(request, obj)``. Never ``obj.delete()``.
"""
