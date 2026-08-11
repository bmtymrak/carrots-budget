import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from purchases.models import Purchase, Receipt, RecurringPurchase
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


class ReceiptModelTests(TestCase):
    def test_purchase_cannot_reference_another_users_receipt(self):
        owner = User.objects.create_user(
            username="receipt-owner", email="owner@example.com", password="testpass123"
        )
        other_user = User.objects.create_user(
            username="receipt-other", email="other@example.com", password="testpass123"
        )
        receipt = Receipt.objects.create(user=owner, date=datetime.date(2024, 1, 1))
        purchase = Purchase(
            user=other_user,
            receipt=receipt,
            item="Cross-user purchase",
            date=datetime.date(2024, 1, 1),
        )

        with self.assertRaises(ValidationError):
            purchase.save()
