from django.contrib import admin

from .models import Category, Comment, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "published_at", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "body", "author__username")
    autocomplete_fields = ("author", "category")
    readonly_fields = ("created_at",)
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author_name", "is_approved", "created_at")
    list_filter = ("is_approved",)
    search_fields = ("author_name", "body", "post__title")
    autocomplete_fields = ("post",)
    readonly_fields = ("created_at",)
