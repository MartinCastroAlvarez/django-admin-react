"""GET /api/v1/<app>/<model>/<pk>/ — implementation lands in PR #4.

Field set is the form's declared fields (from ``ModelAdmin.get_form``)
intersected with ``get_fields(request, obj)``. Anything in
``get_readonly_fields`` is marked ``readonly: true``. Anything in
``get_exclude`` is omitted.
"""
