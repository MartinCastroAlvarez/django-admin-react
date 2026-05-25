"""GET /api/v1/<app>/<model>/ — implementation lands in PR #4.

Must start from ``ModelAdmin.get_queryset(request)`` and apply
``get_search_results(request, qs, q)`` for the ``?q=`` parameter.
``columns`` come from ``get_list_display(request)``. Never calls
``Model.objects.all()``.
"""
