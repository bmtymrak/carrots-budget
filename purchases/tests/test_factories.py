from django.test import TestCase

from .factories import (
    IncomeFactory,
    PurchaseFactory,
    RecurringPurchaseFactory,
    UserFactory,
)


class TransactionFactoryOwnershipTests(TestCase):
    def test_nested_categories_follow_explicit_user(self):
        user = UserFactory()

        purchase = PurchaseFactory(user=user)
        income = IncomeFactory(user=user)
        recurring_purchase = RecurringPurchaseFactory(user=user)

        self.assertEqual(purchase.category.user, user)
        self.assertEqual(income.category.user, user)
        self.assertEqual(recurring_purchase.category.user, user)
        self.assertIsNone(purchase.subcategory)
