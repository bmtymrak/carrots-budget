from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from purchases.models import RecurringPurchase
from .factories import RecurringPurchaseFactory, CategoryFactory


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
            name="Netflix",
            amount=Decimal("15.99"),
            category=self.category,
            merchant="Netflix Inc.",
            notes="Monthly subscription",
            is_active=True,
        )
        self.assertEqual(recurring.name, "Netflix")
        self.assertEqual(recurring.amount, Decimal("15.99"))
        self.assertEqual(recurring.category, self.category)
        self.assertEqual(recurring.merchant, "Netflix Inc.")
        self.assertTrue(recurring.is_active)

    def test_recurring_purchase_str(self):
        recurring = RecurringPurchaseFactory(
            user=self.user,
            name="Spotify",
            category=self.category
        )
        self.assertEqual(str(recurring), f"Spotify ({self.category.name})")

    def test_recurring_purchase_default_is_active(self):
        recurring = RecurringPurchase.objects.create(
            user=self.user,
            name="Test",
            amount=Decimal("10.00"),
            category=self.category,
        )
        self.assertTrue(recurring.is_active)

    def test_recurring_purchase_ordering(self):
        RecurringPurchaseFactory(user=self.user, name="Zebra", category=self.category)
        RecurringPurchaseFactory(user=self.user, name="Alpha", category=self.category)
        RecurringPurchaseFactory(user=self.user, name="Middle", category=self.category)

        purchases = list(RecurringPurchase.objects.filter(user=self.user))
        names = [p.name for p in purchases]
        self.assertEqual(names, ["Alpha", "Middle", "Zebra"])
