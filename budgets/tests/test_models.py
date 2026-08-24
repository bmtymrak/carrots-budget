import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from budgets.models import (
    YearlyBudget,
    MonthlyBudget,
    BudgetItem,
    Rollover,
    ExpenseSource,
    ExpenseSourceCheck,
    ExpenseSourceMonth,
)
from budgets.forms import BudgetItemForm
from purchases.models import Category

User = get_user_model()


class TestYearlyBudget(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testemail@test.com", username="testuser", password="testpass123"
        )

    def test_monthly_budgets_created(self):
        YearlyBudget.objects.create(user=self.user1, date=datetime.datetime.now())

        self.assertEqual(MonthlyBudget.objects.all().count(), 12)

    def test_unique_constraint(self):
        YearlyBudget.objects.create(user=self.user1, date=datetime.date.today())

        with self.assertRaises(IntegrityError):
            YearlyBudget.objects.create(user=self.user1, date=datetime.date.today())


class TestMonthlyBudget(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testemail@test.com", username="testuser", password="testpass123"
        )

        cls.yearly_budget = YearlyBudget.objects.create(
            user=cls.user1, date=datetime.date.today()
        )

    def test_unique_constraint(self):
        MonthlyBudget.objects.create(
            user=self.user1,
            date=datetime.date.today(),
            yearly_budget=self.yearly_budget,
        )

        with self.assertRaises(IntegrityError):
            MonthlyBudget.objects.create(
                user=self.user1,
                date=datetime.date.today(),
                yearly_budget=self.yearly_budget,
            )


class TestBudgetItem(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testemail@test.com", username="testuser", password="testpass123"
        )

        YearlyBudget.objects.create(user=cls.user1, date=datetime.datetime.now())

    def test_create_items_and_rollovers(self):
        self.client.login(email="testemail@test.com", password="testpass123")

        category = Category.objects.create(user=self.user1, name="Test category")
        data = {"category": category, "amount": 1.99}

        form = BudgetItemForm(data, user=self.user1)
        form.is_valid()

        BudgetItem.create_items_and_rollovers(
            self.user1, datetime.datetime.now().year, form
        )

        self.assertEqual(BudgetItem.objects.all().count(), 12)
        self.assertTrue(
            all([item.category == category for item in BudgetItem.objects.all()])
        )
        self.assertEqual(Rollover.objects.all().count(), 1)
        self.assertEqual(Rollover.objects.all()[0].category, category)


class TestExpenseSource(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="source@test.com",
            username="source-user",
            password="testpass123",
        )
        cls.yearly_budget = YearlyBudget.objects.create(
            user=cls.user,
            date=datetime.date(2026, 1, 1),
        )
        cls.january = MonthlyBudget.objects.get(
            user=cls.user,
            date=datetime.date(2026, 1, 1),
        )
        cls.february = MonthlyBudget.objects.get(
            user=cls.user,
            date=datetime.date(2026, 2, 1),
        )

    def test_source_name_is_unique_per_user(self):
        ExpenseSource.objects.create(user=self.user, name="Bank statement")

        with self.assertRaises(IntegrityError):
            ExpenseSource.objects.create(user=self.user, name="Bank statement")

    def test_check_is_unique_per_month_and_source(self):
        source = ExpenseSource.objects.create(user=self.user, name="Bank statement")
        ExpenseSourceCheck.objects.create(
            monthly_budget=self.january,
            expense_source=source,
        )

        with self.assertRaises(IntegrityError):
            ExpenseSourceCheck.objects.create(
                monthly_budget=self.january,
                expense_source=source,
            )

    def test_same_source_has_independent_monthly_state(self):
        source = ExpenseSource.objects.create(user=self.user, name="Bank statement")
        january_check = ExpenseSourceCheck.objects.create(
            monthly_budget=self.january,
            expense_source=source,
            is_checked=True,
        )
        february_check = ExpenseSourceCheck.objects.create(
            monthly_budget=self.february,
            expense_source=source,
        )

        self.assertTrue(january_check.is_checked)
        self.assertFalse(february_check.is_checked)

    def test_source_can_be_included_in_nonconsecutive_months(self):
        source = ExpenseSource.objects.create(user=self.user, name="Bank statement")
        january_membership = ExpenseSourceMonth.objects.create(
            expense_source=source,
            monthly_budget=self.january,
        )
        march = MonthlyBudget.objects.get(
            user=self.user,
            date=datetime.date(2026, 3, 1),
        )
        march_membership = ExpenseSourceMonth.objects.create(
            expense_source=source,
            monthly_budget=march,
        )

        self.assertEqual(january_membership.monthly_budget, self.january)
        self.assertEqual(march_membership.monthly_budget, march)
        self.assertFalse(
            ExpenseSourceMonth.objects.filter(
                expense_source=source,
                monthly_budget=self.february,
            ).exists()
        )

    def test_monthly_notes_are_independent(self):
        source = ExpenseSource.objects.create(user=self.user, name="Bank statement")
        january_check = ExpenseSourceCheck.objects.create(
            monthly_budget=self.january,
            expense_source=source,
            notes="Waiting for a pending charge",
        )
        february_check = ExpenseSourceCheck.objects.create(
            monthly_budget=self.february,
            expense_source=source,
            notes="",
        )

        self.assertEqual(january_check.notes, "Waiting for a pending charge")
        self.assertEqual(february_check.notes, "")
