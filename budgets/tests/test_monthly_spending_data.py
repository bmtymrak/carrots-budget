from decimal import Decimal
import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from budgets.models import YearlyBudget, MonthlyBudget, BudgetItem
from budgets.services import BudgetService
from budgets.tests.factories import YearlyBudgetFactory, MonthlyBudgetFactory, BudgetItemFactory
from purchases.tests.factories import CategoryFactory, PurchaseFactory, IncomeFactory

User = get_user_model()


class TestMonthlySpendingData(TestCase):
    """Test the monthly spending data functionality for the yearly budget view."""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="test@example.com", username="testuser", password="password123"
        )
        cls.year = 2024
        cls.yearly_budget = YearlyBudgetFactory(
            user=cls.user, 
            date=datetime.date(cls.year, 1, 1)
        )
        
        # Create categories
        cls.groceries = CategoryFactory(user=cls.user, name="Groceries")
        cls.savings = CategoryFactory(user=cls.user, name="Emergency Fund")
        
        # Create monthly budgets and budget items
        for month in range(1, 13):
            monthly_budget = MonthlyBudget.objects.get(
                user=cls.user,
                yearly_budget=cls.yearly_budget,
                date__month=month
            )
            
            # Create spending budget item
            BudgetItemFactory(
                user=cls.user,
                category=cls.groceries,
                monthly_budget=monthly_budget,
                yearly_budget=cls.yearly_budget,
                amount=Decimal('500.00'),
                savings=False
            )
            
            # Create savings budget item
            BudgetItemFactory(
                user=cls.user,
                category=cls.savings,
                monthly_budget=monthly_budget,
                yearly_budget=cls.yearly_budget,
                amount=Decimal('1000.00'),
                savings=True
            )
        
        # Create purchases for different months
        PurchaseFactory(
            user=cls.user,
            category=cls.groceries,
            date=datetime.date(cls.year, 1, 15),
            amount=Decimal('450.00')
        )
        PurchaseFactory(
            user=cls.user,
            category=cls.groceries,
            date=datetime.date(cls.year, 2, 10),
            amount=Decimal('520.00')
        )
        PurchaseFactory(
            user=cls.user,
            category=cls.groceries,
            date=datetime.date(cls.year, 3, 20),
            amount=Decimal('480.00')
        )
        
        # Create savings transactions
        PurchaseFactory(
            user=cls.user,
            category=cls.savings,
            date=datetime.date(cls.year, 1, 1),
            amount=Decimal('1000.00')
        )
        PurchaseFactory(
            user=cls.user,
            category=cls.savings,
            date=datetime.date(cls.year, 4, 1),
            amount=Decimal('900.00')
        )
    
    def test_monthly_spending_data_structure(self):
        """Test that monthly spending data has the correct structure."""
        service = BudgetService()
        context = service.get_yearly_budget_context(
            user=self.user,
            year=self.year,
            ytd_month=12
        )
        
        self.assertIn('monthly_spending_data', context)
        monthly_data = context['monthly_spending_data']
        
        self.assertIn('spending', monthly_data)
        self.assertIn('savings', monthly_data)
        
        # Check that we have data for our categories
        spending_categories = [cat['category_name'] for cat in monthly_data['spending']]
        savings_categories = [cat['category_name'] for cat in monthly_data['savings']]
        
        self.assertIn('Groceries', spending_categories)
        self.assertIn('Emergency Fund', savings_categories)
    
    def test_monthly_spending_amounts(self):
        """Test that the monthly spending amounts are correct."""
        service = BudgetService()
        context = service.get_yearly_budget_context(
            user=self.user,
            year=self.year,
            ytd_month=12
        )
        
        monthly_data = context['monthly_spending_data']
        
        # Find groceries in spending data
        groceries_data = next(
            (cat for cat in monthly_data['spending'] if cat['category_name'] == 'Groceries'),
            None
        )
        
        self.assertIsNotNone(groceries_data)
        
        # Check January spending
        self.assertIn(1, groceries_data['months'])
        self.assertEqual(groceries_data['months'][1]['spent'], Decimal('450.00'))
        self.assertEqual(groceries_data['months'][1]['budgeted'], Decimal('500.00'))
        
        # Check February spending
        self.assertIn(2, groceries_data['months'])
        self.assertEqual(groceries_data['months'][2]['spent'], Decimal('520.00'))
        
        # Check March spending
        self.assertIn(3, groceries_data['months'])
        self.assertEqual(groceries_data['months'][3]['spent'], Decimal('480.00'))
        
        # Check months with no spending
        self.assertIn(12, groceries_data['months'])
        self.assertEqual(groceries_data['months'][12]['spent'], 0)
    
    def test_monthly_savings_amounts(self):
        """Test that the monthly savings amounts are correct."""
        service = BudgetService()
        context = service.get_yearly_budget_context(
            user=self.user,
            year=self.year,
            ytd_month=12
        )
        
        monthly_data = context['monthly_spending_data']
        
        # Find Emergency Fund in savings data
        savings_data = next(
            (cat for cat in monthly_data['savings'] if cat['category_name'] == 'Emergency Fund'),
            None
        )
        
        self.assertIsNotNone(savings_data)
        
        # Check January
        self.assertIn(1, savings_data['months'])
        self.assertEqual(savings_data['months'][1]['spent'], Decimal('1000.00'))
        
        # Check April
        self.assertIn(4, savings_data['months'])
        self.assertEqual(savings_data['months'][4]['spent'], Decimal('900.00'))
        
        # Check months with no savings
        self.assertIn(2, savings_data['months'])
        self.assertEqual(savings_data['months'][2]['spent'], 0)
