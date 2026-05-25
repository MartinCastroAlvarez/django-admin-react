from decimal import Decimal

from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Role(models.Model):
    class Seniority(models.TextChoices):
        JUNIOR = "junior", "Junior"
        MID = "mid", "Mid"
        SENIOR = "senior", "Senior"
        STAFF = "staff", "Staff"
        PRINCIPAL = "principal", "Principal"

    title = models.CharField(max_length=120)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="roles")
    seniority = models.CharField(max_length=12, choices=Seniority.choices, default=Seniority.MID)

    class Meta:
        ordering = ["department__name", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["title", "department", "seniority"],
                name="hr_role_unique_title_department_seniority",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.department} ({self.seniority})"


class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hr_employee",
    )
    employee_number = models.CharField(max_length=32, unique=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="employees")
    hired_at = models.DateField()
    terminated_at = models.DateField(null=True, blank=True)
    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Sensitive — only superusers can see/edit (enforced in admin).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-hired_at"]

    def __str__(self) -> str:
        return f"{self.user} ({self.employee_number})"


class TimeOffRequest(models.Model):
    class Kind(models.TextChoices):
        VACATION = "vacation", "Vacation"
        SICK = "sick", "Sick"
        PERSONAL = "personal", "Personal"
        UNPAID = "unpaid", "Unpaid"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="time_off")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.employee} {self.kind} {self.start_date}..{self.end_date}"


class PerformanceReview(models.Model):
    """Restricted: only superusers can see/edit this model in the admin."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hr_reviews_authored",
    )
    review_date = models.DateField()
    summary = models.TextField()
    score = models.PositiveSmallIntegerField(help_text="1..5")
    recommended_action = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-review_date"]

    def __str__(self) -> str:
        return f"Review of {self.employee} on {self.review_date}"
