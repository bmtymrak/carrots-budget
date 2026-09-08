import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from budgets.models import YearlyBudget
from purchases.models import Category, Income, Purchase, RecurringPurchase


User = get_user_model()


class TransactionEndpointSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="owner", email="owner@example.com"
        )
        cls.other_user = User.objects.create_user(
            username="other", email="other@example.com"
        )
        cls.other_category = Category.objects.create(
            user=cls.other_user, name="Other category"
        )
        cls.other_income = Income.objects.create(
            user=cls.other_user,
            amount="100.00",
            date=datetime.date(2024, 1, 1),
        )
        cls.other_purchase = Purchase.objects.create(
            user=cls.other_user,
            item="Private purchase",
            amount="20.00",
            date=datetime.date(2024, 1, 1),
            category=cls.other_category,
        )
        cls.other_recurring = RecurringPurchase.objects.create(
            user=cls.other_user,
            item="Private recurring purchase",
            amount="25.00",
            category=cls.other_category,
        )
        YearlyBudget.objects.create(
            user=cls.other_user, date=datetime.date(2024, 1, 1)
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_foreign_transactions_are_not_accessible(self):
        urls = [
            reverse("purchase_edit_htmx", args=[self.other_purchase.pk]),
            reverse("purchase_delete_htmx", args=[self.other_purchase.pk]),
            reverse("income_edit_htmx", args=[self.other_income.pk]),
            reverse("income_delete_htmx", args=[self.other_income.pk]),
            reverse("recurring_purchase_edit", args=[self.other_recurring.pk]),
            reverse("recurring_purchase_delete", args=[self.other_recurring.pk]),
            reverse("recurring_purchase_add_to_month", args=[2024, 1]),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_missing_and_external_next_urls_use_safe_defaults(self):
        response = self.client.get(reverse("income_create"))
        external_response = self.client.get(
            reverse("recurring_purchase_list"),
            {"next": "https://example.org/leave"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], reverse("yearly_list"))
        self.assertEqual(external_response.status_code, 200)
        self.assertEqual(external_response.context["next"], reverse("yearly_list"))
