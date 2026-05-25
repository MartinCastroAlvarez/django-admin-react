from django.contrib import admin
from django.test import TestCase

from examples.ecommerce.models import Category, Customer, Order, OrderItem, Product


class EcommerceAdminRegistrationTests(TestCase):
    def test_all_models_registered(self) -> None:
        for model in (Category, Product, Customer, Order, OrderItem):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)
