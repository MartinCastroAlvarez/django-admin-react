from django.contrib import admin
from django.test import TestCase

from examples.fintech.models import Account, Card, Statement, Transaction


class FintechAdminRegistrationTests(TestCase):
    """Smoke tests: every fintech model is registered with the admin site."""

    def test_all_models_registered(self) -> None:
        for model in (Account, Transaction, Statement, Card):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)
