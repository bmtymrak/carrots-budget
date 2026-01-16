import datetime
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from purchases.models import RecurringPurchase, Purchase, Category
from purchases.forms import RecurringPurchaseForm
from budgets.models import YearlyBudget, MonthlyBudget
from purchases.tests.factories import (
    UserFactory,
    CategoryFactory,
    RecurringPurchaseFactory,
)


User = get_user_model()


class RecurringPurchaseModelTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user)

    def test_create_recurring_purchase(self):
        """Test creating a recurring purchase with all fields."""
        rp = RecurringPurchase.objects.create(
            user=self.user,
            name="Netflix Subscription",
            amount=Decimal("15.99"),
            category=self.category,
            source="Netflix",
            location="Online",
            notes="Monthly streaming",
            is_active=True,
        )
        self.assertEqual(rp.name, "Netflix Subscription")
        self.assertEqual(rp.amount, Decimal("15.99"))
        self.assertTrue(rp.is_active)
        self.assertEqual(str(rp), f"Netflix Subscription ({self.category.name})")

    def test_recurring_purchase_default_is_active(self):
        """Test that is_active defaults to True."""
        rp = RecurringPurchase.objects.create(
            user=self.user,
            name="Test Purchase",
            amount=Decimal("10.00"),
            category=self.category,
        )
        self.assertTrue(rp.is_active)

    def test_recurring_purchase_ordering(self):
        """Test that recurring purchases are ordered by name."""
        rp1 = RecurringPurchaseFactory(user=self.user, name="Zebra")
        rp2 = RecurringPurchaseFactory(user=self.user, name="Apple")
        rp3 = RecurringPurchaseFactory(user=self.user, name="Mango")
        
        recurring_purchases = RecurringPurchase.objects.filter(user=self.user)
        self.assertEqual(recurring_purchases[0].name, "Apple")
        self.assertEqual(recurring_purchases[1].name, "Mango")
        self.assertEqual(recurring_purchases[2].name, "Zebra")


class RecurringPurchaseFormTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user)

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            "name": "Gym Membership",
            "amount": "50.00",
            "category": self.category.id,
            "source": "LA Fitness",
            "location": "Main Street",
            "notes": "Monthly membership",
            "is_active": True,
        }
        form = RecurringPurchaseForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_filters_categories_by_user(self):
        """Test that form only shows categories for the current user."""
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user)
        
        form = RecurringPurchaseForm(user=self.user)
        category_ids = [c.id for c in form.fields["category"].queryset]
        
        self.assertIn(self.category.id, category_ids)
        self.assertNotIn(other_category.id, category_ids)


class RecurringPurchaseViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.category = CategoryFactory(user=self.user)

    def test_recurringpurchase_manage_get(self):
        """Test GET request to manage recurring purchases modal."""
        rp = RecurringPurchaseFactory(user=self.user)
        response = self.client.get(
            reverse("recurringpurchase_manage"),
            {"next": "/"}
        )
        self.assertEqual(response.status_code, 200)
        # Check that the response context contains what we expect
        self.assertIn("form", response.context)
        self.assertIn("recurring_purchases", response.context)
        # Check that our recurring purchase is in the queryset
        recurring_purchases = list(response.context["recurring_purchases"])
        self.assertIn(rp, recurring_purchases)

    def test_recurringpurchase_manage_post_creates_purchase(self):
        """Test POST request to create a new recurring purchase."""
        response = self.client.post(
            reverse("recurringpurchase_manage"),
            {
                "name": "New Subscription",
                "amount": "25.00",
                "category": self.category.id,
                "source": "Test Source",
                "location": "Test Location",
                "notes": "Test notes",
                "is_active": True,
                "next": "/",
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            RecurringPurchase.objects.filter(
                user=self.user,
                name="New Subscription"
            ).exists()
        )

    def test_recurringpurchase_edit_get(self):
        """Test GET request to edit recurring purchase modal."""
        rp = RecurringPurchaseFactory(user=self.user)
        response = self.client.get(
            reverse("recurringpurchase_edit", kwargs={"pk": rp.pk}),
            {"next": "/"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Recurring Purchase")
        self.assertContains(response, rp.name)

    def test_recurringpurchase_edit_post_updates_purchase(self):
        """Test POST request to update a recurring purchase."""
        rp = RecurringPurchaseFactory(user=self.user, name="Old Name")
        response = self.client.post(
            reverse("recurringpurchase_edit", kwargs={"pk": rp.pk}),
            {
                "name": "Updated Name",
                "amount": "30.00",
                "category": self.category.id,
                "source": "Updated Source",
                "location": "Updated Location",
                "notes": "Updated notes",
                "is_active": False,
                "next": "/",
            }
        )
        self.assertEqual(response.status_code, 200)
        rp.refresh_from_db()
        self.assertEqual(rp.name, "Updated Name")
        self.assertFalse(rp.is_active)

    def test_recurringpurchase_delete_get(self):
        """Test GET request to delete confirmation modal."""
        rp = RecurringPurchaseFactory(user=self.user)
        response = self.client.get(
            reverse("recurringpurchase_delete", kwargs={"pk": rp.pk}),
            {"next": "/"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm Delete")
        self.assertContains(response, rp.name)

    def test_recurringpurchase_delete_deletes_purchase(self):
        """Test DELETE request actually deletes the recurring purchase."""
        rp = RecurringPurchaseFactory(user=self.user)
        rp_id = rp.id
        
        response = self.client.delete(
            reverse("recurringpurchase_delete", kwargs={"pk": rp.pk}) + "?next=/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            RecurringPurchase.objects.filter(id=rp_id).exists()
        )

    def test_user_cannot_access_other_users_recurring_purchase(self):
        """Test that users can't edit other users' recurring purchases."""
        other_user = UserFactory()
        other_rp = RecurringPurchaseFactory(user=other_user)
        
        with self.assertRaises(RecurringPurchase.DoesNotExist):
            self.client.get(
                reverse("recurringpurchase_edit", kwargs={"pk": other_rp.pk}),
                {"next": "/"}
            )


class RecurringPurchaseAddToMonthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.category = CategoryFactory(user=self.user)
        
        # Create yearly budget - this automatically creates monthly budgets
        self.yearly_budget = YearlyBudget.objects.create(
            user=self.user,
            date=datetime.date(2024, 1, 1)
        )
        # Get the auto-created monthly budget for March
        self.monthly_budget = MonthlyBudget.objects.get(
            user=self.user,
            yearly_budget=self.yearly_budget,
            date__month=3
        )

    def test_add_to_month_get_shows_recurring_purchases(self):
        """Test GET request shows list of recurring purchases."""
        rp1 = RecurringPurchaseFactory(user=self.user, is_active=True)
        rp2 = RecurringPurchaseFactory(user=self.user, is_active=True)
        rp3 = RecurringPurchaseFactory(user=self.user, is_active=False)
        
        response = self.client.get(
            reverse("recurringpurchase_add_to_month"),
            {
                "monthly_budget_id": self.monthly_budget.id,
                "next": "/"
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, rp1.name)
        self.assertContains(response, rp2.name)
        # Inactive purchases should not be shown
        self.assertNotContains(response, rp3.name)

    def test_add_to_month_post_creates_purchases(self):
        """Test POST request creates Purchase objects from recurring purchases."""
        rp1 = RecurringPurchaseFactory(
            user=self.user,
            name="Subscription 1",
            amount=Decimal("10.00"),
            category=self.category,
            source="Source 1",
            location="Location 1",
            is_active=True
        )
        rp2 = RecurringPurchaseFactory(
            user=self.user,
            name="Subscription 2",
            amount=Decimal("20.00"),
            category=self.category,
            source="Source 2",
            location="Location 2",
            is_active=True
        )
        
        response = self.client.post(
            reverse("recurringpurchase_add_to_month"),
            {
                "monthly_budget_id": self.monthly_budget.id,
                f"recurring_purchase_{rp1.id}": "1",
                f"amount_{rp1.id}": "10.00",
                f"source_{rp1.id}": "Source 1",
                f"location_{rp1.id}": "Location 1",
                f"notes_{rp1.id}": "",
                f"recurring_purchase_{rp2.id}": "1",
                f"amount_{rp2.id}": "20.00",
                f"source_{rp2.id}": "Source 2",
                f"location_{rp2.id}": "Location 2",
                f"notes_{rp2.id}": "",
                "next": "/",
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that purchases were created
        purchases = Purchase.objects.filter(user=self.user)
        self.assertEqual(purchases.count(), 2)
        
        # Verify purchase details
        p1 = Purchase.objects.get(item="Subscription 1")
        self.assertEqual(p1.amount, Decimal("10.00"))
        self.assertEqual(p1.source, "Source 1")
        self.assertEqual(p1.location, "Location 1")
        self.assertEqual(p1.category, self.category)
        self.assertEqual(p1.date, datetime.date(2024, 3, 1))

    def test_add_to_month_with_custom_values(self):
        """Test that custom amounts/source/location override defaults."""
        rp = RecurringPurchaseFactory(
            user=self.user,
            name="Subscription",
            amount=Decimal("10.00"),
            source="Original Source",
            location="Original Location",
            category=self.category,
            is_active=True
        )
        
        response = self.client.post(
            reverse("recurringpurchase_add_to_month"),
            {
                "monthly_budget_id": self.monthly_budget.id,
                f"recurring_purchase_{rp.id}": "1",
                f"amount_{rp.id}": "15.00",  # Custom amount
                f"source_{rp.id}": "Custom Source",  # Custom source
                f"location_{rp.id}": "Custom Location",  # Custom location
                f"notes_{rp.id}": "Custom notes",
                "next": "/",
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that purchase was created with custom values
        p = Purchase.objects.get(item="Subscription")
        self.assertEqual(p.amount, Decimal("15.00"))
        self.assertEqual(p.source, "Custom Source")
        self.assertEqual(p.location, "Custom Location")
        self.assertEqual(p.notes, "Custom notes")

    def test_add_to_month_respects_selection(self):
        """Test that only selected recurring purchases are added."""
        rp1 = RecurringPurchaseFactory(user=self.user, name="Selected", is_active=True, category=self.category)
        rp2 = RecurringPurchaseFactory(user=self.user, name="Not Selected", is_active=True, category=self.category)
        
        response = self.client.post(
            reverse("recurringpurchase_add_to_month"),
            {
                "monthly_budget_id": self.monthly_budget.id,
                f"recurring_purchase_{rp1.id}": "1",  # Only rp1 is checked
                f"amount_{rp1.id}": str(rp1.amount),
                f"source_{rp1.id}": rp1.source,
                f"location_{rp1.id}": rp1.location,
                f"notes_{rp1.id}": rp1.notes,
                # rp2 is not included (checkbox unchecked)
                "next": "/",
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Only one purchase should be created
        self.assertEqual(Purchase.objects.filter(user=self.user).count(), 1)
        self.assertTrue(Purchase.objects.filter(item="Selected").exists())
        self.assertFalse(Purchase.objects.filter(item="Not Selected").exists())

    def test_add_to_month_detects_duplicates(self):
        """Test that duplicate detection works correctly."""
        # Create a recurring purchase
        rp = RecurringPurchaseFactory(
            user=self.user,
            name="Netflix",
            amount=Decimal("15.99"),
            category=self.category,
            is_active=True
        )
        
        # Add it to the month once
        Purchase.objects.create(
            user=self.user,
            item="Netflix",
            date=datetime.date(2024, 3, 1),
            amount=Decimal("15.99"),
            source="Netflix Inc",
            category=self.category,
        )
        
        # Try to get the add modal again - should show it as already added
        response = self.client.get(
            reverse("recurringpurchase_add_to_month"),
            {
                "monthly_budget_id": self.monthly_budget.id,
                "next": "/"
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All recurring purchases have already been added")
        self.assertIn("all_added", response.context)
        self.assertTrue(response.context["all_added"])


class RecurringPurchaseAdminTests(TestCase):
    def setUp(self):
        self.user = UserFactory(is_staff=True, is_superuser=True)
        self.client = Client()
        self.client.force_login(self.user)

    def test_recurringpurchase_in_admin(self):
        """Test that RecurringPurchase is registered in admin."""
        from django.contrib import admin
        from purchases.models import RecurringPurchase
        self.assertIn(RecurringPurchase, admin.site._registry)
