import datetime
import unittest

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from purchases.models import Category, Purchase, Income, RecurringPurchase
from purchases.forms import IncomeForm
from budgets.models import YearlyBudget, MonthlyBudget
from .factories import (
    CategoryFactory,
    SubcategoryFactory,
    PurchaseFactory,
    IncomeFactory,
    RecurringPurchaseFactory,
)


User = get_user_model()




class PurchaseViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.category = CategoryFactory(user=self.user)
        self.subcategory = SubcategoryFactory(user=self.user)

    def test_purchase_create_view(self):
        response = self.client.post(
            reverse('purchase_create'),
            {
                'form-TOTAL_FORMS': '1',
                'form-INITIAL_FORMS': '0',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-item': 'Test Purchase',
                'form-0-date': datetime.date.today(),
                'form-0-amount': '100.00',
                'form-0-source': 'Test Store',
                'form-0-location': 'Test Location',
                'form-0-category': self.category.id,
                'form-0-subcategory': self.subcategory.id,
                'form-0-notes': 'Test notes',
                'form-0-savings': False,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Purchase.objects.filter(
                user=self.user,
                item='Test Purchase'
            ).exists()
        )

    @unittest.skip("Feature 'new_category' is not implemented in Purchase backend")
    def test_purchase_create_with_new_category(self):
        response = self.client.post(
            reverse('purchase_create'),
            {
                'form-TOTAL_FORMS': '1',
                'form-INITIAL_FORMS': '0',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-item': 'Test Purchase',
                'form-0-date': datetime.date.today(),
                'form-0-amount': '100.00',
                'form-0-source': 'Test Store',
                'form-0-location': 'Test Location',
                'form-0-new_category': 'New Test Category',
                'form-0-notes': 'Test notes',
                'form-0-savings': False,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Purchase.objects.filter(
                user=self.user,
                item='Test Purchase',
                category__name='New Test Category'
            ).exists()
        )




class IncomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.category = CategoryFactory(user=self.user)

    def test_income_create_view(self):
        response = self.client.post(
            reverse('income_create'),
            {
                'amount': '5000.00',
                'date': datetime.date.today(),
                'source': 'Test Employer',
                'payer': 'Test Payer',
                'category': self.category.id,
                'notes': 'Test income'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Income.objects.filter(
                user=self.user,
                amount=Decimal('5000.00')
            ).exists()
        )

    @unittest.skip("Feature 'new_category' is not implemented in Income backend")
    def test_income_create_with_new_category(self):
        response = self.client.post(
            reverse('income_create'),
            {
                'amount': '5000.00',
                'date': datetime.date.today(),
                'source': 'Test Employer',
                'payer': 'Test Payer',
                'new_category': 'New Income Category',
                'notes': 'Test income'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Income.objects.filter(
                user=self.user,
                amount=Decimal('5000.00'),
                category__name='New Income Category'
            ).exists()
        )




class CategoryViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_category_create_view(self):
        response = self.client.post(
            reverse('category_create'),
            {
                'name': 'Test Category',
                'rollover': True,
                'notes': 'Test category notes'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Category.objects.filter(
                user=self.user,
                name='Test Category'
            ).exists()
        )


class RecurringPurchaseViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.category = CategoryFactory(user=self.user)

    def test_recurring_purchase_list_view_get(self):
        """Test GET request to recurring purchase list."""
        response = self.client.get(
            reverse('recurring_purchase_list'),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'purchases/recurring_purchase_list_htmx.html')

    def test_recurring_purchase_create_via_list(self):
        """Test creating a recurring purchase via the list view."""
        response = self.client.post(
            reverse('recurring_purchase_list'),
            {
                'name': 'Netflix',
                'amount': '15.99',
                'category': self.category.id,
                'merchant': 'Netflix Inc',
                'notes': 'Monthly subscription',
                'is_active': True,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)  # HTMX redirect
        self.assertTrue(
            RecurringPurchase.objects.filter(
                user=self.user,
                name='Netflix'
            ).exists()
        )

    def test_recurring_purchase_edit_view_get(self):
        """Test GET request to recurring purchase edit view."""
        recurring = RecurringPurchaseFactory(user=self.user, category=self.category)
        response = self.client.get(
            reverse('recurring_purchase_edit', kwargs={'pk': recurring.pk}),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'purchases/recurring_purchase_edit_htmx.html')

    def test_recurring_purchase_edit_view_post(self):
        """Test POST request to update a recurring purchase."""
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            name='Old Name',
            amount=Decimal('10.00')
        )
        response = self.client.post(
            reverse('recurring_purchase_edit', kwargs={'pk': recurring.pk}),
            {
                'name': 'New Name',
                'amount': '20.00',
                'category': self.category.id,
                'merchant': 'New Merchant',
                'notes': 'Updated notes',
                'is_active': True,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)  # HTMX redirect
        recurring.refresh_from_db()
        self.assertEqual(recurring.name, 'New Name')
        self.assertEqual(recurring.amount, Decimal('20.00'))

    def test_recurring_purchase_delete_view_get(self):
        """Test GET request to recurring purchase delete view."""
        recurring = RecurringPurchaseFactory(user=self.user, category=self.category)
        response = self.client.get(
            reverse('recurring_purchase_delete', kwargs={'pk': recurring.pk}),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'purchases/recurring_purchase_delete_htmx.html')

    def test_recurring_purchase_delete_view_delete(self):
        """Test DELETE request to delete a recurring purchase."""
        recurring = RecurringPurchaseFactory(user=self.user, category=self.category)
        recurring_id = recurring.pk
        response = self.client.delete(
            reverse('recurring_purchase_delete', kwargs={'pk': recurring.pk}) + '?next=/'
        )
        self.assertEqual(response.status_code, 200)  # HTMX redirect
        self.assertFalse(
            RecurringPurchase.objects.filter(pk=recurring_id).exists()
        )

    def test_recurring_purchase_add_to_month_view_get(self):
        """Test GET request to add recurring purchases to month."""
        yearly_budget = YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(user=self.user, category=self.category)
        
        response = self.client.get(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'purchases/recurring_purchase_add_to_month_htmx.html')

    def test_recurring_purchase_add_to_month_creates_purchases(self):
        """Test that submitting the form creates actual purchases."""
        yearly_budget = YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            name='Netflix',
            amount=Decimal('15.99'),
            merchant='Netflix Inc'
        )
        
        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            {
                'selected_recurring': [str(recurring.pk)],
                f'amount_{recurring.pk}': '15.99',
                f'merchant_{recurring.pk}': 'Netflix Inc',
                f'notes_{recurring.pk}': 'Monthly sub',
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)  # HTMX redirect
        
        # Check that a purchase was created
        purchase = Purchase.objects.get(user=self.user, item='Netflix')
        self.assertEqual(purchase.amount, Decimal('15.99'))
        self.assertEqual(purchase.category, self.category)
        self.assertEqual(purchase.date, datetime.date(2024, 1, 1))

    def test_recurring_purchase_add_with_modified_amount(self):
        """Test that modified amounts are used when creating purchases."""
        yearly_budget = YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            name='Spotify',
            amount=Decimal('9.99')
        )
        
        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            {
                'selected_recurring': [str(recurring.pk)],
                f'amount_{recurring.pk}': '14.99',  # Different amount
                f'merchant_{recurring.pk}': recurring.merchant,
                f'notes_{recurring.pk}': recurring.notes,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)
        
        purchase = Purchase.objects.get(user=self.user, item='Spotify')
        self.assertEqual(purchase.amount, Decimal('14.99'))
