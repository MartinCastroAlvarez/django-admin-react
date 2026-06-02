"""``PipelineAdmin`` — the many-actions fixture that pins the detail-page
toolbar wrapping behaviour (#672).

The point of this admin is purely the *number* and *width* of its actions.
Stock Django ``@admin.action`` declarations only:

* **12 batch actions** — default (queryset-shaped) third parameter, so the API
  signature classifier marks them ``target: "batch"``. They render BOTH in the
  changelist multi-select dropdown AND as buttons on the detail page.
* **2 detail-only actions** — ``obj_id`` / ``str``-shaped third parameter, so
  the classifier marks them ``target: "detail"``. They render ONLY as detail
  buttons, never in the changelist dropdown.

14 buttons (several with long descriptions) on one detail page cannot fit on a
single row at 1280/1024/768/480 px. Before #672 the toolbar overflowed
horizontally and pushed the H1 title + breadcrumb off-screen; now the SPA
stacks the header as three full-width rows and ``flex-wrap``s the toolbar.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib import messages

from examples.many_actions.models import Pipeline


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    actions = [
        "recompute_derived_field_a",
        "recompute_derived_field_b",
        "recompute_derived_field_c",
        "rerun_pipeline_step_1",
        "rerun_pipeline_step_2",
        "rerun_pipeline_step_3",
        "invalidate_downstream_cache",
        "mark_as_reviewed_by_operator",
        "mark_as_pending_operator_review",
        "export_selected_rows_as_csv",
        "export_selected_rows_as_json",
        "notify_owner_of_selected_rows",
    ]

    # --- 12 batch actions (changelist dropdown + detail button) ----------- #

    @admin.action(description="Recompute Derived Field A")
    def recompute_derived_field_a(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Recomputed Derived Field A.", level=messages.SUCCESS)

    @admin.action(description="Recompute Derived Field B")
    def recompute_derived_field_b(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Recomputed Derived Field B.", level=messages.SUCCESS)

    @admin.action(description="Recompute Derived Field C")
    def recompute_derived_field_c(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Recomputed Derived Field C.", level=messages.SUCCESS)

    @admin.action(description="Re-run Pipeline Step 1")
    def rerun_pipeline_step_1(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Re-ran Pipeline Step 1.", level=messages.SUCCESS)

    @admin.action(description="Re-run Pipeline Step 2")
    def rerun_pipeline_step_2(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Re-ran Pipeline Step 2.", level=messages.SUCCESS)

    @admin.action(description="Re-run Pipeline Step 3")
    def rerun_pipeline_step_3(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Re-ran Pipeline Step 3.", level=messages.SUCCESS)

    @admin.action(description="Invalidate Downstream Cache")
    def invalidate_downstream_cache(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Invalidated downstream cache.", level=messages.SUCCESS)

    @admin.action(description="Mark As Reviewed By Operator")
    def mark_as_reviewed_by_operator(self, request, queryset):  # noqa: ANN001
        queryset.update(status="reviewed")

    @admin.action(description="Mark As Pending Operator Review")
    def mark_as_pending_operator_review(self, request, queryset):  # noqa: ANN001
        queryset.update(status="pending_review")

    @admin.action(description="Export Selected Rows As CSV")
    def export_selected_rows_as_csv(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Exported as CSV.", level=messages.SUCCESS)

    @admin.action(description="Export Selected Rows As JSON")
    def export_selected_rows_as_json(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Exported as JSON.", level=messages.SUCCESS)

    @admin.action(description="Notify Owner Of Selected Rows")
    def notify_owner_of_selected_rows(self, request, queryset):  # noqa: ANN001
        self.message_user(request, "Notified owners.", level=messages.SUCCESS)

    # --- 2 detail-only actions (detail button only) ----------------------- #
    # `obj_id` / `str`-shaped third parameter → classifier marks `detail`.

    @admin.action(description="Open Detailed Audit View For This Pipeline Run")
    def open_detailed_audit_view(self, request, obj_id: str):  # noqa: ANN001
        self.message_user(request, f"Opened audit view for {obj_id}.", level=messages.INFO)

    @admin.action(description="Replay Last Operation On This Pipeline Run")
    def replay_last_operation(self, request, obj_id: str):  # noqa: ANN001
        self.message_user(request, f"Replayed last operation on {obj_id}.", level=messages.INFO)
