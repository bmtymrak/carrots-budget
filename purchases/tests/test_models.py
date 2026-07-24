from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from purchases.models import RecurringIncome, RecurringPurchase
from .factories import (
    CategoryFactory,
    RecurringIncomeFactory,
    RecurringPurchaseFactory,
)


User = get_user_model()


class RecurringPurchaseModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.category = CategoryFactory(user=self.user)

    def test_recurring_purchase_creation(self):
        recurring = RecurringPurchase.objects.create(
            user=self.user,
            item="Netflix",
            amount=Decimal("15.99"),
            category=self.category,
            source="Netflix Inc.",
            location="Online",
            notes="Monthly subscription",
            is_active=True,
        )
        self.assertEqual(recurring.item, "Netflix")
        self.assertEqual(recurring.amount, Decimal("15.99"))
        self.assertEqual(recurring.category, self.category)
        self.assertEqual(recurring.source, "Netflix Inc.")
        self.assertEqual(recurring.location, "Online")
        self.assertTrue(recurring.is_active)

    def test_recurring_purchase_str(self):
        recurring = RecurringPurchaseFactory(
            user=self.user,
            item="Spotify",
            category=self.category
        )
        self.assertEqual(str(recurring), f"Spotify ({self.category.name})")

    def test_recurring_purchase_default_is_active(self):
        recurring = RecurringPurchase.objects.create(
            user=self.user,
            item="Test",
            amount=Decimal("10.00"),
            category=self.category,
        )
        self.assertTrue(recurring.is_active)

    def test_recurring_purchase_ordering(self):
        RecurringPurchaseFactory(user=self.user, item="Zebra", category=self.category)
        RecurringPurchaseFactory(user=self.user, item="Alpha", category=self.category)
        RecurringPurchaseFactory(user=self.user, item="Middle", category=self.category)

        purchases = list(RecurringPurchase.objects.filter(user=self.user))
        items = [p.item for p in purchases]
        self.assertEqual(items, ["Alpha", "Middle", "Zebra"])


class RecurringIncomeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="incomeuser",
            email="income@example.com",
            ******,
        )
        self.category = CategoryFactory(user=self.user)

    def test_recurring_income_creation_and_string_representation(self):
        recurring = RecurringIncome.objects.create(
            user=self.user,
            amount=Decimal("5000.00"),
            source="Employer",
            payer="Payroll",
            category=self.category,
        )

        self.assertEqual(str(recurring), f"Employer ({self.category.name})")
        self.assertTrue(recurring.is_active)

    def test_recurring_income_ordering(self):
        RecurringIncomeFactory(user=self.user, category=self.category, source="Zebra")
        RecurringIncomeFactory(user=self.user, category=self.category, source="Alpha")

        self.assertEqual(
            list(
                RecurringIncome.objects.filter(user=self.user).values_list(
                    "source", flat=True
                )
            ),
            ["Alpha", "Zebra"],
        )
