import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from purchases.models import Category, Subcategory
from purchases.forms import (
    IncomeForm,
    PurchaseForm,
    RecurringPurchaseAddToMonthFormSet,
)
from purchases.tests.factories import RecurringPurchaseFactory

User = get_user_model()


class IncomeFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

        cls.testuser1_category = Category.objects.create(
            name="category1", user=cls.user1
        )
        cls.testuser2_category = Category.objects.create(
            name="category1", user=cls.user2
        )

    def test_only_current_user_categories_show_in_form(self):
        form = IncomeForm(user=self.user1)
        self.assertTrue(len(form.fields["category"].queryset) == 1)


class TestPurchaseForm(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

        cls.testuser1_category = Category.objects.create(
            name="category1", user=cls.user1
        )
        cls.testuser2_category = Category.objects.create(
            name="category1", user=cls.user2
        )

        cls.testuser1_subcategory = Subcategory.objects.create(
            name="subcategory1", user=cls.user1
        )
        cls.testuser2_subcategory = Subcategory.objects.create(
            name="subcategory1", user=cls.user2
        )

    def test_only_current_user_categories_show_in_form(self):
        form = PurchaseForm(user=self.user1)

        category_user = form.fields["category"].queryset[0].user

        self.assertEqual(len(form.fields["category"].queryset), 1)
        self.assertEqual(category_user, self.user1)

    def test_only_current_user_subcategories_show_in_form(self):
        form = PurchaseForm(user=self.user1)

        subcategory_user = form.fields["subcategory"].queryset[0].user

        self.assertEqual(len(form.fields["subcategory"].queryset), 1)
        self.assertEqual(subcategory_user, self.user1)


class TestRecurringPurchaseAddToMonthFormSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser3@test.com", username="testuser3", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser4@test.com", username="testuser4", password="testpass123"
        )

        cls.user1_category = Category.objects.create(name="utilities", user=cls.user1)
        cls.user1_alt_category = Category.objects.create(name="subscriptions", user=cls.user1)
        cls.user2_category = Category.objects.create(name="other-user", user=cls.user2)

        cls.recurring = RecurringPurchaseFactory(
            user=cls.user1,
            category=cls.user1_category,
            item="Netflix",
            amount=Decimal("15.99"),
            source="Netflix Inc",
            location="Online",
            notes="Monthly sub",
        )

    def _management_form_data(self, total_forms):
        return {
            "form-TOTAL_FORMS": str(total_forms),
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }

    def test_selected_purchases_include_selected_row_data(self):
        formset = RecurringPurchaseAddToMonthFormSet(
            data={
                **self._management_form_data(1),
                "form-0-selected": "on",
                "form-0-recurring_purchase_id": str(self.recurring.pk),
                "form-0-date": "2024-01-15",
                "form-0-amount": "19.99",
                "form-0-source": "Updated source",
                "form-0-location": "Updated location",
                "form-0-category": str(self.user1_alt_category.pk),
                "form-0-notes": "Updated notes",
            },
            user=self.user1,
            recurring_purchases=[self.recurring],
            purchase_date=datetime.date(2024, 1, 1),
        )

        self.assertTrue(formset.is_valid())
        self.assertEqual(len(formset.selected_purchases), 1)

        selected_purchase = formset.selected_purchases[0]
        self.assertEqual(selected_purchase["recurring_purchase"], self.recurring)
        self.assertEqual(selected_purchase["date"], datetime.date(2024, 1, 15))
        self.assertEqual(selected_purchase["amount"], Decimal("19.99"))
        self.assertEqual(selected_purchase["source"], "Updated source")
        self.assertEqual(selected_purchase["location"], "Updated location")
        self.assertEqual(selected_purchase["category"], self.user1_alt_category)
        self.assertEqual(selected_purchase["notes"], "Updated notes")

    def test_duplicate_selected_recurring_purchase_ids_raise_formset_error(self):
        formset = RecurringPurchaseAddToMonthFormSet(
            data={
                **self._management_form_data(2),
                "form-0-selected": "on",
                "form-0-recurring_purchase_id": str(self.recurring.pk),
                "form-0-date": "2024-01-15",
                "form-0-amount": "19.99",
                "form-0-category": str(self.user1_category.pk),
                "form-1-selected": "on",
                "form-1-recurring_purchase_id": str(self.recurring.pk),
                "form-1-date": "2024-01-16",
                "form-1-amount": "20.99",
                "form-1-category": str(self.user1_category.pk),
            },
            user=self.user1,
            recurring_purchases=[self.recurring, self.recurring],
            purchase_date=datetime.date(2024, 1, 1),
        )

        self.assertFalse(formset.is_valid())
        self.assertIn(
            "Recurring purchases can only be added once per submission.",
            formset.non_form_errors(),
        )

    def test_row_defaults_are_applied_on_get(self):
        formset = RecurringPurchaseAddToMonthFormSet(
            user=self.user1,
            recurring_purchases=[self.recurring],
            purchase_date=datetime.date(2024, 1, 1),
        )

        row_form = formset.forms[0]
        self.assertEqual(row_form.initial["recurring_purchase_id"], self.recurring.pk)
        self.assertEqual(row_form.initial["date"], datetime.date(2024, 1, 1))
        self.assertEqual(row_form.initial["amount"], Decimal("15.99"))
        self.assertEqual(row_form.initial["category"], self.user1_category)
        self.assertTrue(row_form.initial["selected"])

    def test_category_must_belong_to_user(self):
        formset = RecurringPurchaseAddToMonthFormSet(
            data={
                **self._management_form_data(1),
                "form-0-selected": "on",
                "form-0-recurring_purchase_id": str(self.recurring.pk),
                "form-0-date": "2024-01-15",
                "form-0-amount": "15.99",
                "form-0-category": str(self.user2_category.pk),
            },
            user=self.user1,
            recurring_purchases=[self.recurring],
            purchase_date=datetime.date(2024, 1, 1),
        )

        self.assertFalse(formset.is_valid())
        self.assertIn("category", formset.forms[0].errors)

    def test_selected_row_allows_blank_amount(self):
        formset = RecurringPurchaseAddToMonthFormSet(
            data={
                **self._management_form_data(1),
                "form-0-selected": "on",
                "form-0-recurring_purchase_id": str(self.recurring.pk),
                "form-0-date": "2024-01-15",
                "form-0-amount": "",
                "form-0-category": str(self.user1_category.pk),
            },
            user=self.user1,
            recurring_purchases=[self.recurring],
            purchase_date=datetime.date(2024, 1, 1),
        )

        self.assertTrue(formset.is_valid())
        self.assertIsNone(formset.selected_purchases[0]["amount"])

    def test_tampered_recurring_purchase_id_is_rejected(self):
        other_recurring = RecurringPurchaseFactory(
            user=self.user1,
            category=self.user1_category,
        )
        formset = RecurringPurchaseAddToMonthFormSet(
            data={
                **self._management_form_data(1),
                "form-0-selected": "on",
                "form-0-recurring_purchase_id": str(other_recurring.pk),
                "form-0-date": "2024-01-15",
                "form-0-amount": "15.99",
                "form-0-category": str(self.user1_category.pk),
            },
            user=self.user1,
            recurring_purchases=[self.recurring],
            purchase_date=datetime.date(2024, 1, 1),
        )

        self.assertFalse(formset.is_valid())
        self.assertIn("recurring_purchase_id", formset.forms[0].errors)
