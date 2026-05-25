"""PATCH /api/v1/<app>/<model>/<pk>/ — implementation lands in PR #5.

Builds form initial from the existing instance, merges the request
body on top, validates with ``ModelAdmin.get_form(request, obj)``, and
saves via ``ModelAdmin.save_model(..., change=True)``. Writes to
readonly or excluded fields produce a 400.
"""
