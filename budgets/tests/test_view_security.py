import datetime
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from budgets.models import BudgetItem, Rollover, YearlyBudget
from purchases.models import Category


User = get_user_model()


class BudgetEndpointSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="owner", email="owner@example.com"
        )
        cls.other_user = User.objects.create_user(
            username="other", email="other@example.com"
        )
        cls.other_yearly_budget = YearlyBudget.objects.create(
            user=cls.other_user, date=datetime.date(2024, 1, 1)
        )
        cls.other_monthly_budget = cls.other_yearly_budget.monthly_budgets.get(
            date=datetime.date(2024, 1, 1)
        )
        cls.other_category = Category.objects.create(
            user=cls.other_user, name="Private category"
        )
        cls.other_budget_item = BudgetItem.objects.create(
            user=cls.other_user,
            yearly_budget=cls.other_yearly_budget,
            monthly_budget=cls.other_monthly_budget,
            category=cls.other_category,
            amount=Decimal("100.00"),
            savings=False,
        )
        cls.other_rollover = Rollover.objects.create(
            user=cls.other_user,
            yearly_budget=cls.other_yearly_budget,
            category=cls.other_category,
            amount=Decimal("50.00"),
        )
        cls.yearly_budget = YearlyBudget.objects.create(
            user=cls.user, date=datetime.date(2025, 1, 1)
        )
        cls.monthly_budget = cls.yearly_budget.monthly_budgets.get(
            date=datetime.date(2025, 1, 1)
        )
        cls.category = Category.objects.create(user=cls.user, name="Food")
        cls.budget_item = BudgetItem.objects.create(
            user=cls.user,
            yearly_budget=cls.yearly_budget,
            monthly_budget=cls.monthly_budget,
            category=cls.category,
            amount=Decimal("100.00"),
            savings=False,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_foreign_budget_objects_are_not_accessible(self):
        urls = [
            reverse("yearly_detail", args=[2024]),
            reverse("budget_item_detail", args=[2024, 1, self.other_category.name]),
            reverse("budget_item_delete", args=[2024, 1, self.other_category.name]),
            reverse("budgetitem_edit_htmx", args=[2024, 1, self.other_category.name]),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_rollover_update_cannot_modify_another_users_rollover(self):
        response = self.client.post(
            reverse("rollover_update"),
            data=json.dumps(
                {
                    "amount": "999.00",
                    "category": self.other_category.name,
                    "year": 2024,
                }
            ),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 404)
        self.other_rollover.refresh_from_db()
        self.assertEqual(self.other_rollover.amount, Decimal("50.00"))

    def test_rollover_update_rejects_bad_requests(self):
        url = reverse("rollover_update")
        cases = [
            ({}, {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}),
            ("not json", {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}),
            (
                {"amount": "NaN", "category": "Anything", "year": 2024},
                {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
            ),
            (
                {"amount": "1.001", "category": "Anything", "year": 2024},
                {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
            ),
            (
                {"amount": "10000000000", "category": "Anything", "year": 2024},
                {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
            ),
            (
                {"amount": "1.00", "category": "Anything", "year": 10000},
                {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
            ),
            ({"amount": "1.00", "category": "Anything", "year": 2024}, {}),
        ]

        for data, headers in cases:
            with self.subTest(data=data, headers=headers):
                response = self.client.post(
                    url,
                    data=json.dumps(data) if not isinstance(data, str) else data,
                    content_type="application/json",
                    **headers,
                )
                self.assertEqual(response.status_code, 400)

        self.assertEqual(self.client.get(url).status_code, 405)

    def test_budget_item_create_without_next_uses_yearly_detail(self):
        response = self.client.get(reverse("budgetitem_create_htmx", args=[2025]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], reverse("yearly_detail", args=[2025]))

    def test_budget_item_modals_use_safe_default_return_urls(self):
        cases = [
            (
                reverse("budgetitem_edit_htmx", args=[2025, 1, self.category.name]),
                reverse("monthly_detail", args=[2025, 1]),
            ),
            (
                reverse("budgetitem_bulk_edit_htmx", args=[2025, self.category.name]),
                reverse("yearly_detail", args=[2025]),
            ),
            (
                reverse("budget_item_delete_htmx", args=[2025, self.category.name]),
                reverse("yearly_detail", args=[2025]),
            ),
        ]

        for url, expected_next in cases:
            with self.subTest(url=url):
                response = self.client.get(url, {"next": "https://example.org/leave"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["next"], expected_next)
