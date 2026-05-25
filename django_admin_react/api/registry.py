"""AdminSite introspection helpers.

The package looks up ModelAdmin instances **only** through
``admin.site._registry`` (or the configured site's ``_registry``).
Client-provided ``app_label``/``model_name`` strings are resolved here
and never used to ``import_string`` a model.

Implementation lands in PR #3.
"""
