import datetime
import unittest
from urllib.parse import quote

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from purchases.models import Category, Purchase, Income, RecurringPurchase, Receipt
from budgets.models import YearlyBudget
from .factories import (
    CategoryFactory,
    PurchaseFactory,
    SubcategoryFactory,
    RecurringPurchaseFactory,
)

User = get_user_model()

TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    # Avoid manifest-based static file lookups when rendering templates in tests.
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(STORAGES=TEST_STORAGES)
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

    def test_purchase_create_get_without_next_uses_purchase_list(self):
        response = self.client.get(reverse("purchase_create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], reverse("purchase_list"))
        self.assertContains(response, "<h2>Add a purchase</h2>", html=True)
        self.assertContains(response, "data-purchase-row>", count=1)
        self.assertContains(response, "data-purchase-count")

    def test_purchase_create_rejects_external_next_url(self):
        response = self.client.get(
            reverse("purchase_create"),
            {"next": "https://example.com/collect"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], reverse("purchase_list"))

    def test_purchase_create_post_without_next_redirects_to_purchase_list(self):
        response = self.client.post(
            reverse("purchase_create"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-item": "Test Purchase",
                "form-0-date": datetime.date.today(),
                "form-0-amount": "10.00",
                "form-0-source": "Test Store",
                "form-0-location": "Test Location",
                "form-0-category": self.category.id,
                "form-0-subcategory": self.subcategory.id,
                "form-0-notes": "",
                "form-0-savings": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Redirect"], reverse("purchase_list"))

    def test_sidebar_purchase_button_preserves_full_return_url(self):
        response = self.client.get(
            reverse("purchase_list"),
            {
                "search": "coffee & bagels",
                "purchase_date_from": "2026-01-01",
            },
        )
        return_url = response.context["request"].get_full_path()
        encoded_return_url = quote(return_url, safe="")
        purchase_url = (
            f'{reverse("purchase_create")}?next={encoded_return_url}'
        )

        self.assertContains(
            response,
            (
                f'<button class="sidebar-action" type="button" '
                f'hx-get="{purchase_url}" hx-target="#modal-content">'
                "Add a Purchase</button>"
            ),
            html=True,
        )
        self.assertNotContains(response, f"href='{purchase_url}'", html=False)

        purchase_form_response = self.client.get(
            reverse("purchase_create"),
            {"next": return_url},
        )
        self.assertEqual(purchase_form_response.context["next"], return_url)

        content = response.content.decode()
        self.assertLess(content.index("Purchase List</a>"), content.index("Add a Purchase</button>"))
        self.assertLess(content.index("Add a Purchase</button>"), content.index("Logout</a>"))

    def test_purchase_create_view(self):
        response = self.client.post(
            reverse('purchase_create'),
            {
                'form-TOTAL_FORMS': '2',
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
                'form-1-item': 'Test Purchase 2',
                'form-1-date': datetime.date.today(),
                'form-1-amount': '50.00',
                'form-1-source': '',
                'form-1-location': '',
                'form-1-category': self.category.id,
                'form-1-subcategory': self.subcategory.id,
                'form-1-notes': 'More notes',
                'form-1-savings': False,
                'next': '/'
            }
        )
        self.assertEqual(response.status_code, 200)
        purchases = list(
            Purchase.objects.filter(user=self.user).order_by("item")
        )
        self.assertEqual(len(purchases), 2)
        self.assertEqual(purchases[0].receipt_id, purchases[1].receipt_id)
        self.assertEqual(purchases[0].source, "Test Store")
        self.assertEqual(purchases[0].location, "Test Location")
        self.assertEqual(purchases[1].source, "Test Store")
        self.assertEqual(purchases[1].location, "Test Location")
        self.assertEqual(Receipt.objects.filter(user=self.user).count(), 1)

    def test_purchase_edit_shows_other_purchases_from_same_receipt(self):
        receipt = Receipt.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1),
            source="Old Store",
            location="Old Location",
        )
        first = Purchase.objects.create(
            user=self.user,
            receipt=receipt,
            item="First",
            date=datetime.date(2024, 1, 1),
            amount=Decimal("10.00"),
            source="Old Store",
            location="Old Location",
            category=self.category,
            subcategory=self.subcategory,
        )
        second = Purchase.objects.create(
            user=self.user,
            receipt=receipt,
            item="Second",
            date=datetime.date(2024, 1, 1),
            amount=Decimal("20.00"),
            source="Old Store",
            location="Old Location",
            category=self.category,
            subcategory=self.subcategory,
            notes="Sibling notes",
        )

        response = self.client.get(
            reverse("purchase_edit_htmx", kwargs={"pk": first.pk}),
            {"next": "/"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["receipt"], receipt)
        self.assertEqual(
            list(response.context["receipt_purchases"]),
            [first, second],
        )
        self.assertEqual(
            list(response.context["purchase_formset"].queryset),
            [first, second],
        )
        self.assertContains(response, "Purchases on this receipt")
        self.assertContains(response, "First")
        self.assertContains(response, "Second")
        self.assertContains(response, "Sibling notes")

    def test_purchase_edit_keeps_receipt_metadata_in_sync(self):
        receipt = Receipt.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1),
            source="Old Store",
            location="Old Location",
        )
        first = Purchase.objects.create(
            user=self.user,
            receipt=receipt,
            item="First",
            date=datetime.date(2024, 1, 1),
            amount=Decimal("10.00"),
            source="Old Store",
            location="Old Location",
            category=self.category,
            subcategory=self.subcategory,
        )
        second = Purchase.objects.create(
            user=self.user,
            receipt=receipt,
            item="Second",
            date=datetime.date(2024, 1, 1),
            amount=Decimal("20.00"),
            source="Old Store",
            location="Old Location",
            category=self.category,
            subcategory=self.subcategory,
        )

        response = self.client.post(
            reverse("purchase_edit_htmx", kwargs={"pk": first.pk}),
            {
                "date": "2024-02-01",
                "source": "New Store",
                "location": "New Location",
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "2",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": str(first.pk),
                "form-0-item": "First updated",
                "form-0-amount": "12.00",
                "form-0-category": self.category.pk,
                "form-0-subcategory": self.subcategory.pk,
                "form-0-notes": "Updated",
                "form-0-savings": False,
                "form-1-id": str(second.pk),
                "form-1-item": "Second",
                "form-1-amount": "20.00",
                "form-1-category": self.category.pk,
                "form-1-subcategory": self.subcategory.pk,
                "form-1-notes": "",
                "form-1-savings": False,
                "next": "/",
            },
        )

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        receipt.refresh_from_db()
        self.assertEqual(first.item, "First updated")
        self.assertEqual(first.amount, Decimal("12.00"))
        self.assertEqual(first.date, datetime.date(2024, 2, 1))
        self.assertEqual(second.item, "Second")
        self.assertEqual(second.amount, Decimal("20.00"))
        self.assertEqual(second.notes, "")
        self.assertFalse(second.savings)
        self.assertEqual(second.date, datetime.date(2024, 2, 1))
        self.assertEqual(second.source, "New Store")
        self.assertEqual(second.location, "New Location")
        self.assertEqual(receipt.date, datetime.date(2024, 2, 1))
        self.assertEqual(receipt.source, "New Store")
        self.assertEqual(receipt.location, "New Location")

    def test_deleting_last_purchase_removes_orphaned_receipt(self):
        receipt = Receipt.objects.create(user=self.user, date=datetime.date(2024, 1, 1))
        purchase = Purchase.objects.create(
            user=self.user,
            receipt=receipt,
            item="Delete me",
            date=datetime.date(2024, 1, 1),
            category=self.category,
            subcategory=self.subcategory,
        )

        response = self.client.delete(
            reverse("purchase_delete_htmx", kwargs={"pk": purchase.pk}) + "?next=/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Receipt.objects.filter(pk=receipt.pk).exists())

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


@override_settings(STORAGES=TEST_STORAGES)
class PurchaseListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "testpass123"
        self.user = get_user_model().objects.create_user(
            username="purchase_list_user",
            email="purchase-list@example.com",
        )
        self.user.set_password(self.password)
        self.user.save()
        self.client.force_login(self.user)
        self.category = CategoryFactory(user=self.user)

    def test_purchase_list_orders_by_date_descending(self):
        older_purchase = PurchaseFactory(
            user=self.user,
            category=self.category,
            date=datetime.date(2024, 1, 1),
            item="Older purchase",
        )
        newer_purchase = PurchaseFactory(
            user=self.user,
            category=self.category,
            date=datetime.date(2024, 2, 1),
            item="Newer purchase",
        )
        other_user = get_user_model().objects.create_user(
            username="other_purchase_list_user",
            email="other-purchase-list@example.com",
        )
        other_category = CategoryFactory(user=other_user)
        PurchaseFactory(
            user=other_user,
            category=other_category,
            date=datetime.date(2024, 3, 1),
        )

        response = self.client.get(reverse("purchase_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "purchases/purchase_list.html")
        self.assertEqual(
            list(response.context["purchases"]),
            [newer_purchase, older_purchase],
        )

    def test_purchase_list_paginates_to_100_items_per_page(self):
        for index in range(101):
            PurchaseFactory(
                user=self.user,
                category=self.category,
                subcategory=None,
                item=f"Purchase {index}",
                date=datetime.date(2024, 1, 1) + datetime.timedelta(days=index),
            )

        first_page_response = self.client.get(reverse("purchase_list"))
        second_page_response = self.client.get(reverse("purchase_list"), {"page": 2})

        self.assertEqual(first_page_response.status_code, 200)
        self.assertTrue(first_page_response.context["is_paginated"])
        self.assertEqual(first_page_response.context["paginator"].per_page, 100)
        self.assertEqual(len(first_page_response.context["purchases"]), 100)
        self.assertEqual(second_page_response.status_code, 200)
        self.assertEqual(len(second_page_response.context["purchases"]), 1)

    def test_purchase_list_pagination_links_preserve_filters(self):
        for index in range(101):
            PurchaseFactory(
                user=self.user,
                category=self.category,
                subcategory=None,
                item=f"Needle purchase {index}",
                date=datetime.date(2024, 2, 1),
            )

        response = self.client.get(
            reverse("purchase_list"),
            {"search": "needle", "category": str(self.category.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["next_page_url"],
            f"?search=needle&category={self.category.pk}&page=2",
        )
        self.assertIsNone(response.context["previous_page_url"])
        self.assertContains(
            response,
            f'href="?search=needle&amp;category={self.category.pk}&amp;page=2"',
            html=False,
        )

    def test_purchase_delete_from_last_page_redirects_to_valid_page(self):
        for index in range(101):
            PurchaseFactory(
                user=self.user,
                category=self.category,
                subcategory=None,
                item=f"Purchase {index}",
                date=datetime.date(2024, 1, 1) + datetime.timedelta(days=index),
            )

        page_two_url = f'{reverse("purchase_list")}?search=purchase&page=2'
        page_two_response = self.client.get(page_two_url)
        purchase = page_two_response.context["purchases"][0]
        return_url = f'{reverse("purchase_list")}?search=purchase'

        self.assertContains(
            page_two_response,
            f'hx-get=\'{reverse("purchase_delete_htmx", kwargs={"pk": purchase.pk})}'
            f'?next={quote(return_url, safe="")}\'',
            html=False,
        )

        delete_url = (
            f'{reverse("purchase_delete_htmx", kwargs={"pk": purchase.pk})}'
            f'?next={quote(return_url, safe="")}'
        )
        response = self.client.delete(delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], return_url)

        redirected_response = self.client.get(response["HX-Redirect"])

        self.assertEqual(redirected_response.status_code, 200)
        self.assertEqual(redirected_response.context["page_obj"].number, 1)
        self.assertEqual(len(redirected_response.context["purchases"]), 100)

    def test_purchase_list_filters_by_dates_and_search(self):
        filtered_purchases = [
            PurchaseFactory(
                user=self.user,
                category=self.category,
                item="Needle item",
                source="Regular source",
                location="Regular location",
                date=datetime.date(2024, 2, 10),
            ),
            PurchaseFactory(
                user=self.user,
                category=self.category,
                item="Other item",
                source="Needle source",
                location="Regular location",
                date=datetime.date(2024, 2, 11),
            ),
            PurchaseFactory(
                user=self.user,
                category=self.category,
                item="Other item",
                source="Regular source",
                location="Needle location",
                date=datetime.date(2024, 2, 12),
            ),
        ]
        out_of_range_purchase = PurchaseFactory(
            user=self.user,
            category=self.category,
            item="Needle item outside range",
            source="Needle source outside range",
            location="Needle location outside range",
            date=datetime.date(2024, 1, 15),
        )

        matching_purchase_ids = [purchase.pk for purchase in filtered_purchases]
        Purchase.objects.filter(pk__in=matching_purchase_ids).update(
            created_at=timezone.make_aware(datetime.datetime(2024, 3, 31, 23, 59, 59))
        )
        Purchase.objects.filter(pk=out_of_range_purchase.pk).update(
            created_at=timezone.make_aware(datetime.datetime(2024, 4, 1, 0, 0, 0))
        )

        response = self.client.get(
            reverse("purchase_list"),
            {
                "purchase_date_from": "2024-02-01",
                "purchase_date_to": "2024-02-29",
                "date_added_from": "2024-03-01",
                "date_added_to": "2024-03-31",
                "search": "needle",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["purchases"]),
            list(reversed(filtered_purchases)),
        )

    def test_purchase_list_filters_by_category_with_used_category_options(self):
        other_category = CategoryFactory(user=self.user, name="Other category")
        unused_category = CategoryFactory(user=self.user, name="Unused category")
        matching_purchase = PurchaseFactory(
            user=self.user,
            category=self.category,
            item="Matching purchase",
            date=datetime.date(2024, 2, 10),
        )
        non_matching_purchase = PurchaseFactory(
            user=self.user,
            category=other_category,
            item="Non matching purchase",
            date=datetime.date(2024, 2, 11),
        )

        response = self.client.get(
            reverse("purchase_list"),
            {"category": str(self.category.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["purchases"]),
            [matching_purchase],
        )
        self.assertEqual(
            list(response.context["filter_categories"]),
            [self.category, other_category],
        )
        self.assertNotIn(unused_category, response.context["filter_categories"])
        self.assertContains(
            response,
            f'<option value="{self.category.pk}" selected>{self.category.name}</option>',
            html=True,
        )
        self.assertContains(
            response,
            f'<option value="{other_category.pk}">{other_category.name}</option>',
            html=True,
        )
        self.assertNotContains(response, unused_category.name)
        self.assertNotIn(non_matching_purchase, response.context["purchases"])

    def test_purchase_list_modal_links_preserve_filters(self):
        purchase = PurchaseFactory(
            user=self.user,
            category=self.category,
            item="Needle purchase",
            date=datetime.date(2024, 2, 10),
        )
        filtered_url = (
            f'{reverse("purchase_list")}?purchase_date_from=2024-02-01'
            f"&purchase_date_to=2024-02-29&search=needle&category={self.category.pk}"
        )
        encoded_next = quote(filtered_url, safe="")

        response = self.client.get(filtered_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'hx-get=\'{reverse("purchase_edit_htmx", kwargs={"pk": purchase.pk})}?next={encoded_next}\'',
            html=False,
        )
        self.assertContains(
            response,
            f'hx-get=\'{reverse("purchase_delete_htmx", kwargs={"pk": purchase.pk})}?next={encoded_next}\'',
            html=False,
        )

    def test_purchase_delete_modal_preserves_filtered_redirect(self):
        purchase = PurchaseFactory(
            user=self.user,
            category=self.category,
            item="Delete me",
        )
        filtered_url = (
            f'{reverse("purchase_list")}?purchase_date_from=2024-02-01'
            f"&purchase_date_to=2024-02-29&search=needle&category={self.category.pk}"
        )
        encoded_next = quote(filtered_url, safe="")

        response = self.client.get(
            reverse("purchase_delete_htmx", kwargs={"pk": purchase.pk}),
            {"next": filtered_url},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'hx-delete=\'{reverse("purchase_delete_htmx", kwargs={"pk": purchase.pk})}?next={encoded_next}\'',
            html=False,
        )

@override_settings(STORAGES=TEST_STORAGES)
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




@override_settings(STORAGES=TEST_STORAGES)
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


@override_settings(STORAGES=TEST_STORAGES)
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
        self.assertIsNotNone(purchase.receipt_id)
        self.assertEqual(purchase.receipt.source, "Netflix Inc")
        self.assertEqual(purchase.receipt.location, "Online")

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

    def test_recurring_purchase_add_uses_all_edited_details(self):
        """Editable row details are retained when creating the monthly purchase."""
        YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1),
        )
        recurring = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item="Internet",
            amount=Decimal("75.00"),
            source="Original source",
            location="Original location",
            notes="Original notes",
        )

        response = self.client.post(
            reverse("recurring_purchase_add_to_month", kwargs={"year": 2024, "month": 1}),
            self._build_add_to_month_post_data(
                [
                    {
                        "recurring": recurring,
                        "date": "2024-01-22",
                        "amount": "82.50",
                        "source": "Edited source",
                        "location": "Edited location",
                        "category": str(self.category.id),
                        "notes": "Edited notes",
                    }
                ]
            ),
        )

        self.assertEqual(response.status_code, 200)
        purchase = Purchase.objects.get(user=self.user, recurring_purchase=recurring)
        self.assertEqual(purchase.date, datetime.date(2024, 1, 22))
        self.assertEqual(purchase.amount, Decimal("82.50"))
        self.assertEqual(purchase.source, "Edited source")
        self.assertEqual(purchase.location, "Edited location")
        self.assertEqual(purchase.category, self.category)
        self.assertEqual(purchase.notes, "Edited notes")
        self.assertEqual(purchase.receipt.date, datetime.date(2024, 1, 22))
        self.assertEqual(purchase.receipt.source, "Edited source")
        self.assertEqual(purchase.receipt.location, "Edited location")

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

    def test_recurring_purchase_selected_rows_get_distinct_receipts(self):
        """Test each selected recurring purchase is grouped under its own receipt."""
        YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1),
        )
        recurring1 = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item="Netflix",
            amount=Decimal("15.99"),
        )
        recurring2 = RecurringPurchaseFactory(
            user=self.user,
            category=self.category,
            item="Spotify",
            amount=Decimal("9.99"),
        )

        response = self.client.post(
            reverse("recurring_purchase_add_to_month", kwargs={"year": 2024, "month": 1}),
            self._build_add_to_month_post_data(
                [
                    {"recurring": recurring1, "category": str(self.category.id)},
                    {"recurring": recurring2, "category": str(self.category.id)},
                ]
            ),
        )
        self.assertEqual(response.status_code, 200)

        purchases = list(
            Purchase.objects.filter(user=self.user, item__in=["Netflix", "Spotify"]).order_by("item")
        )
        self.assertEqual(len(purchases), 2)
        self.assertIsNotNone(purchases[0].receipt_id)
        self.assertIsNotNone(purchases[1].receipt_id)
        self.assertNotEqual(purchases[0].receipt_id, purchases[1].receipt_id)

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
            '<h2>Add recurring purchases</h2>',
            html=False,
            count=1,
        )
        self.assertContains(response, 'This field is required.')
