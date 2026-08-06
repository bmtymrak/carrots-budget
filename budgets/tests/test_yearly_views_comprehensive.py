from decimal import Decimal
import datetime
import factory
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from budgets.models import YearlyBudget, MonthlyBudget, BudgetItem, Rollover
from purchases.models import Purchase, Income
from budgets.tests.factories import (
    YearlyBudgetFactory,
    MonthlyBudgetFactory,
    BudgetItemFactory,
    RolloverFactory,
)
from purchases.tests.factories import (
    CategoryFactory,
    PurchaseFactory,
    IncomeFactory,
)

User = get_user_model()

class TestYearlyBudgetDetailViewComprehensive(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="test@example.com", username="testuser", password="password123"
        )
        cls.year = datetime.date.today().year
        cls.yearly_budget = YearlyBudgetFactory(user=cls.user, date=datetime.date(cls.year, 1, 1))

        # Create 12 monthly budgets
        cls.monthly_budgets = []
        for month in range(1, 13):
            cls.monthly_budgets.append(
                MonthlyBudgetFactory(
                    user=cls.user,
                    yearly_budget=cls.yearly_budget,
                    date=datetime.date(cls.year, month, 1)
                )
            )

        # Categories
        cls.cat_food = CategoryFactory(user=cls.user, name="Food")
        cls.cat_vacation = CategoryFactory(user=cls.user, name="Vacation")

    def setUp(self):
        self.client.login(email="test@example.com", password="password123")

    def test_basic_context_structure(self):
        """Verify that the view returns 200 and has the expected context keys."""
        response = self.client.get(reverse("yearly_detail", kwargs={"year": self.year}))
        self.assertEqual(response.status_code, 200)
        
        expected_keys = [
            "budget_items_combined",
            "savings_items_combined",
            "total_budgeted",
            "total_spent_saved",
            "total_remaining",
            "months",
        ]
        for key in expected_keys:
            self.assertIn(key, response.context)

    def test_data_calculation_standard_scenario(self):
        """
        Verify calculations for a standard scenario with spending, savings, income, and rollover.
        """
        # Setup Budget Items
        # Food: $500/month * 12 = $6000
        for mb in self.monthly_budgets:
            BudgetItemFactory(
                user=self.user,
                category=self.cat_food,
                monthly_budget=mb,
                amount=Decimal("500.00"),
                savings=False
            )
        
        # Vacation: $200/month * 12 = $2400 (Savings)
        for mb in self.monthly_budgets:
            BudgetItemFactory(
                user=self.user,
                category=self.cat_vacation,
                monthly_budget=mb,
                amount=Decimal("200.00"),
                savings=True
            )

        # Setup Transactions
        # Purchase in Jan for Food: $100
        PurchaseFactory(
            user=self.user,
            category=self.cat_food,
            date=datetime.date(self.year, 1, 15),
            amount=Decimal("100.00")
        )

        # Purchase in Jan for Vacation: $50 (Counts as 'saved' in this app logic)
        PurchaseFactory(
            user=self.user,
            category=self.cat_vacation,
            date=datetime.date(self.year, 1, 15),
            amount=Decimal("50.00")
        )

        prev_year_budget = YearlyBudgetFactory(user=self.user, date=datetime.date(self.year - 1, 1, 1))
        # Rollover from previous year for Food: $50
        RolloverFactory(
            user=self.user,
            yearly_budget=prev_year_budget,
            category=self.cat_food,
            amount=Decimal("50.00")
        )

        # Execute
        response = self.client.get(reverse("yearly_detail", kwargs={"year": self.year}))
        context = response.context

        # Assertions for Food (Spending)
        # Find the food item in combined list
        food_item = next(item for item in context["budget_items_combined"] if item["category__name"] == "Food")
        self.assertEqual(food_item["amount_total"], Decimal("6000.00"))
        self.assertEqual(food_item["spent"], Decimal("100.00"))
        # diff (remaining) -> amount_total - spent + income + rollover
        # 6000 - 100 + 0 + 50 = 5950
        self.assertEqual(food_item["diff"], Decimal("5950.00"))

        # Assertions for Vacation (Savings)
        vacation_item = next(item for item in context["savings_items_combined"] if item["category__name"] == "Vacation")

        self.assertEqual(vacation_item["amount_total"], Decimal("2400.00"))
        # saved (purchases + income) -> 50 + 0 = 50
        self.assertEqual(vacation_item["saved"], Decimal("50.00"))
        # diff (remaining) -> amount_total - saved + income
        # 2400 - 50 + 0 = 2350
        self.assertEqual(vacation_item["diff"], Decimal("2350.00"))

    def test_ytd_logic(self):
        """Verify YTD calculations when 'ytd' param is provided."""
        # Setup: $100 budget per month for Food
        for mb in self.monthly_budgets:
            BudgetItemFactory(
                user=self.user,
                category=self.cat_food,
                monthly_budget=mb,
                amount=Decimal("100.00"),
                savings=False
            )
        
        # Purchase in June: $50
        PurchaseFactory(
            user=self.user,
            category=self.cat_food,
            date=datetime.date(self.year, 6, 15),
            amount=Decimal("50.00")
        )
        
        # Purchase in July: $50 (Should NOT be in YTD if we ask for June)
        PurchaseFactory(
            user=self.user,
            category=self.cat_food,
            date=datetime.date(self.year, 7, 15),
            amount=Decimal("50.00")
        )

        # Request YTD for June (month 6)
        response = self.client.get(reverse("yearly_detail", kwargs={"year": self.year}) + "?ytd=6")
        context = response.context
        
        food_item = next(item for item in context["budget_items_combined"] if item["category__name"] == "Food")
        
        # YTD Budget: 6 months * 100 = 600
        self.assertEqual(food_item["amount_total_ytd"], Decimal("600.00"))
        
        # YTD Spent: Only June purchase = 50
        self.assertEqual(food_item["spent_ytd"], Decimal("50.00"))
        
        # YTD Diff: 600 - 50 = 550
        self.assertEqual(food_item["diff_ytd"], Decimal("550.00"))

    def test_empty_state(self):
        """Verify view handles a year with no data gracefully."""
        empty_year = self.year - 5
        YearlyBudgetFactory(user=self.user, date=datetime.date(empty_year, 1, 1))
        
        response = self.client.get(reverse("yearly_detail", kwargs={"year": empty_year}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["budget_items_combined"]), 0)
        self.assertEqual(response.context["total_budgeted"], 0)

    def test_uncategorized_purchases(self):
        """Verify uncategorized purchases are handled."""
        PurchaseFactory(
            user=self.user,
            category=None,
            date=datetime.date(self.year, 1, 15),
            amount=Decimal("99.99")
        )
        
        response = self.client.get(reverse("yearly_detail", kwargs={"year": self.year}))
        self.assertEqual(response.status_code, 200)
        
    def test_heavy_data_load(self):
        """
        Demonstrate how to seed a lot of data:
        - 5 Categories
        - Budget items for all 12 months for each category
        - 3 Purchases per month for each category
        """
        # 1. Create 5 Categories
        categories = CategoryFactory.create_batch(5, user=self.user)

        # 2. Setup Budget Items and Purchases
        # We'll use deterministic values to make assertions easy
        # Budget: $1000/month
        # Purchases: $10, $20, $30 per month (Total $60/month)
        
        expected_total_budgeted = Decimal("0.00")
        expected_total_spent = Decimal("0.00")

        for i, category in enumerate(categories):
            # Create Budget Items for all 12 months
            for mb in self.monthly_budgets:
                BudgetItemFactory(
                    user=self.user,
                    category=category,
                    monthly_budget=mb,
                    amount=Decimal(str(1000.00 + mb.date.month + i)),
                    savings=False
                )
                expected_total_budgeted += Decimal(str(1000.00 + mb.date.month + i))

                # Create 3 purchases for this month
                p1_amount = Decimal(str(10.00 + mb.date.month + i))
                p2_amount = Decimal(str(20.00 + mb.date.month + i))
                p3_amount = Decimal(str(30.00 + mb.date.month + i))

                PurchaseFactory.create_batch(
                    3,
                    user=self.user,
                    category=category,
                    date=mb.date + datetime.timedelta(days=1), # Set date to 2nd of month
                    amount=factory.Iterator([p1_amount, p2_amount, p3_amount])
                )
                expected_total_spent += (p1_amount + p2_amount + p3_amount)

        # Execute
        response = self.client.get(reverse("yearly_detail", kwargs={"year": self.year}))
        context = response.context

        # Assertions
        # Check Grand Totals
        self.assertEqual(context["total_budgeted"], expected_total_budgeted)
        self.assertEqual(context["total_spent_saved"], expected_total_spent)
        
        # Check individual category data in the combined list
        # We expect 5 categories + the 2 from setUpTestData = 7 total
        # (Actually setUpTestData creates 'Food' and 'Vacation', so 7 total)
        # Let's just check one of our new categories
        test_cat = categories[0]
        cat_item = next(item for item in context["budget_items_combined"] if item["category__name"] == test_cat.name)
        
        # Budgeted: Sum of (1000.00 + month) for months 1-12  
        expected_cat_budgeted = Decimal("0.00")
        expected_cat_spent = Decimal("0.00")
        for month in range(1, 13):
            # We are verifying categories[0], so don't need to add category index (like we did above)
            expected_cat_budgeted += Decimal(str(1000.00 + month))
            
            p1 = Decimal(str(10.00 + month))
            p2 = Decimal(str(20.00 + month))
            p3 = Decimal(str(30.00 + month))
            expected_cat_spent += (p1 + p2 + p3)

        self.assertEqual(cat_item["amount_total"], expected_cat_budgeted)
        self.assertEqual(cat_item["spent"], expected_cat_spent)

    def test_using_fixtures(self):
        """
        Demonstrate how to use fixtures to load data.
        Note: We need to specify 'fixtures' in the class or use 'call_command' to load them.
        For this specific test method, we'll use call_command to avoid affecting other tests
        if we were to set it on the class level (though class level is more common).
        """
        from django.core.management import call_command
        from purchases.models import Category
        
        # Load the fixture
        call_command('loaddata', 'test_data.json', verbosity=0)
        
        # Verify data is loaded
        fixture_user = User.objects.get(email="fixture@example.com")
        self.assertEqual(fixture_user.username, "fixture_user")
        
        categories = Category.objects.filter(user=fixture_user)
        self.assertEqual(categories.count(), 2)
        self.assertTrue(categories.filter(name="Fixture Category 1").exists())
        
        yb = YearlyBudgetFactory(user=fixture_user, date=datetime.date(self.year, 1, 1))
        
        # Login as the fixture user
        fixture_user.set_password("newpassword123")
        fixture_user.save()
        
        self.client.login(email="fixture@example.com", password="newpassword123")
        response = self.client.get(reverse("yearly_detail", kwargs={"year": self.year}))
        self.assertEqual(response.status_code, 200)


class TestYearlyBudgetListView(TestCase):
    """Tests for the Yearly Budget List View with summary metrics."""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="test@example.com", username="testuser", password="password123"
        )
        cls.year = datetime.date.today().year
        cls.yearly_budget = YearlyBudgetFactory(user=cls.user, date=datetime.date(cls.year, 1, 1))

        # Create 12 monthly budgets
        cls.monthly_budgets = []
        for month in range(1, 13):
            cls.monthly_budgets.append(
                MonthlyBudgetFactory(
                    user=cls.user,
                    yearly_budget=cls.yearly_budget,
                    date=datetime.date(cls.year, month, 1)
                )
            )

        # Categories
        cls.cat_food = CategoryFactory(user=cls.user, name="Food")
        cls.cat_vacation = CategoryFactory(user=cls.user, name="Vacation")

    def setUp(self):
        self.client.login(email="test@example.com", password="password123")

    def test_yearly_list_view_loads_successfully(self):
        """Verify that the yearly budget list view returns 200."""
        response = self.client.get(reverse("yearly_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("yearly_budgets", response.context)

    def test_yearly_list_view_has_summary_metrics(self):
        """Verify that each yearly budget in the list has summary metrics."""
        # Create budget items and transactions
        for mb in self.monthly_budgets:
            BudgetItemFactory(
                user=self.user,
                category=self.cat_food,
                monthly_budget=mb,
                yearly_budget=self.yearly_budget,
                amount=Decimal("500.00"),
                savings=False
            )
            BudgetItemFactory(
                user=self.user,
                category=self.cat_vacation,
                monthly_budget=mb,
                yearly_budget=self.yearly_budget,
                amount=Decimal("200.00"),
                savings=True
            )

        # Create a purchase in spending category
        PurchaseFactory(
            user=self.user,
            category=self.cat_food,
            date=datetime.date(self.year, 1, 15),
            amount=Decimal("100.00")
        )

        # Create a purchase in savings category
        PurchaseFactory(
            user=self.user,
            category=self.cat_vacation,
            date=datetime.date(self.year, 2, 15),
            amount=Decimal("50.00")
        )

        # Create income (not assigned to category)
        IncomeFactory(
            user=self.user,
            category=None,
            date=datetime.date(self.year, 1, 15),
            amount=Decimal("5000.00")
        )

        response = self.client.get(reverse("yearly_list"))
        yearly_budgets = response.context["yearly_budgets"]

        # Find our yearly budget in the list
        budget = next((b for b in yearly_budgets if b.date.year == self.year), None)
        self.assertIsNotNone(budget)
        
        # Verify summary metrics exist
        self.assertTrue(hasattr(budget, 'summary'))
        summary = budget.summary

        # Verify the calculated values
        # Total budgeted: 500*12 + 200*12 = 6000 + 2400 = 8400
        self.assertEqual(summary['total_budgeted'], Decimal("8400.00"))
        
        # Total income: 5000 (only non-categorized income)
        self.assertEqual(summary['total_income'], Decimal("5000.00"))
        
        # Total spent: 100 (only in spending categories)
        self.assertEqual(summary['total_spent'], Decimal("100.00"))
        
        # Total saved: 50 (purchases in savings categories)
        self.assertEqual(summary['total_saved'], Decimal("50.00"))
        
        # Total spent + saved: 100 + 50 = 150
        self.assertEqual(summary['total_spent_saved'], Decimal("150.00"))

    def test_yearly_list_view_with_savings_income(self):
        """Verify that income to savings categories is included in total_saved."""
        # Create savings budget item
        for mb in self.monthly_budgets:
            BudgetItemFactory(
                user=self.user,
                category=self.cat_vacation,
                monthly_budget=mb,
                yearly_budget=self.yearly_budget,
                amount=Decimal("200.00"),
                savings=True
            )

        # Create income for savings category
        IncomeFactory(
            user=self.user,
            category=self.cat_vacation,
            date=datetime.date(self.year, 1, 15),
            amount=Decimal("100.00")
        )

        # Create purchase in savings category
        PurchaseFactory(
            user=self.user,
            category=self.cat_vacation,
            date=datetime.date(self.year, 2, 15),
            amount=Decimal("50.00")
        )

        response = self.client.get(reverse("yearly_list"))
        yearly_budgets = response.context["yearly_budgets"]

        budget = next((b for b in yearly_budgets if b.date.year == self.year), None)
        summary = budget.summary

        # Total saved should include both purchase and income: 50 + 100 = 150
        self.assertEqual(summary['total_saved'], Decimal("150.00"))

    def test_yearly_list_view_multiple_years(self):
        """Verify that multiple yearly budgets are displayed with correct summaries."""
        # Create a second year
        year2 = self.year - 1
        yearly_budget2 = YearlyBudgetFactory(user=self.user, date=datetime.date(year2, 1, 1))
        
        monthly_budgets2 = []
        for month in range(1, 13):
            monthly_budgets2.append(
                MonthlyBudgetFactory(
                    user=self.user,
                    yearly_budget=yearly_budget2,
                    date=datetime.date(year2, month, 1)
                )
            )

        # Create budget items for both years with different amounts
        for mb in self.monthly_budgets:
            BudgetItemFactory(
                user=self.user,
                category=self.cat_food,
                monthly_budget=mb,
                yearly_budget=self.yearly_budget,
                amount=Decimal("500.00"),
                savings=False
            )

        for mb in monthly_budgets2:
            BudgetItemFactory(
                user=self.user,
                category=self.cat_food,
                monthly_budget=mb,
                yearly_budget=yearly_budget2,
                amount=Decimal("300.00"),
                savings=False
            )

        response = self.client.get(reverse("yearly_list"))
        yearly_budgets = response.context["yearly_budgets"]

        # Should have 2 yearly budgets
        self.assertEqual(len(yearly_budgets), 2)

        # Find each budget and verify summaries
        budget_current = next((b for b in yearly_budgets if b.date.year == self.year), None)
        budget_previous = next((b for b in yearly_budgets if b.date.year == year2), None)

        self.assertIsNotNone(budget_current)
        self.assertIsNotNone(budget_previous)

        # Current year: 500 * 12 = 6000
        self.assertEqual(budget_current.summary['total_budgeted'], Decimal("6000.00"))

        # Previous year: 300 * 12 = 3600
        self.assertEqual(budget_previous.summary['total_budgeted'], Decimal("3600.00"))

    def test_yearly_list_view_empty_budget(self):
        """Verify that a year with no budget items shows zero values."""
        response = self.client.get(reverse("yearly_list"))
        yearly_budgets = response.context["yearly_budgets"]

        budget = next((b for b in yearly_budgets if b.date.year == self.year), None)
        summary = budget.summary

        # All values should be zero
        self.assertEqual(summary['total_budgeted'], Decimal("0"))
        self.assertEqual(summary['total_income'], Decimal("0"))
        self.assertEqual(summary['total_spent'], Decimal("0"))
        self.assertEqual(summary['total_saved'], Decimal("0"))
        self.assertEqual(summary['total_spent_saved'], Decimal("0"))

