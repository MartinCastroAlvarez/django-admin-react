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
    # Stock Django admin actions (`@admin.action`). They surface on the
    # changelist (multi-pk runs) AND the SPA's detail page header
    # (single-pk runs) — no `django-object-actions` mixin, no
    # `change_actions = [...]` redeclaration. One source of truth for
    # everything the consumer wants to expose as an action.
    actions = ("mark_reconciled", "recompute_reference")

    @admin.action(description="Mark as reconciled")
    def mark_reconciled(self, request, queryset):
        """Tag every row in the queryset as reconciled.

        Demo no-op: the model has no `reconciled` flag yet — this
        exists so the SPA's detail page has a stock-Django-admin
        action to render. A real ModelAdmin would update the row
        and message the user.
        """
        count = queryset.count()
        self.message_user(request, f"Marked {count} transaction(s) as reconciled.")

    @admin.action(description="Recompute reference")
    def recompute_reference(self, request, queryset):
        """Roll the ``reference`` field on each row in the queryset.

        Demo: bumps ``reference`` to ``TXN-RECOMP-<stamp>-<i>`` so the
        operator can see the action ran end-to-end on the SPA.
        """
        from datetime import datetime, timezone as tz
        stamp = datetime.now(tz.utc).strftime("%Y%m%d%H%M%S")
        for i, row in enumerate(queryset):
            row.reference = f"TXN-RECOMP-{stamp}-{i:02d}"
            row.save(update_fields=["reference"])
        self.message_user(request, f"Recomputed reference on {queryset.count()} row(s).")


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
