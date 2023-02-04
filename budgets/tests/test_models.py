import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from budgets.models import YearlyBudget, MonthlyBudget, BudgetItem, Rollover
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
