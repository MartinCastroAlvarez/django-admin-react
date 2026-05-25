from django.contrib import admin

from .models import Account, Card, Statement, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "currency", "balance", "is_active", "created_at")
    list_filter = ("currency", "is_active")
    search_fields = ("name", "iban", "owner__username")
    readonly_fields = ("iban", "created_at")
    autocomplete_fields = ("owner",)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "kind", "amount", "description", "posted_at", "reference")
    list_filter = ("kind",)
    search_fields = ("reference", "description", "account__name")
    date_hierarchy = "posted_at"
    autocomplete_fields = ("account",)
    readonly_fields = ("reference",)


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "period_start",
        "period_end",
        "opening_balance",
        "closing_balance",
        "generated_at",
    )
    list_filter = ("account__currency",)
    search_fields = ("account__name", "account__iban")
    readonly_fields = ("generated_at",)
    autocomplete_fields = ("account",)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("masked_number", "holder_name", "account", "expires_at", "status")
    list_filter = ("status",)
    search_fields = ("holder_name", "last4", "account__name")
    autocomplete_fields = ("account",)
    readonly_fields = ("last4",)

    @admin.display(description="Card")
    def masked_number(self, obj: Card) -> str:
        return f"**** **** **** {obj.last4}"
