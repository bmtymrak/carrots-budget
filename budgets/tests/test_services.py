import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from budgets.services import BudgetService
from budgets.models import BudgetItem, MonthlyBudget, Rollover, YearlyBudget
from purchases.models import Category, Income, Purchase


User = get_user_model()


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


class BudgetServiceMonthlyContextTests(TestCase):
    year = 2024
    month = 1
    month_start = datetime.date(year, month, 1)

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="service-user@example.com",
            username="service-user",
            password="testpass123",
        )
        cls.other_user = User.objects.create_user(
            email="other-service-user@example.com",
            username="other-service-user",
            password="testpass123",
        )

        cls.yearly_budget = YearlyBudget.objects.create(
            user=cls.user,
            date=datetime.date(cls.year, 1, 1),
        )
        cls.monthly_budget = MonthlyBudget.objects.get(
            user=cls.user,
            yearly_budget=cls.yearly_budget,
            date=cls.month_start,
        )
        other_yearly_budget = YearlyBudget.objects.create(
            user=cls.other_user,
            date=datetime.date(cls.year, 1, 1),
        )
        other_monthly_budget = MonthlyBudget.objects.get(
            user=cls.other_user,
            yearly_budget=other_yearly_budget,
            date=cls.month_start,
        )

        cls.spending_category = Category.objects.create(
            user=cls.user,
            name="Spending",
        )
        cls.savings_category = Category.objects.create(
            user=cls.user,
            name="Savings",
        )
        other_category = Category.objects.create(
            user=cls.other_user,
            name="Other user",
        )

        BudgetItem.objects.create(
            user=cls.user,
            category=cls.spending_category,
            amount=Decimal("500.00"),
            monthly_budget=cls.monthly_budget,
            yearly_budget=cls.yearly_budget,
            savings=False,
        )
        BudgetItem.objects.create(
            user=cls.user,
            category=cls.savings_category,
            amount=Decimal("200.00"),
            monthly_budget=cls.monthly_budget,
            yearly_budget=cls.yearly_budget,
            savings=True,
        )

        Purchase.objects.create(
            user=cls.user,
            category=cls.spending_category,
            date=datetime.date(cls.year, 1, 15),
            amount=Decimal("125.00"),
            item="January spending",
        )
        Purchase.objects.create(
            user=cls.user,
            category=cls.savings_category,
            date=datetime.date(cls.year, 1, 20),
            amount=Decimal("30.00"),
            item="January saving",
        )
        Purchase.objects.create(
            user=cls.user,
            category=None,
            date=datetime.date(cls.year, 1, 25),
            amount=Decimal("20.00"),
            item="Uncategorized purchase",
        )
        Purchase.objects.create(
            user=cls.user,
            category=cls.spending_category,
            date=datetime.date(cls.year, 2, 1),
            amount=Decimal("900.00"),
            item="Next month spending",
        )
        Purchase.objects.create(
            user=cls.other_user,
            category=other_category,
            date=datetime.date(cls.year, 1, 15),
            amount=Decimal("700.00"),
            item="Other user spending",
        )

        Income.objects.create(
            user=cls.user,
            category=cls.spending_category,
            date=datetime.date(cls.year, 1, 10),
            amount=Decimal("25.00"),
            source="Spending adjustment",
        )
        Income.objects.create(
            user=cls.user,
            category=cls.savings_category,
            date=datetime.date(cls.year, 1, 11),
            amount=Decimal("50.00"),
            source="Savings contribution",
        )
        Income.objects.create(
            user=cls.user,
            category=None,
            date=datetime.date(cls.year, 1, 12),
            amount=Decimal("1000.00"),
            source="Uncategorized income",
        )
        Income.objects.create(
            user=cls.user,
            category=None,
            date=datetime.date(cls.year, 2, 1),
            amount=Decimal("900.00"),
            source="Next month income",
        )
        Income.objects.create(
            user=cls.other_user,
            category=None,
            date=datetime.date(cls.year, 1, 12),
            amount=Decimal("800.00"),
            source="Other user income",
        )

    def test_monthly_context_calculates_spending_savings_and_totals(self):
        context = BudgetService().get_monthly_budget_context(
            user=self.user,
            year=self.year,
            month=self.month,
            monthly_budget=self.monthly_budget,
        )

        spending_item = context["budget_items"][0]
        self.assertEqual(spending_item.category, self.spending_category)
        self.assertEqual(spending_item.amount, Decimal("500.00"))
        self.assertEqual(spending_item.spent, Decimal("125.00"))
        self.assertEqual(spending_item.income, Decimal("25.00"))
        self.assertEqual(spending_item.diff, Decimal("400.00"))

        savings_item = context["savings_items"][0]
        self.assertEqual(savings_item.category, self.savings_category)
        self.assertEqual(savings_item.amount, Decimal("200.00"))
        self.assertEqual(savings_item.saved, Decimal("80.00"))
        self.assertEqual(savings_item.income, Decimal("50.00"))
        self.assertEqual(savings_item.diff, Decimal("170.00"))

        self.assertEqual(context["total_spending_budgeted"]["amount"], Decimal("500.00"))
        self.assertEqual(context["total_spending_spent"]["amount"], Decimal("145.00"))
        self.assertEqual(context["total_spending_remaining"]["amount"], Decimal("380.00"))
        self.assertEqual(context["total_savings_budgeted"]["amount"], Decimal("200.00"))
        self.assertEqual(context["total_saved"]["amount"], Decimal("80.00"))
        self.assertEqual(context["total_savings_remaining"]["amount"], Decimal("170.00"))
        self.assertEqual(context["total_budgeted"], Decimal("700.00"))
        self.assertEqual(context["total_spent_saved"], Decimal("225.00"))
        self.assertEqual(context["total_remaining"], Decimal("550.00"))
        self.assertEqual(context["total_income"]["amount"], Decimal("1000.00"))
        self.assertEqual(context["free_income"], Decimal("775.00"))
        self.assertEqual(
            context["uncategorized_purchases"],
            {
                "amount": Decimal("20.00"),
                "remaining": Decimal("-20.00"),
                "budgeted": 0,
            },
        )

        self.assertCountEqual(
            context["purchases"].values_list("item", flat=True),
            ["January spending", "January saving", "Uncategorized purchase"],
        )
        self.assertCountEqual(
            context["incomes"].values_list("source", flat=True),
            ["Spending adjustment", "Savings contribution", "Uncategorized income"],
        )


class BudgetServiceYearlyContextTests(TestCase):
    year = 2024
    ytd_month = 2

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="yearly-service-user@example.com",
            username="yearly-service-user",
            password="testpass123",
        )
        cls.yearly_budget = YearlyBudget.objects.create(
            user=cls.user,
            date=datetime.date(cls.year, 1, 1),
        )
        monthly_budgets = {
            month: MonthlyBudget.objects.get(
                user=cls.user,
                yearly_budget=cls.yearly_budget,
                date=datetime.date(cls.year, month, 1),
            )
            for month in (1, 2, 3)
        }
        cls.category = Category.objects.create(user=cls.user, name="Annual spending")

        for month in (1, 2, 3):
            BudgetItem.objects.create(
                user=cls.user,
                category=cls.category,
                amount=Decimal("100.00"),
                monthly_budget=monthly_budgets[month],
                yearly_budget=cls.yearly_budget,
                savings=False,
            )

        previous_year_budget = YearlyBudget.objects.create(
            user=cls.user,
            date=datetime.date(cls.year - 1, 1, 1),
        )
        Rollover.objects.create(
            user=cls.user,
            category=cls.category,
            yearly_budget=previous_year_budget,
            amount=Decimal("30.00"),
        )
        Rollover.objects.create(
            user=cls.user,
            category=cls.category,
            yearly_budget=cls.yearly_budget,
            amount=Decimal("50.00"),
        )

        Purchase.objects.create(
            user=cls.user,
            category=cls.category,
            date=datetime.date(cls.year, 1, 15),
            amount=Decimal("10.00"),
            item="January purchase",
        )
        Purchase.objects.create(
            user=cls.user,
            category=cls.category,
            date=datetime.date(cls.year, 2, 29),
            amount=Decimal("20.00"),
            item="YTD boundary purchase",
        )
        Purchase.objects.create(
            user=cls.user,
            category=cls.category,
            date=datetime.date(cls.year, 3, 1),
            amount=Decimal("999.00"),
            item="After YTD boundary purchase",
        )
        Purchase.objects.create(
            user=cls.user,
            category=cls.category,
            date=datetime.date(cls.year + 1, 1, 1),
            amount=Decimal("500.00"),
            item="Next year purchase",
        )

        Income.objects.create(
            user=cls.user,
            category=cls.category,
            date=datetime.date(cls.year, 1, 10),
            amount=Decimal("3.00"),
            source="January income",
        )
        Income.objects.create(
            user=cls.user,
            category=cls.category,
            date=datetime.date(cls.year, 2, 29),
            amount=Decimal("4.00"),
            source="YTD boundary income",
        )
        Income.objects.create(
            user=cls.user,
            category=cls.category,
            date=datetime.date(cls.year, 3, 1),
            amount=Decimal("5.00"),
            source="After YTD boundary income",
        )

    def test_yearly_context_respects_ytd_boundary_and_rollovers(self):
        context = BudgetService().get_yearly_budget_context(
            user=self.user,
            year=self.year,
            ytd_month=self.ytd_month,
        )

        item = context["budget_items_combined"][0]
        self.assertEqual(item["category"], self.category.pk)
        self.assertEqual(item["amount_total"], Decimal("300.00"))
        self.assertEqual(item["spent"], Decimal("1029.00"))
        self.assertEqual(item["diff"], Decimal("-687.00"))
        self.assertEqual(item["amount_total_ytd"], Decimal("200.00"))
        self.assertEqual(item["spent_ytd"], Decimal("30.00"))
        self.assertEqual(item["diff_ytd"], Decimal("177.00"))
        self.assertEqual(item["rollover_current"], Decimal("30.00"))
        self.assertEqual(item["rollover_next"], Decimal("50.00"))

        self.assertEqual(context["total_budgeted"], Decimal("300.00"))
        self.assertEqual(context["total_spent_saved"], Decimal("1029.00"))
        self.assertEqual(context["total_remaining"], Decimal("-687.00"))
        self.assertEqual(context["total_budgeted_ytd"], Decimal("200.00"))
        self.assertEqual(context["total_spent_saved_ytd"], Decimal("30.00"))
        self.assertEqual(context["total_remaining_ytd"], Decimal("177.00"))
        self.assertEqual(context["total_income"]["amount"], Decimal("12.00"))
        self.assertEqual(context["total_income_ytd"]["amount"], Decimal("7.00"))
        self.assertEqual(context["ytd_month_name"], "February")
