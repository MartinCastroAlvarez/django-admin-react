from django.contrib import admin

from .models import Author, Book, Genre, Loan, Member


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "book_count")
    search_fields = ("name",)

    @admin.display(description="Books")
    def book_count(self, obj: Genre) -> int:
        return obj.books.count()


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "born", "died")
    list_filter = ("country",)
    search_fields = ("name", "country")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "genre", "language", "in_stock", "published_date")
    list_filter = ("language", "genre")
    search_fields = ("title", "isbn", "author__name")
    autocomplete_fields = ("author", "genre")
    readonly_fields = ("isbn",)


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("user", "membership_type", "is_active", "member_since")
    list_filter = ("membership_type", "is_active")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("member_since",)
    autocomplete_fields = ("user",)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("book", "member", "loaned_at", "due_at", "returned_at")
    list_filter = ("returned_at",)
    search_fields = ("book__title", "member__user__username")
    autocomplete_fields = ("book", "member")
    date_hierarchy = "loaned_at"
