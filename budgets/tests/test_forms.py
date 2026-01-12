from django.test import TestCase
from django.contrib.auth import get_user_model
import datetime

from purchases.models import Category
from budgets.models import BudgetItem, YearlyBudget
from budgets.forms import BudgetItemForm, YearlyBudgetForm


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

    def test_correct_fields_in_form(self):
        form = BudgetItemForm(user=self.user1)
        expected_fields = [
            "category",
            "new_category",
            "amount",
            "savings",
            "notes",
        ]

        self.assertTrue(
            all([field in expected_fields for field in list(form.fields.keys())])
        )


class YearlyBudgetFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

    def test_yearly_budget_form_has_year_field(self):
        """Test that the form has a year field instead of date field"""
        form = YearlyBudgetForm()
        self.assertIn("year", form.fields)
        self.assertNotIn("date", form.fields)

    def test_yearly_budget_form_accepts_year(self):
        """Test that the form accepts a year and creates the budget correctly"""
        form = YearlyBudgetForm(data={"year": 2024})
        form.instance.user = self.user1
        self.assertTrue(form.is_valid())
        yearly_budget = form.save()
        self.assertEqual(yearly_budget.date.year, 2024)
        self.assertEqual(yearly_budget.date.month, 1)
        self.assertEqual(yearly_budget.date.day, 1)

    def test_yearly_budget_form_validates_duplicate_year(self):
        """Test that the form prevents duplicate yearly budgets for the same user and year"""
        # Create an existing yearly budget
        YearlyBudget.objects.create(user=self.user1, date=datetime.date(2024, 1, 1))
        
        # Try to create another one for the same year
        form = YearlyBudgetForm(data={"year": 2024})
        form.instance.user = self.user1
        self.assertFalse(form.is_valid())
        self.assertIn("year", form.errors)
        self.assertIn("already exists", str(form.errors["year"]))

    def test_yearly_budget_form_allows_different_users_same_year(self):
        """Test that different users can create budgets for the same year"""
        # Create a yearly budget for user1
        YearlyBudget.objects.create(user=self.user1, date=datetime.date(2024, 1, 1))
        
        # User2 should be able to create a budget for the same year
        form = YearlyBudgetForm(data={"year": 2024})
        form.instance.user = self.user2
        self.assertTrue(form.is_valid())
        yearly_budget = form.save()
        self.assertEqual(yearly_budget.user, self.user2)
        self.assertEqual(yearly_budget.date.year, 2024)

    def test_yearly_budget_form_year_range(self):
        """Test that the form validates year range"""
        # Test minimum year
        form = YearlyBudgetForm(data={"year": 1999})
        form.instance.user = self.user1
        self.assertFalse(form.is_valid())
        
        # Test maximum year
        form = YearlyBudgetForm(data={"year": 2101})
        form.instance.user = self.user1
        self.assertFalse(form.is_valid())
        
        # Test valid year
        form = YearlyBudgetForm(data={"year": 2025})
        form.instance.user = self.user1
        self.assertTrue(form.is_valid())
