from decimal import Decimal

from django.conf import settings
from django.db import models


class Currency(models.TextChoices):
    USD = "USD", "US Dollar"
    EUR = "EUR", "Euro"
    GBP = "GBP", "Pound Sterling"
    ARS = "ARS", "Argentine Peso"


class Account(models.Model):
    name = models.CharField(max_length=120)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fintech_accounts",
    )
    iban = models.CharField(max_length=34, unique=True)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency})"


class Transaction(models.Model):
    class Kind(models.TextChoices):
        DEBIT = "debit", "Debit"
        CREDIT = "credit", "Credit"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    kind = models.CharField(max_length=8, choices=Kind.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.CharField(max_length=240, blank=True)
    reference = models.CharField(max_length=64, blank=True, db_index=True)
    posted_at = models.DateTimeField()

    class Meta:
        ordering = ["-posted_at"]

    def __str__(self) -> str:
        return f"{self.kind} {self.amount} on {self.account}"


class Statement(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="statements")
    period_start = models.DateField()
    period_end = models.DateField()
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "period_start", "period_end"],
                name="fintech_statement_unique_period",
            ),
        ]

    def __str__(self) -> str:
        return f"Statement {self.period_start}..{self.period_end} for {self.account}"


class Card(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"
        EXPIRED = "expired", "Expired"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="cards")
    holder_name = models.CharField(max_length=120)
    last4 = models.CharField(max_length=4)
    expires_at = models.DateField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["-expires_at"]

    def __str__(self) -> str:
        return f"**** **** **** {self.last4} ({self.status})"
