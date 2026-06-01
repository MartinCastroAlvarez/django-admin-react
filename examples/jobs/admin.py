"""``JobAdmin`` — the custom-form fixture that proves the legacy-iframe escape.

This admin uses *only* documented Django ``ModelAdmin`` hooks — no
django-admin-react / -rest-api / -mcp-specific API. The point: if this runs
on the React admin at ``/admin-react/`` with at most a single-view iframe
fallback, then any legacy ``/admin/`` ModelAdmin does too.

Two rendering paths:

* **Path A** — ``/admin-react/jobs/job/<pk>/change/`` (no query). The stock
  change form, fully describable by the form-spec contract.
  ``formfield_for_dbfield`` swaps ``metadata`` to a large textarea, which
  the SPA renders natively from ``widget.kind == "textarea"``.
* **Path B** — ``?run_custom=1``. ``change_view`` returns a hand-rolled
  dual-listbox template (not a ModelForm, not fieldsets). The form-spec
  resolver detects the custom render and returns
  ``{renderer: "legacy-iframe", legacy_url: …}``; the SPA embeds the legacy
  page in an iframe inside its own chrome.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse

from examples.jobs.models import Job


def get_step_registry() -> list[dict]:
    """The catalogue of pipeline steps a Job can run (plain demo data)."""
    return [
        {"name": "fetch", "label": "Fetch inputs", "default_order": 1, "is_default": True},
        {"name": "validate", "label": "Validate", "default_order": 2, "is_default": True},
        {"name": "transform", "label": "Transform", "default_order": 3, "is_default": True},
        {"name": "dry_run", "label": "Dry run", "default_order": 4, "is_default": False},
        {"name": "notify", "label": "Notify stakeholders", "default_order": 5, "is_default": False},
        {"name": "archive", "label": "Archive outputs", "default_order": 6, "is_default": False},
    ]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    actions = ["run_with_custom_steps"]

    # 1) request-aware widget override on a single DB field (Path A).
    def formfield_for_dbfield(self, db_field, request, **kwargs):  # noqa: ANN001
        if db_field.name == "metadata":
            kwargs["widget"] = admin.widgets.AdminTextareaWidget(attrs={"class": "vLargeTextField"})
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    # 2) action that redirects to the ?run_custom=1 variant of the change page.
    @admin.action(description="Run (Custom)")
    def run_with_custom_steps(self, request, queryset):  # noqa: ANN001
        if queryset.count() != 1:
            self.message_user(request, "Pick exactly one row.", level=messages.ERROR)
            return None
        obj = queryset.get()
        return HttpResponseRedirect(
            reverse("admin:jobs_job_change", args=[obj.pk]) + "?run_custom=1"
        )

    # 3) change_view override branching on request.GET.
    def change_view(self, request, object_id, form_url="", extra_context=None):  # noqa: ANN001
        if request.GET.get("run_custom") == "1":
            return self.run_custom_view(request, object_id)
        return super().change_view(request, object_id, form_url, extra_context)

    # 4) custom view rendering a custom template — not a ModelForm / fieldsets.
    def run_custom_view(self, request, object_id):  # noqa: ANN001
        obj = self.get_object(request, object_id)

        if request.method == "POST":
            selected = request.POST.getlist("selected_steps")  # ordered list
            if not selected:
                messages.error(request, "Pick at least one step.")
                return redirect(request.get_full_path())
            messages.success(request, f"Queued {' → '.join(selected)}")
            return redirect("admin:jobs_job_change", object_id)

        all_steps = get_step_registry()
        selected_steps = sorted(
            (s for s in all_steps if s["is_default"]),
            key=lambda s: s["default_order"],
        )
        available_steps = [s for s in all_steps if not s["is_default"]]

        context = dict(
            self.admin_site.each_context(request),
            title=f"Configure Step Sequence: {obj.name}",
            item_type="Job",
            item_name=obj.name,
            obj=obj,
            available_steps=available_steps,
            selected_steps=selected_steps,
            all_steps=sorted(all_steps, key=lambda s: s["default_order"]),
            back_url=reverse("admin:jobs_job_changelist"),
            cancel_url=reverse("admin:jobs_job_change", args=[obj.pk]),
            opts=self.model._meta,
            preserved_filters=self.get_preserved_filters(request),
        )
        return render(request, "admin/jobs/job/run_custom.html", context)
