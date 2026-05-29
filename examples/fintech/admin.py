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
    # Stock Django admin actions (`@admin.action`). Same `actions = (...)`
    # declaration, two render surfaces — the API (1.0.6+) inspects each
    # callable's third-parameter NAME / ANNOTATION and classifies it:
    #
    #   - `mark_reconciled(self, request, queryset)`     → batch
    #     → renders on the changelist with multi-select.
    #   - `reprocess(self, request, obj_id: str)`        → detail
    #     → renders as a button on the single-object detail page.
    #
    # Same admin declaration. One actions tuple. Signature decides
    # where the SPA renders the button.
    actions = ("mark_reconciled", "recompute_reference", "reprocess")

    @admin.action(description="Mark as reconciled")
    def mark_reconciled(self, request, queryset):
        """Changelist (`batch`) action — operates on every selected row.

        Demo no-op: the model has no `reconciled` flag yet, so this
        just message_users the count. Renders on the changelist
        because the third parameter is named `queryset`.
        """
        count = queryset.count()
        self.message_user(request, f"Marked {count} transaction(s) as reconciled.")

    @admin.action(description="Recompute reference")
    def recompute_reference(self, request, queryset):
        """Changelist (`batch`) action — bumps every selected row's
        ``reference`` so the operator can see the action ran end-to-end
        from the changelist."""
        from datetime import datetime, timezone as tz
        stamp = datetime.now(tz.utc).strftime("%Y%m%d%H%M%S")
        for i, row in enumerate(queryset):
            row.reference = f"TXN-RECOMP-{stamp}-{i:02d}"
            row.save(update_fields=["reference"])
        self.message_user(request, f"Recomputed reference on {queryset.count()} row(s).")

    @admin.action(description="Reprocess this transaction")
    def reprocess(self, request, obj_id: str):
        """Detail-page (`detail`) action — operates on the single
        object behind the detail view.

        Renders on the SPA's detail page header (not on the
        changelist) because the third parameter is annotated `str`
        and named `obj_id` — both signals tell the API's classifier
        the action expects a single object id, not a queryset.

        Demo: writes a `reference` tag so the operator can see the
        action ran end-to-end without leaving the detail view.
        """
        from datetime import datetime, timezone as tz
        stamp = datetime.now(tz.utc).strftime("%Y%m%d%H%M%S")
        row = Transaction.objects.get(pk=obj_id)
        row.reference = f"TXN-REPROC-{stamp}"
        row.save(update_fields=["reference"])
        self.message_user(request, f"Reprocessed transaction {row.pk}.")


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
