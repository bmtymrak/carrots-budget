import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Category
from .forms import IncomeForm

User = get_user_model()


class IncomeFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

        cls.testuser1_category = Category.objects.create(
            name="category1", user=cls.user1
        )
        cls.testuser2_category = Category.objects.create(
            name="category1", user=cls.user2
        )

    def test_current_user_categories_show_in_form(self):
        form = IncomeForm(user=self.user1)
        self.assertTrue(len(form.fields["category"].queryset) == 1)
