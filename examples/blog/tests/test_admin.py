from django.contrib import admin
from django.test import TestCase

from examples.blog.models import Category, Comment, Post, Tag


class BlogAdminRegistrationTests(TestCase):
    def test_all_models_registered(self) -> None:
        for model in (Category, Tag, Post, Comment):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)
