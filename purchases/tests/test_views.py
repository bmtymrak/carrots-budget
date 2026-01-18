import datetime
import unittest

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from purchases.models import Category, Purchase, Income
from purchases.forms import IncomeForm
from .factories import (
    CategoryFactory,
    SubcategoryFactory,
    PurchaseFactory,
    IncomeFactory,
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
