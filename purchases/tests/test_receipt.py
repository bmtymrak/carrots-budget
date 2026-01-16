import datetime

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from purchases.models import Purchase, Receipt
from .factories import (
    CategoryFactory,
    SubcategoryFactory,
    PurchaseFactory,
    ReceiptFactory,
)


User = get_user_model()


class ReceiptModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_receipt_creation(self):
        """Test that a receipt can be created"""
        receipt = Receipt.objects.create(user=self.user)
        self.assertIsNotNone(receipt.id)
        self.assertEqual(receipt.user, self.user)
        self.assertIsNotNone(receipt.created_at)
        self.assertIsNotNone(receipt.updated_at)

    def test_receipt_str(self):
        """Test the string representation of a receipt"""
        receipt = Receipt.objects.create(user=self.user)
        self.assertIn("Receipt", str(receipt))
        self.assertIn(str(receipt.created_at.date()), str(receipt))


class ReceiptPurchaseRelationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = CategoryFactory(user=self.user)
        self.subcategory = SubcategoryFactory(user=self.user)

    def test_purchases_linked_to_receipt(self):
        """Test that multiple purchases can be linked to the same receipt"""
        receipt = Receipt.objects.create(user=self.user)
        
        purchase1 = Purchase.objects.create(
            user=self.user,
            item='Item 1',
            amount=Decimal('10.00'),
            date=datetime.date.today(),
            receipt=receipt
        )
        purchase2 = Purchase.objects.create(
            user=self.user,
            item='Item 2',
            amount=Decimal('20.00'),
            date=datetime.date.today(),
            receipt=receipt
        )
        
        self.assertEqual(purchase1.receipt, receipt)
        self.assertEqual(purchase2.receipt, receipt)
        self.assertEqual(receipt.purchases.count(), 2)


class ReceiptPurchaseCreateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.category = CategoryFactory(user=self.user)
        self.subcategory = SubcategoryFactory(user=self.user)

    def test_single_purchase_creates_receipt(self):
        """Test that creating a single purchase creates a receipt"""
        initial_receipt_count = Receipt.objects.count()
        
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
        
        self.assertEqual(Receipt.objects.count(), initial_receipt_count + 1)
        purchase = Purchase.objects.get(item='Test Purchase')
        self.assertIsNotNone(purchase.receipt)
        self.assertEqual(purchase.receipt.user, self.user)

    def test_multiple_purchases_share_receipt(self):
        """Test that multiple purchases created together share the same receipt"""
        initial_receipt_count = Receipt.objects.count()
        
        response = self.client.post(
            reverse('purchase_create'),
            {
                'form-TOTAL_FORMS': '2',
                'form-INITIAL_FORMS': '0',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-item': 'Purchase 1',
                'form-0-date': datetime.date.today(),
                'form-0-amount': '50.00',
                'form-0-source': 'Test Store',
                'form-0-location': 'Test Location',
                'form-0-category': self.category.id,
                'form-0-subcategory': self.subcategory.id,
                'form-0-notes': '',
                'form-0-savings': False,
                'form-1-item': 'Purchase 2',
                'form-1-date': datetime.date.today(),
                'form-1-amount': '75.00',
                'form-1-source': 'Test Store',
                'form-1-location': 'Test Location',
                'form-1-category': self.category.id,
                'form-1-subcategory': self.subcategory.id,
                'form-1-notes': '',
                'form-1-savings': False,
                'next': '/'
            }
        )
        
        # Should create only one new receipt
        self.assertEqual(Receipt.objects.count(), initial_receipt_count + 1)
        
        purchase1 = Purchase.objects.get(item='Purchase 1')
        purchase2 = Purchase.objects.get(item='Purchase 2')
        
        # Both purchases should have the same receipt
        self.assertIsNotNone(purchase1.receipt)
        self.assertIsNotNone(purchase2.receipt)
        self.assertEqual(purchase1.receipt, purchase2.receipt)


class ReceiptPurchaseEditTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.category = CategoryFactory(user=self.user)
        self.subcategory = SubcategoryFactory(user=self.user)

    def test_edit_shows_all_purchases_from_receipt(self):
        """Test that editing a purchase shows all purchases from the same receipt"""
        receipt = Receipt.objects.create(user=self.user)
        
        purchase1 = Purchase.objects.create(
            user=self.user,
            item='Item 1',
            amount=Decimal('10.00'),
            date=datetime.date.today(),
            receipt=receipt,
            category=self.category,
            source='Store A',
            location='Location A'
        )
        purchase2 = Purchase.objects.create(
            user=self.user,
            item='Item 2',
            amount=Decimal('20.00'),
            date=datetime.date.today(),
            receipt=receipt,
            category=self.category,
            source='Store A',
            location='Location A'
        )
        
        response = self.client.get(
            reverse('purchase_edit_htmx', kwargs={'pk': purchase1.id}),
            {'next': '/'}
        )
        
        self.assertEqual(response.status_code, 200)
        # Check that both purchases are in the formset
        self.assertContains(response, 'Item 1')
        self.assertContains(response, 'Item 2')

    def test_edit_single_purchase_without_receipt(self):
        """Test that editing a purchase without a receipt only shows that purchase"""
        purchase = Purchase.objects.create(
            user=self.user,
            item='Solo Item',
            amount=Decimal('30.00'),
            date=datetime.date.today(),
            category=self.category,
            source='Store B',
            location='Location B'
        )
        
        response = self.client.get(
            reverse('purchase_edit_htmx', kwargs={'pk': purchase.id}),
            {'next': '/'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Solo Item')
