"""POST /api/v1/<app>/<model>/ — implementation lands in PR #5.

Constructs ``ModelAdmin.get_form(request)(data=payload)``, calls
``form.is_valid()``, and on success calls
``ModelAdmin.save_model(request, instance, form, change=False)``.
Unknown keys in the payload return 400; no manual setattr.
"""
