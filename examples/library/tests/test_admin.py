from django.contrib import admin
from django.test import TestCase

from examples.library.models import Author, Book, Genre, Loan, Member


class LibraryAdminRegistrationTests(TestCase):
    def test_all_models_registered(self) -> None:
        for model in (Genre, Author, Book, Member, Loan):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)
