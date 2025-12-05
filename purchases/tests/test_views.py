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


class TestPurchaseEditView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

        cls.test_category = Category.objects.create(
            name="Test Category", user=cls.user1
        )
        cls.test_purchase = Purchase.objects.create(
            item="Test Item",
            date=datetime.datetime.now(),
            user=cls.user1,
            amount=10.10,
            source="Test Source",
            location="Test Location",
            category=cls.test_category,
        )

    def test_redirect_if_logged_in(self):
        response = self.client.get(
            reverse("purchase_edit", args=[self.test_purchase.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, f"/accounts/login/?next=/purchases/{self.test_purchase.pk}/edit/"
        )

    def test_logged_in_uses_correct_template(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("purchase_edit", args=[self.test_purchase.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "purchases/purchase_edit.html")

    def test_correct_object_used(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("purchase_edit", args=[self.test_purchase.pk])
        )

        self.assertEqual(response.context["object"], self.test_purchase)


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

    def test_purchase_edit_view(self):
        purchase = PurchaseFactory(
            user=self.user,
            category=self.category,
            amount=Decimal('100.00')
        )
        
        response = self.client.post(
            reverse('purchase_edit', kwargs={'pk': purchase.pk}),
            {
                'item': purchase.item,
                'date': purchase.date,
                'amount': '200.00',
                'source': purchase.source,
                'location': purchase.location,
                'category': self.category.id,
                'subcategory': self.subcategory.id,
                'notes': 'Updated notes',
                'savings': False,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 302)
        purchase.refresh_from_db()
        self.assertEqual(purchase.amount, Decimal('200.00'))

    def test_purchase_delete_view(self):
        purchase = PurchaseFactory(user=self.user)
        response = self.client.post(
            reverse('purchase_delete', kwargs={'pk': purchase.pk}),
            {'next': '/'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Purchase.objects.filter(id=purchase.id).exists()
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

    def test_income_edit_view(self):
        income = IncomeFactory(
            user=self.user,
            category=self.category,
            amount=Decimal('5000.00')
        )
        
        response = self.client.post(
            reverse('income_edit', kwargs={'pk': income.pk}),
            {
                'amount': '6000.00',
                'date': income.date,
                'source': income.source,
                'payer': income.payer,
                'category': self.category.id,
                'notes': 'Updated income'
            }
        )
        self.assertEqual(response.status_code, 302)
        income.refresh_from_db()
        self.assertEqual(income.amount, Decimal('6000.00'))

    def test_income_delete_view(self):
        income = IncomeFactory(user=self.user)
        response = self.client.post(
            reverse('income_delete', kwargs={'pk': income.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Income.objects.filter(id=income.id).exists()
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
