import datetime
import unittest

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from purchases.models import Category, Purchase, Income, RecurringPurchase
from budgets.models import YearlyBudget
from .factories import (
    CategoryFactory,
    SubcategoryFactory,
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

    def test_purchase_list_view(self):
        """Test that the purchase list view loads successfully"""
        response = self.client.get(reverse('purchase_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'purchase_list.html')
    
    def test_purchase_list_pagination(self):
        """Test that purchases are paginated to 200 items per page"""
        # Create 250 purchases
        for i in range(250):
            PurchaseFactory(user=self.user, category=self.category)
        
        response = self.client.get(reverse('purchase_list'))
        self.assertEqual(response.status_code, 200)
        # Should have pagination
        self.assertTrue(response.context['is_paginated'])
        # First page should have 200 items
        self.assertEqual(len(response.context['purchases']), 200)
        # Should have 2 pages total
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 2)
    
    def test_purchase_list_filter_by_category(self):
        """Test filtering purchases by category"""
        category2 = CategoryFactory(user=self.user, name='Category 2')
        
        # Create purchases with different categories
        for i in range(5):
            PurchaseFactory(user=self.user, category=self.category)
        for i in range(3):
            PurchaseFactory(user=self.user, category=category2)
        
        # Filter by first category
        response = self.client.get(reverse('purchase_list'), {'category': self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['purchases']), 5)
    
    def test_purchase_list_filter_by_year(self):
        """Test filtering purchases by year"""
        # Create purchases in different years
        for i in range(3):
            PurchaseFactory(
                user=self.user, 
                category=self.category,
                date=datetime.date(2023, 1, 1)
            )
        for i in range(4):
            PurchaseFactory(
                user=self.user, 
                category=self.category,
                date=datetime.date(2024, 1, 1)
            )
        
        # Filter by 2024
        response = self.client.get(reverse('purchase_list'), {'year': '2024'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['purchases']), 4)
    
    def test_purchase_list_filter_by_month(self):
        """Test filtering purchases by month and year"""
        # Create purchases in different months
        for i in range(2):
            PurchaseFactory(
                user=self.user, 
                category=self.category,
                date=datetime.date(2024, 1, 15)
            )
        for i in range(3):
            PurchaseFactory(
                user=self.user, 
                category=self.category,
                date=datetime.date(2024, 2, 15)
            )
        
        # Filter by February 2024
        response = self.client.get(reverse('purchase_list'), {'year': '2024', 'month': '2'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['purchases']), 3)
    
    def test_purchase_list_combined_filters(self):
        """Test combining category, year, and month filters"""
        category2 = CategoryFactory(user=self.user, name='Category 2')
        
        # Create purchases with different combinations
        PurchaseFactory(
            user=self.user, 
            category=self.category,
            date=datetime.date(2024, 1, 15)
        )
        PurchaseFactory(
            user=self.user, 
            category=self.category,
            date=datetime.date(2024, 2, 15)
        )
        PurchaseFactory(
            user=self.user, 
            category=category2,
            date=datetime.date(2024, 2, 15)
        )
        
        # Filter by category, year, and month
        response = self.client.get(reverse('purchase_list'), {
            'category': self.category.id,
            'year': '2024',
            'month': '2'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['purchases']), 1)
    
    def test_purchase_list_invalid_category_filter(self):
        """Test that invalid category IDs are handled gracefully"""
        PurchaseFactory(user=self.user, category=self.category)
        
        # Test with non-integer category
        response = self.client.get(reverse('purchase_list'), {'category': 'invalid'})
        self.assertEqual(response.status_code, 200)
        
        # Test with non-existent category ID
        response = self.client.get(reverse('purchase_list'), {'category': '99999'})
        self.assertEqual(response.status_code, 200)
    
    def test_purchase_list_invalid_year_filter(self):
        """Test that invalid year values are handled gracefully"""
        PurchaseFactory(user=self.user, category=self.category)
        
        # Test with non-integer year
        response = self.client.get(reverse('purchase_list'), {'year': 'invalid'})
        self.assertEqual(response.status_code, 200)
        
        # Test with out-of-range year
        response = self.client.get(reverse('purchase_list'), {'year': '12345'})
        self.assertEqual(response.status_code, 200)
    
    def test_purchase_list_invalid_month_filter(self):
        """Test that invalid month values are handled gracefully"""
        PurchaseFactory(user=self.user, category=self.category)
        
        # Test with non-integer month
        response = self.client.get(reverse('purchase_list'), {'year': '2024', 'month': 'invalid'})
        self.assertEqual(response.status_code, 200)
        
        # Test with out-of-range month
        response = self.client.get(reverse('purchase_list'), {'year': '2024', 'month': '13'})
        self.assertEqual(response.status_code, 200)



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

    def _management_form_data(self, total_forms):
        return {
            'form-TOTAL_FORMS': str(total_forms),
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
        }

    def _build_add_to_month_post_data(self, rows, next_url='/'):
        data = {
            **self._management_form_data(len(rows)),
            'next': next_url,
        }

        for index, row in enumerate(rows):
            recurring = row['recurring']
            data[f'form-{index}-recurring_purchase_id'] = str(
                row.get('recurring_purchase_id', recurring.pk)
            )

            if row.get('selected', True):
                data[f'form-{index}-selected'] = 'on'

            data[f'form-{index}-date'] = row.get('date', '2024-01-01')
            data[f'form-{index}-amount'] = row.get('amount', str(recurring.amount))
            data[f'form-{index}-source'] = row.get('source', recurring.source)
            data[f'form-{index}-location'] = row.get('location', recurring.location)
            data[f'form-{index}-category'] = row.get('category', str(recurring.category_id))
            data[f'form-{index}-notes'] = row.get('notes', recurring.notes)

        return data

    def test_recurring_purchase_list_view_get(self):
        """Test GET request to recurring purchase list."""
        response = self.client.get(
            reverse('recurring_purchase_list'),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'purchases/recurring_purchase_list_modal.html')

    def test_recurring_purchase_create_via_list(self):
        """Test creating a recurring purchase via the list view."""
        response = self.client.post(
            reverse('recurring_purchase_list'),
            {
                'item': 'Netflix',
                'amount': '15.99',
                'category': self.category.id,
                'source': 'Netflix Inc',
                'location': 'Online',
                'notes': 'Monthly subscription',
                'is_active': True,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)  # HTMX redirect
        self.assertTrue(
            RecurringPurchase.objects.filter(
                user=self.user,
                item='Netflix'
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
        self.assertTemplateUsed(response, 'purchases/recurring_purchase_edit_modal.html')
        self.assertContains(response, 'hx-target="#modal-content"', html=False)
        self.assertContains(response, 'hx-swap="innerHTML"', html=False)

    def test_recurring_purchase_edit_view_post(self):
        """Test POST request to update a recurring purchase."""
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Old Name',
            amount=Decimal('10.00')
        )
        response = self.client.post(
            reverse('recurring_purchase_edit', kwargs={'pk': recurring.pk}),
            {
                'item': 'New Name',
                'amount': '20.00',
                'category': self.category.id,
                'source': 'New Source',
                'location': 'New Location',
                'notes': 'Updated notes',
                'is_active': True,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)  # HTMX redirect
        recurring.refresh_from_db()
        self.assertEqual(recurring.item, 'New Name')
        self.assertEqual(recurring.amount, Decimal('20.00'))

    def test_recurring_purchase_delete_view_get(self):
        """Test GET request to recurring purchase delete view."""
        recurring = RecurringPurchaseFactory(user=self.user, category=self.category)
        response = self.client.get(
            reverse('recurring_purchase_delete', kwargs={'pk': recurring.pk}),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'purchases/recurring_purchase_delete_modal.html')

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
        self.assertTemplateUsed(response, 'purchases/recurring_purchase_add_to_month_modal.html')
        self.assertContains(response, 'hx-target="#modal-content"', html=False)
        self.assertContains(response, 'hx-swap="innerHTML"', html=False)
        self.assertFalse(response.context['formset'].forms[0].initial['selected'])

    def test_recurring_purchase_add_to_month_creates_purchases(self):
        """Test that submitting the form creates actual purchases."""
        yearly_budget = YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Netflix',
            amount=Decimal('15.99'),
            source='Netflix Inc',
            location='Online'
        )
        
        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            self._build_add_to_month_post_data(
                [
                    {
                        'recurring': recurring,
                        'amount': '15.99',
                        'source': 'Netflix Inc',
                        'location': 'Online',
                        'category': str(self.category.id),
                        'notes': 'Monthly sub',
                    }
                ]
            )
        )
        self.assertEqual(response.status_code, 200)  # HTMX redirect
        
        # Check that a purchase was created with the foreign key set
        purchase = Purchase.objects.get(user=self.user, item='Netflix')
        self.assertEqual(purchase.amount, Decimal('15.99'))
        self.assertEqual(purchase.category, self.category)
        self.assertEqual(purchase.date, datetime.date(2024, 1, 1))
        self.assertEqual(purchase.recurring_purchase, recurring)

    def test_recurring_purchase_already_added_detected_by_fk(self):
        """Test that recurring purchases are detected as already added via FK."""
        yearly_budget = YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Netflix',
            amount=Decimal('15.99')
        )
        
        # Create an existing purchase with the recurring_purchase FK set
        Purchase.objects.create(
            user=self.user,
            item='Netflix',
            date=datetime.date(2024, 1, 15),
            amount=Decimal('15.99'),
            category=self.category,
            recurring_purchase=recurring
        )
        
        response = self.client.get(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(recurring.id, response.context['already_added'])

    def test_recurring_purchase_add_with_modified_amount(self):
        """Test that modified amounts are used when creating purchases."""
        yearly_budget = YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Spotify',
            amount=Decimal('9.99')
        )
        
        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            self._build_add_to_month_post_data(
                [
                    {
                        'recurring': recurring,
                        'amount': '14.99',
                        'source': recurring.source,
                        'location': recurring.location,
                        'category': str(self.category.id),
                        'notes': recurring.notes,
                    }
                ]
            )
        )
        self.assertEqual(response.status_code, 200)
        
        purchase = Purchase.objects.get(user=self.user, item='Spotify')
        self.assertEqual(purchase.amount, Decimal('14.99'))

    def test_recurring_purchase_add_allows_blank_amount(self):
        """Test that selected recurring purchases can be created without an amount."""
        YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Daycare',
            amount=Decimal('1500.00')
        )

        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            self._build_add_to_month_post_data(
                [
                    {
                        'recurring': recurring,
                        'amount': '',
                        'source': recurring.source,
                        'location': recurring.location,
                        'category': str(self.category.id),
                        'notes': recurring.notes,
                    }
                ]
            )
        )

        self.assertEqual(response.status_code, 200)
        purchase = Purchase.objects.get(user=self.user, item='Daycare')
        self.assertIsNone(purchase.amount)

    def test_recurring_purchase_post_does_not_duplicate_existing_month_entry(self):
        """Test POST path skips a recurring purchase already added for that month."""
        YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Netflix',
            amount=Decimal('15.99')
        )

        Purchase.objects.create(
            user=self.user,
            item='Netflix',
            date=datetime.date(2024, 1, 10),
            amount=Decimal('15.99'),
            category=self.category,
            recurring_purchase=recurring,
        )

        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            self._build_add_to_month_post_data(
                [
                    {
                        'recurring': recurring,
                        'amount': '15.99',
                        'source': recurring.source,
                        'location': recurring.location,
                        'category': str(self.category.id),
                        'notes': recurring.notes,
                    }
                ]
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Purchase.objects.filter(
                user=self.user,
                recurring_purchase=recurring,
                date__year=2024,
                date__month=1,
            ).count(),
            1,
        )

    def test_recurring_purchase_post_rejects_tampered_recurring_purchase_id(self):
        """Test tampering with a row recurring_purchase_id re-renders with validation errors."""
        YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='GitHub',
            amount=Decimal('4.00')
        )

        other_recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Other',
            amount=Decimal('7.00')
        )

        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            self._build_add_to_month_post_data(
                [
                    {
                        'recurring': recurring,
                        'recurring_purchase_id': str(other_recurring.pk),
                        'amount': '4.00',
                        'source': recurring.source,
                        'location': recurring.location,
                        'category': str(self.category.id),
                        'notes': recurring.notes,
                    },
                    {
                        'recurring': other_recurring,
                        'selected': False,
                    },
                ]
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Purchase.objects.filter(
                user=self.user,
                recurring_purchase=recurring,
                date__year=2024,
                date__month=1,
            ).exists()
        )
        self.assertFormError(
            response.context['formset'].forms[0],
            'recurring_purchase_id',
            'Recurring purchase does not match this row.'
        )

    def test_invalid_post_preserves_selected_state_without_mutating_already_added(self):
        """Invalid POST should preserve user input separately from persisted already-added state."""
        YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        existing_recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Netflix',
            amount=Decimal('15.99')
        )
        selected_recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Spotify',
            amount=Decimal('9.99')
        )
        other_user = get_user_model().objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_category = CategoryFactory(user=other_user)

        Purchase.objects.create(
            user=self.user,
            item='Netflix',
            date=datetime.date(2024, 1, 10),
            amount=Decimal('15.99'),
            category=self.category,
            recurring_purchase=existing_recurring,
        )

        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2024, 'month': 1}),
            self._build_add_to_month_post_data(
                [
                    {
                        'recurring': existing_recurring,
                        'selected': False,
                    },
                    {
                        'recurring': selected_recurring,
                        'date': '2024-01-18',
                        'amount': '12.34',
                        'source': 'Updated source',
                        'location': 'Updated location',
                        'category': str(other_category.pk),
                        'notes': 'Updated notes',
                    },
                ]
            )
        )

        self.assertEqual(response.status_code, 200)
        formset = response.context['formset']
        self.assertTrue(formset.forms[0].already_added)
        self.assertEqual(formset.forms[1]['amount'].value(), '12.34')
        self.assertTrue(formset.forms[1]['selected'].value())
        self.assertContains(
            response,
            'name="form-1-selected"',
            html=False,
        )
        self.assertContains(response, 'Please correct the highlighted recurring purchase values and try again.')

    def test_invalid_post_renders_single_heading(self):
        """Invalid recurring purchase submission should render the modal heading exactly once."""
        YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2028, 2, 1)
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item='Daycare',
            amount=Decimal('1500.00')
        )

        response = self.client.post(
            reverse('recurring_purchase_add_to_month', kwargs={'year': 2028, 'month': 2}),
            self._build_add_to_month_post_data(
                [
                    {
                        'recurring': recurring,
                        'category': '',
                    }
                ]
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<h2>Add Recurring Purchases for February 2028</h2>',
            html=False,
            count=1,
        )
        self.assertContains(response, 'This field is required.')
