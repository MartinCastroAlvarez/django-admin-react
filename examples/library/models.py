from django.conf import settings
from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=120)
    country = models.CharField(max_length=80, blank=True)
    born = models.DateField(null=True, blank=True)
    died = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    class Language(models.TextChoices):
        EN = "en", "English"
        ES = "es", "Spanish"
        FR = "fr", "French"
        DE = "de", "German"
        PT = "pt", "Portuguese"

    title = models.CharField(max_length=240)
    isbn = models.CharField(max_length=17, unique=True)
    author = models.ForeignKey(Author, on_delete=models.PROTECT, related_name="books")
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="books")
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.EN)
    published_date = models.DateField(null=True, blank=True)
    page_count = models.PositiveIntegerField(default=0)
    summary = models.TextField(blank=True)
    in_stock = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class Member(models.Model):
    class Membership(models.TextChoices):
        STANDARD = "standard", "Standard"
        STUDENT = "student", "Student"
        STAFF = "staff", "Library staff"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="library_member",
    )
    membership_type = models.CharField(
        max_length=16,
        choices=Membership.choices,
        default=Membership.STANDARD,
    )
    member_since = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-member_since"]

    def __str__(self) -> str:
        return f"{self.user} ({self.membership_type})"


class Loan(models.Model):
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="loans")
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="loans")
    loaned_at = models.DateTimeField()
    due_at = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-loaned_at"]

    def __str__(self) -> str:
        suffix = "returned" if self.returned_at else "out"
        return f"{self.book} → {self.member} ({suffix})"
