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

    def test_category_edit_view(self):
        category = CategoryFactory(user=self.user, name='Original Name', rollover=False)
        
        response = self.client.post(
            reverse('category_edit_htmx', kwargs={'pk': category.pk}),
            {
                'name': 'Updated Name',
                'rollover': 'on',
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)
        
        category.refresh_from_db()
        self.assertEqual(category.name, 'Updated Name')
        self.assertTrue(category.rollover)

    def test_category_edit_view_get(self):
        category = CategoryFactory(user=self.user, name='Test Category')
        
        response = self.client.get(
            reverse('category_edit_htmx', kwargs={'pk': category.pk}),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Category')

    def test_category_edit_only_own_category(self):
        other_user = get_user_model().objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        category = CategoryFactory(user=other_user, name='Other Category')
        
        # Attempt to edit another user's category should fail
        with self.assertRaises(Category.DoesNotExist):
            response = self.client.post(
                reverse('category_edit_htmx', kwargs={'pk': category.pk}),
                {
                    'name': 'Hacked Name',
                    'next': '/'
                }
            )
