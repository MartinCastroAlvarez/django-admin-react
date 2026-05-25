from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Legacy HTML admin — kept side-by-side so reviewers can compare.
    path("admin/legacy/", admin.site.urls),
    # The React admin. The mount point is the consumer's choice; this
    # demo uses `/admin-react/` (and `/admin/` once PR #5 lands and we
    # are confident the React UI is feature-complete enough to be the
    # default).
    path("admin-react/", include("django_admin_react.urls")),
]
