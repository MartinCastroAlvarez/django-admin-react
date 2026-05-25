from django.contrib import admin
from django.test import TestCase

from examples.hr.models import (
    Department,
    Employee,
    PerformanceReview,
    Role,
    TimeOffRequest,
)


class HRAdminRegistrationTests(TestCase):
    def test_all_models_registered(self) -> None:
        for model in (Department, Role, Employee, TimeOffRequest, PerformanceReview):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)
