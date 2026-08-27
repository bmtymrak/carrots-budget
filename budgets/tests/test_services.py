from decimal import Decimal

from django.test import SimpleTestCase

from budgets.services import BudgetService


class BudgetServiceUsagePercentTests(SimpleTestCase):
    def test_calculates_and_rounds_usage_percent(self):
        self.assertEqual(
            BudgetService._usage_percent(Decimal("25.00"), Decimal("100.00")),
            25,
        )
        self.assertEqual(
            BudgetService._usage_percent(Decimal("125.50"), Decimal("100.00")),
            126,
        )

    def test_zero_budget_is_fully_used_only_when_there_is_activity(self):
        self.assertEqual(BudgetService._usage_percent(Decimal("0"), Decimal("0")), 0)
        self.assertEqual(BudgetService._usage_percent(Decimal("1"), Decimal("0")), 100)
