from django.test import TestCase
from django.contrib.auth import get_user_model
import datetime

from purchases.models import Category
from budgets.models import BudgetItem, YearlyBudget, ExpenseSource
from budgets.forms import BudgetItemForm, YearlyBudgetForm, ExpenseSourceForm


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
        self.assertEqual(
            list(form.fields["category"].queryset),
            [self.testuser1_category],
        )

        foreign_category_form = BudgetItemForm(
            data={
                "category": self.testuser2_category.pk,
                "amount": "10.00",
                "savings": False,
                "notes": "",
            },
            user=self.user1,
        )

        self.assertFalse(foreign_category_form.is_valid())
        self.assertIn("category", foreign_category_form.errors)

    def test_correct_fields_in_form(self):
        form = BudgetItemForm(user=self.user1)
        expected_fields = [
            "category",
            "new_category",
            "amount",
            "savings",
            "notes",
        ]

        self.assertEqual(list(form.fields.keys()), expected_fields)


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
        """Test that the form includes appropriate year choices"""
        form = YearlyBudgetForm()
        # Get the year choices
        year_choices = [int(choice[0]) for choice in form.fields['year'].choices]
        
        # Current year should be in choices
        current_year = datetime.date.today().year
        self.assertIn(current_year, year_choices)
        
        # Should include future years (at least current + 5)
        self.assertIn(current_year + 5, year_choices)
        
        # Should include past years (at least back to 2000)
        self.assertIn(2000, year_choices)
        
        # Test valid year
        form = YearlyBudgetForm(data={"year": 2025})
        form.instance.user = self.user1
        self.assertTrue(form.is_valid())

    def test_yearly_budget_form_defaults_to_current_year(self):
        """Test that the form defaults to the current year"""
        form = YearlyBudgetForm()
        current_year = datetime.date.today().year
        self.assertEqual(form.fields['year'].initial, current_year)


class ExpenseSourceFormTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="expense-source-form@test.com",
            username="expense-source-form",
            password="testpass123",
        )

    def test_normalizes_whitespace(self):
        form = ExpenseSourceForm(
            data={"name": "  Bank   statement  "},
            user=self.user,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Bank statement")

    def test_rejects_duplicate_name_case_insensitively(self):
        ExpenseSource.objects.create(user=self.user, name="Bank statement")
        form = ExpenseSourceForm(
            data={"name": "BANK STATEMENT"},
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("already have an expense source", str(form.errors))


class BudgetCategoryChoiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="category-owner", email="category-owner@example.com")
        other_user = User.objects.create_user(username="category-other", email="category-other@example.com")
        cls.category = Category.objects.create(user=cls.user, name="Food")
        cls.foreign_category = Category.objects.create(user=other_user, name="Food")

    def test_create_requires_exactly_one_category(self):
        cases = [
            (self.category.pk, "", True), ("", " New name ", True),
            ("", "", False), ("", "   ", False), ("", "x" * 251, False),
            (self.category.pk, "New name", False),
            (self.foreign_category.pk, "", False),
            (self.foreign_category.pk, "New name", False),
        ]
        for category, name, valid in cases:
            with self.subTest(category=category, name=name):
                form = BudgetItemForm(
                    user=self.user,
                    data={"category": category, "new_category": name, "amount": "10"},
                )
                self.assertEqual(form.is_valid(), valid, form.errors)
                if valid and name:
                    self.assertEqual(form.cleaned_data["new_category"], "New name")

    def test_edit_only_accepts_existing_category(self):
        from budgets.forms import BudgetItemEditForm

        self.assertNotIn("new_category", BudgetItemEditForm(user=self.user).fields)
        cases = [
            (self.category.pk, None, True), ("", None, False),
            ("", "New name", False), ("", "   ", False), ("", "x" * 251, False),
            (self.category.pk, "New name", False),
            (self.category.pk, "   ", False), (self.category.pk, "", False),
            (self.foreign_category.pk, None, False),
        ]
        for category, name, valid in cases:
            with self.subTest(category=category, name=name):
                data = {"category": category, "amount": "10"}
                if name is not None:
                    data["new_category"] = name
                form = BudgetItemEditForm(user=self.user, data=data)
                self.assertEqual(form.is_valid(), valid, form.errors)
