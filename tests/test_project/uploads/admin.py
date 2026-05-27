from django.contrib import admin

from tests.test_project.uploads.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "attachment")
