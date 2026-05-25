from django.contrib import admin

from .models import Department, Employee, PerformanceReview, Role, TimeOffRequest


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "seniority")
    list_filter = ("seniority", "department")
    search_fields = ("title", "department__name")
    autocomplete_fields = ("department",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_number", "user", "role", "hired_at", "is_active")
    list_filter = ("is_active", "role__department")
    search_fields = ("employee_number", "user__username", "user__email")
    autocomplete_fields = ("user", "role")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.append("salary")
        return readonly

    def get_exclude(self, request, obj=None):
        excluded = list(super().get_exclude(request, obj) or [])
        if not request.user.is_superuser:
            excluded.append("salary")
        return excluded


@admin.register(TimeOffRequest)
class TimeOffRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "kind", "start_date", "end_date", "status", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("employee__user__username", "reason")
    autocomplete_fields = ("employee",)
    readonly_fields = ("created_at",)
    date_hierarchy = "start_date"


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    """Restricted to superusers — exercises the permission-gating contract."""

    list_display = ("employee", "reviewer", "review_date", "score")
    list_filter = ("score",)
    search_fields = ("employee__user__username", "summary")
    autocomplete_fields = ("employee", "reviewer")
    date_hierarchy = "review_date"

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)
