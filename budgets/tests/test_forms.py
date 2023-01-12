from django.test import TestCase
from django.contrib.auth import get_user_model

from purchases.models import Category
from budgets.models import BudgetItem
from budgets.forms import BudgetItemForm


User = get_user_model()


class BudgetItemFormTest(TestCase):
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

    def test_only_current_user_categories_show_in_form(self):
        form = BudgetItemForm(user=self.user1)
        self.assertEqual(form.fields["category"].queryset.count(), 1)
