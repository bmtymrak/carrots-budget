import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from budgets.models import BudgetItem, YearlyBudget
from budgets.services import BudgetService
from purchases.models import Category, Income, Purchase


User = get_user_model()


class QueryGrowthTests(TestCase):
    year = 2024

    def _create_budget_data(self, label, category_count):
        user = User.objects.create_user(
            username=f"{label}-user", email=f"{label}@example.com"
        )
        yearly_budget = YearlyBudget.objects.create(
            user=user, date=datetime.date(self.year, 1, 1)
        )
        january = yearly_budget.monthly_budgets.get(date=datetime.date(self.year, 1, 1))
        categories = Category.objects.bulk_create(
            [
                Category(user=user, name=f"{label} category {index}")
                for index in range(category_count)
            ]
        )
        BudgetItem.objects.bulk_create(
            [
                BudgetItem(
                    user=user,
                    category=category,
                    amount=Decimal("100.00"),
                    monthly_budget=january,
                    yearly_budget=yearly_budget,
                    savings=False,
                )
                for category in categories
            ]
        )
        Purchase.objects.bulk_create(
            [
                Purchase(
                    user=user,
                    category=category,
                    item=f"Purchase {index}",
                    amount=Decimal("10.00"),
                    date=datetime.date(self.year, 1, 15),
                )
                for index, category in enumerate(categories)
            ]
        )
        Income.objects.bulk_create(
            [
                Income(
                    user=user,
                    category=category,
                    amount=Decimal("5.00"),
                    date=datetime.date(self.year, 1, 15),
                )
                for category in categories
            ]
        )
        return user, january

    def _monthly_query_count(self, user, monthly_budget):
        with CaptureQueriesContext(connection) as queries:
            context = BudgetService().get_monthly_budget_context(
                user, self.year, 1, monthly_budget
            )
            list(context["purchases"])
            list(context["incomes"])
        return len(queries)

    def _yearly_query_count(self, user):
        with CaptureQueriesContext(connection) as queries:
            context = BudgetService().get_yearly_budget_context(user, self.year, 6)
            list(context["purchases_uncategorized"])
            list(context["incomes"])
        return len(queries)

    def test_budget_query_counts_do_not_grow_with_categories(self):
        small_user, small_month = self._create_budget_data("small", 1)
        large_user, large_month = self._create_budget_data("large", 30)

        small_monthly_queries = self._monthly_query_count(small_user, small_month)
        large_monthly_queries = self._monthly_query_count(large_user, large_month)
        small_yearly_queries = self._yearly_query_count(small_user)
        large_yearly_queries = self._yearly_query_count(large_user)

        self.assertEqual(small_monthly_queries, large_monthly_queries)
        self.assertLessEqual(small_monthly_queries, 10)
        self.assertEqual(small_yearly_queries, large_yearly_queries)
        self.assertLessEqual(small_yearly_queries, 10)

    def test_purchase_pagination_query_count_does_not_grow_with_rows(self):
        small_user = User.objects.create_user(
            username="small-list", email="small-list@example.com"
        )
        large_user = User.objects.create_user(
            username="large-list", email="large-list@example.com"
        )
        Purchase.objects.create(
            user=small_user, item="Only row", date=datetime.date(self.year, 1, 1)
        )
        Purchase.objects.bulk_create(
            [
                Purchase(
                    user=large_user,
                    item=f"Row {index}",
                    date=datetime.date(self.year, 1, 1),
                )
                for index in range(150)
            ]
        )
        small_client = Client()
        large_client = Client()
        small_client.force_login(small_user)
        large_client.force_login(large_user)

        with CaptureQueriesContext(connection) as small_queries:
            small_client.get(reverse("purchase_list"))
        with CaptureQueriesContext(connection) as large_queries:
            large_client.get(reverse("purchase_list"))

        self.assertEqual(len(small_queries), len(large_queries))
        self.assertLessEqual(len(small_queries), 6)
