import datetime
from urllib.parse import quote

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from budgets.models import (
    YearlyBudget,
    MonthlyBudget,
    BudgetItem,
    Rollover,
    ExpenseSource,
    MonthlyExpenseSource,
)
from purchases.models import Category, Purchase, Receipt, Subcategory
from budgets.forms import BudgetItemForm
from .factories import (
    YearlyBudgetFactory,
    MonthlyBudgetFactory,
    BudgetItemFactory,
    RolloverFactory,
)
from purchases.tests.factories import CategoryFactory, PurchaseFactory, IncomeFactory


User = get_user_model()


TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class TestYearlyBudgetDetailView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="testemail@test.com", username="testuser", password="testpass123"
        )
        cls.yearly_budget = YearlyBudget.objects.create(
            user=cls.user, date=datetime.datetime.now()
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse("yearly_detail", args=[datetime.datetime.now().year])
        )

        self.assertRedirects(
            response, f"/accounts/login/?next=/budgets/{datetime.datetime.now().year}"
        )

    def test_yearly_detail_uses_correct_template(self):
        self.client.login(email="testemail@test.com", password="testpass123")
        response = self.client.get(
            reverse("yearly_detail", args=[datetime.datetime.now().year])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "budgets/yearly_budget_detail.html")


class TestYearlyBudgetCreateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("yearly_list"))

        self.assertRedirects(response, "/accounts/login/?next=/budgets/")

    def test_yearly_budget_create_get(self):
        self.client.login(email="testuser1@test.com", password="testpass123")
        response = self.client.get(reverse("yearly_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h2>Create Budget</h2>", html=True)

    def test_correct_budgets_created(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.post(
            reverse("yearly_create"), {"year": datetime.date.today().year}
        )

        self.assertTrue(len(YearlyBudget.objects.all()) == 1)
        self.assertTrue(YearlyBudget.objects.all()[0].user == self.user1)
        self.assertEqual(len(MonthlyBudget.objects.filter(user=self.user1)), 12)
        self.assertEqual(
            [
                date["date"].month
                for date in MonthlyBudget.objects.filter(user=self.user1).values("date")
            ],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        )

    def test_correct_redirect_on_successful_post(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.post(
            reverse("yearly_create"), {"year": datetime.date.today().year}
        )

        self.assertRedirects(response, f"/budgets/", 200)

    def test_duplicate_yearly_budget_validation(self):
        """Test that creating a duplicate yearly budget for the same user/year shows an error"""
        self.client.login(email="testuser1@test.com", password="testpass123")
        year = 2024
        
        # Create first budget
        response = self.client.post(
            reverse("yearly_create"), {"year": year}
        )
        self.assertEqual(YearlyBudget.objects.filter(user=self.user1, date__year=year).count(), 1)
        
        # Try to create duplicate budget
        response = self.client.post(
            reverse("yearly_create"), {"year": year}
        )
        # Should not redirect (form should show error)
        self.assertEqual(response.status_code, 200)
        # Should still only have one budget
        self.assertEqual(YearlyBudget.objects.filter(user=self.user1, date__year=year).count(), 1)
        # Should show error message in form
        self.assertIn("already exists", response.content.decode())

    def test_different_users_can_create_same_year_budget(self):
        """Test that different users can create budgets for the same year"""
        year = 2024
        
        # User1 creates budget
        self.client.login(email="testuser1@test.com", password="testpass123")
        response = self.client.post(
            reverse("yearly_create"), {"year": year}
        )
        self.assertEqual(YearlyBudget.objects.filter(user=self.user1, date__year=year).count(), 1)
        
        # User2 creates budget for same year
        self.client.login(email="testuser2@test.com", password="testpass123")
        response = self.client.post(
            reverse("yearly_create"), {"year": year}
        )
        self.assertEqual(YearlyBudget.objects.filter(user=self.user2, date__year=year).count(), 1)
        
        # Both budgets should exist
        self.assertEqual(YearlyBudget.objects.filter(date__year=year).count(), 2)


class TestYearlyBudgetListView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("yearly_list"))

        self.assertRedirects(response, "/accounts/login/?next=/budgets/")

    def test_logged_in_user_with_budgets(self):
        self.client.login(email="testuser1@test.com", password="testpass123")
        self.yearly_budget = YearlyBudget.objects.create(
            user=self.user1, date=datetime.datetime.now()
        )

        response = self.client.get(reverse("yearly_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "budgets/yearly_budget_list.html")

    def test_logged_in_user_correct_template(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(reverse("yearly_list"))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "budgets/yearly_budget_list.html")

    def test_only_show_current_user_budgets(self):
        yearly_budget_user1 = YearlyBudget.objects.create(
            user=self.user1, date=datetime.datetime.now()
        )
        yearly_budget_user2 = YearlyBudget.objects.create(
            user=self.user2, date=datetime.datetime.now()
        )

        self.client.login(email="testuser1@test.com", password="testpass123")
        response = self.client.get(reverse("yearly_list"))

        self.assertTrue(yearly_budget_user1 in response.context["yearly_budgets"])
        self.assertFalse(yearly_budget_user2 in response.context["yearly_budgets"])


@override_settings(STORAGES=TEST_STORAGES)
class TestMonthlyBudgetDetailView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

        cls.yearly_budget_user1 = YearlyBudget.objects.create(
            user=cls.user1, date=datetime.datetime.now()
        )

        cls.yearly_budget_user2 = YearlyBudget.objects.create(
            user=cls.user2, date=datetime.datetime.now()
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse("monthly_detail", args=[datetime.datetime.now().year, 1])
        )
        self.assertRedirects(
            response, f"/accounts/login/?next=/budgets/{datetime.datetime.now().year}/1"
        )

    def test_montly_budget_detail_correct_template(self):

        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("monthly_detail", args=[datetime.datetime.now().year, 1])
        )

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "budgets/monthly_budget_detail.html")

    def test_object_is_for_the_current_logged_in_user(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        monthly_budget = MonthlyBudget.objects.get(
            user=self.user1, date__year=datetime.datetime.now().year, date__month=1
        )
        response = self.client.get(
            reverse("monthly_detail", args=[datetime.datetime.now().year, 1])
        )

        self.assertEqual(monthly_budget, response.context["object"])

    def test_post_groups_purchases_by_receipt_metadata(self):
        category = Category.objects.create(user=self.user1, name="Monthly category")
        subcategory = Subcategory.objects.create(user=self.user1, name="Monthly subcategory")
        year = self.yearly_budget_user1.date.year
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.post(
            reverse("monthly_detail", kwargs={"year": year, "month": 1}),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-date": f"{year}-01-01",
                "form-0-item": "Monthly purchase",
                "form-0-amount": "25.00",
                "form-0-source": "Monthly store",
                "form-0-location": "Monthly location",
                "form-0-category": category.pk,
                "form-0-subcategory": subcategory.pk,
                "form-0-notes": "Created from budget",
                "form-0-savings": False,
            },
        )

        self.assertEqual(response.status_code, 302)
        purchase = Purchase.objects.get(user=self.user1, item="Monthly purchase")
        self.assertIsNotNone(purchase.receipt_id)
        receipt = Receipt.objects.get(pk=purchase.receipt_id)
        self.assertEqual(receipt.user, self.user1)
        self.assertEqual(receipt.source, "Monthly store")
        self.assertEqual(receipt.location, "Monthly location")

    def test_formset_in_response_context(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("monthly_detail", args=[datetime.datetime.now().year, 1])
        )

        self.assertTrue("purchase_formset" in response.context)




class TestBudgetItemDetailView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

        cls.yearly_budget_user1 = YearlyBudget.objects.create(
            user=cls.user1, date=datetime.date.today()
        )

        cls.yearly_budget_user2 = YearlyBudget.objects.create(
            user=cls.user2, date=datetime.datetime.now()
        )

        cls.monthly_budget_user1 = MonthlyBudget.objects.create(
            user=cls.user1,
            yearly_budget=cls.yearly_budget_user1,
            date=datetime.datetime.now().date(),
        )

        cls.monthly_budget_user2 = MonthlyBudget.objects.create(
            user=cls.user2,
            yearly_budget=cls.yearly_budget_user2,
            date=datetime.datetime.now().date(),
        )

        cls.category_user1 = Category.objects.create(
            user=cls.user1, name="Test category"
        )

        cls.category_user2 = Category.objects.create(
            user=cls.user2, name="Test category"
        )

        BudgetItem.objects.create(
            user=cls.user1,
            category=cls.category_user1,
            amount=100,
            monthly_budget=cls.monthly_budget_user1,
            yearly_budget=cls.yearly_budget_user1,
            savings=False,
        )

        BudgetItem.objects.create(
            user=cls.user2,
            category=cls.category_user2,
            amount=100,
            monthly_budget=cls.monthly_budget_user2,
            yearly_budget=cls.yearly_budget_user2,
            savings=False,
        )

        Purchase.objects.create(
            user=cls.user1,
            date=datetime.datetime.today(),
            item="Item 1",
            category=cls.category_user1,
        )
        Purchase.objects.create(
            user=cls.user1,
            date=datetime.datetime.today(),
            item="Item 2",
            category=cls.category_user1,
        )
        Purchase.objects.create(
            user=cls.user1,
            date=datetime.datetime.today(),
            item="Item 3",
            category=cls.category_user1,
        )
        Purchase.objects.create(
            user=cls.user2,
            date=datetime.datetime.today(),
            item="Item 1",
            category=cls.category_user2,
        )
        Purchase.objects.create(
            user=cls.user2,
            date=datetime.datetime.today(),
            item="Item 2",
            category=cls.category_user2,
        )

    def test_redirect_if_not_logged_in(self):
        url = reverse(
                "budget_item_detail",
                args=[
                    datetime.datetime.now().year,
                    datetime.datetime.now().month,
                    self.category_user1.name,
                ],
            )
        response = self.client.get(url)

        expected_url = f"/accounts/login/?next={quote(url)}"
        self.assertRedirects(response, expected_url)

    def test_budget_item_create_uses_correct_template(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse(
                "budget_item_detail",
                args=[
                    datetime.datetime.now().year,
                    datetime.datetime.now().month,
                    self.category_user1.name,
                ],
            )
        )

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "budgets/budgetitem_detail.html")

    def test_correct_objects_shown(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse(
                "budget_item_detail",
                args=[
                    datetime.datetime.now().year,
                    datetime.datetime.now().month,
                    self.category_user1.name,
                ],
            )
        )

        self.assertEqual(
            response.context["object"],
            BudgetItem.objects.get(
                user=self.user1,
                category=self.category_user1,
                yearly_budget__date__year=datetime.datetime.now().year,
                monthly_budget__date__month=datetime.datetime.now().month,
            ),
        )

        self.assertEqual(len(response.context["purchases"]), 3)


class TestBudgetItemDeleteView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

        cls.yearly_budget_user1 = YearlyBudget.objects.create(
            user=cls.user1, date=datetime.date.today()
        )

        cls.yearly_budget_user2 = YearlyBudget.objects.create(
            user=cls.user2, date=datetime.datetime.now()
        )

        cls.category_user1 = Category.objects.create(
            user=cls.user1, name="Test category"
        )

        cls.category_user2 = Category.objects.create(
            user=cls.user2, name="Test category"
        )

        Purchase.objects.create(
            user=cls.user1,
            date=datetime.datetime.today(),
            item="Item 1",
            category=cls.category_user1,
        )
        Purchase.objects.create(
            user=cls.user1,
            date=datetime.datetime.today(),
            item="Item 2",
            category=cls.category_user1,
        )
        Purchase.objects.create(
            user=cls.user1,
            date=datetime.datetime.today(),
            item="Item 3",
            category=cls.category_user1,
        )
        Purchase.objects.create(
            user=cls.user2,
            date=datetime.datetime.today(),
            item="Item 1",
            category=cls.category_user2,
        )
        Purchase.objects.create(
            user=cls.user2,
            date=datetime.datetime.today(),
            item="Item 2",
            category=cls.category_user2,
        )

        data_user1 = {"category": cls.category_user1, "amount": 100}

        form_user1 = BudgetItemForm(data_user1, user=cls.user1)
        form_user1.is_valid()

        BudgetItem.create_items_and_rollovers(
            cls.user1, datetime.datetime.now().year, form_user1
        )

        data_user2 = {"category": cls.category_user2, "amount": 100}

        form_user2 = BudgetItemForm(data_user2, user=cls.user2)
        form_user2.is_valid()

        BudgetItem.create_items_and_rollovers(
            cls.user2, datetime.datetime.now().year, form_user2
        )

    def test_redirect_if_not_logged_in(self):
        url = reverse(
            "budget_item_delete",
            args=[
                datetime.datetime.now().year,
                datetime.datetime.now().month,
                self.category_user1.name,
            ],
        )
        response = self.client.get(url)

        expected_url = f"/accounts/login/?next={quote(url)}"
        self.assertRedirects(response, expected_url)

    def test_budget_item_delete_uses_correct_template(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse(
                "budget_item_delete",
                args=[
                    datetime.datetime.now().year,
                    datetime.datetime.now().month,
                    self.category_user1.name,
                ],
            )
        )

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "budgets/budgetitem_delete.html")

    def test_correct_item_deleted(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.post(
            reverse(
                "budget_item_delete",
                args=[
                    datetime.datetime.now().year,
                    datetime.datetime.now().month,
                    self.category_user1.name,
                ],
            ),
            {"delete-all": True},
        )

        self.assertEqual(BudgetItem.objects.filter(user=self.user1).count(), 0)
        self.assertEqual(Rollover.objects.filter(user=self.user1).count(), 0)
        self.assertEqual(BudgetItem.objects.filter(user=self.user2).count(), 12)
        self.assertEqual(Rollover.objects.filter(user=self.user2).count(), 1)


class YearlyBudgetViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.year = datetime.date.today().year
        self.yearly_budget = YearlyBudgetFactory(
            user=self.user,
            date=datetime.date(self.year, 1, 1)
        )

    def test_yearly_budget_list_view(self):
        response = self.client.get(reverse('yearly_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'budgets/yearly_budget_list.html')
        self.assertContains(response, str(self.year))

    def test_yearly_budget_detail_view(self):
        category = CategoryFactory(user=self.user)
        budget_item = BudgetItemFactory(
            user=self.user,
            category=category,
            yearly_budget=self.yearly_budget,
            monthly_budget=MonthlyBudgetFactory(
                user=self.user,
                yearly_budget=self.yearly_budget
            )
        )
        
        response = self.client.get(
            reverse('yearly_detail', kwargs={'year': self.year})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'budgets/yearly_budget_detail.html')
        self.assertContains(response, category.name)
        self.assertEqual(response.context["ytd_month"], datetime.datetime.now().month)
        self.assertContains(
            response,
            f'data-ytd-month="{datetime.datetime.now().month}"',
        )

    def test_yearly_budget_detail_uses_requested_ytd_month(self):
        response = self.client.get(
            reverse('yearly_detail', kwargs={'year': self.year}),
            {'ytd': '6'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["ytd_month"], 6)
        self.assertContains(response, 'data-ytd-month="6"')

    def test_yearly_budget_detail_ignores_invalid_ytd_month(self):
        response = self.client.get(
            reverse('yearly_detail', kwargs={'year': self.year}),
            {'ytd': '13'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["ytd_month"], datetime.datetime.now().month)

    def test_past_year_budget_detail_uses_december_as_ytd_month(self):
        past_year = self.year - 1
        YearlyBudgetFactory(
            user=self.user,
            date=datetime.date(past_year, 1, 1),
        )

        response = self.client.get(
            reverse('yearly_detail', kwargs={'year': past_year})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["ytd_month"], 12)
        self.assertContains(response, 'data-ytd-month="12"')

    def test_yearly_budget_create_view(self):
        next_year = self.year + 1
        response = self.client.post(
            reverse('yearly_create'),
            {'year': next_year}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            YearlyBudget.objects.filter(
                user=self.user,
                date__year=next_year
            ).exists()
        )


class MonthlyBudgetViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.year = datetime.date.today().year
        self.month = datetime.date.today().month
        self.yearly_budget = YearlyBudgetFactory(
            user=self.user,
            date=datetime.date(self.year, 1, 1)
        )
        self.monthly_budget = MonthlyBudgetFactory(
            user=self.user,
            yearly_budget=self.yearly_budget,
            date=datetime.date(self.year, self.month, 1)
        )

    def test_monthly_budget_detail_view(self):
        category = CategoryFactory(user=self.user)
        budget_item = BudgetItemFactory(
            user=self.user,
            category=category,
            monthly_budget=self.monthly_budget,
            yearly_budget=self.yearly_budget
        )
        
        response = self.client.get(
            reverse('monthly_detail', kwargs={
                'year': self.year,
                'month': self.month
            })
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'budgets/monthly_budget_detail.html')
        self.assertContains(response, category.name)

    def test_monthly_budget_detail_with_purchases(self):
        category = CategoryFactory(user=self.user)
        budget_item = BudgetItemFactory(
            user=self.user,
            category=category,
            monthly_budget=self.monthly_budget,
            yearly_budget=self.yearly_budget,
            amount=Decimal('500.00')
        )
        purchase = PurchaseFactory(
            user=self.user,
            category=category,
            date=datetime.date(self.year, self.month, 15),
            amount=Decimal('100.00')
        )
        
        response = self.client.get(
            reverse('monthly_detail', kwargs={
                'year': self.year,
                'month': self.month
            })
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '$100')
        self.assertContains(response, '$500')


class BudgetItemViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.year = datetime.date.today().year
        self.month = datetime.date.today().month
        self.yearly_budget = YearlyBudgetFactory(
            user=self.user,
            date=datetime.date(self.year, 1, 1)
        )
        self.monthly_budget = MonthlyBudgetFactory(
            user=self.user,
            yearly_budget=self.yearly_budget,
            date=datetime.date(self.year, self.month, 1)
        )
        self.category = CategoryFactory(user=self.user)

    def test_budget_item_delete_view(self):
        budget_item = BudgetItemFactory(
            user=self.user,
            category=self.category,
            monthly_budget=self.monthly_budget,
            yearly_budget=self.yearly_budget
        )
        
        response = self.client.post(
            reverse('budget_item_delete', kwargs={
                'year': self.year,
                'month': self.month,
                'category': self.category.name
            }) + f'?next={reverse("yearly_list")}'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            BudgetItem.objects.get(id=budget_item.id).amount,
            Decimal('0.00')
        )

    def test_bulk_edit_cannot_update_another_users_budget_item(self):
        other_user = get_user_model().objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
        )
        other_yearly_budget = YearlyBudgetFactory(
            user=other_user,
            date=datetime.date(self.year, 1, 1),
        )
        other_monthly_budget = MonthlyBudget.objects.get(
            yearly_budget=other_yearly_budget,
            date=self.monthly_budget.date,
        )
        other_category = CategoryFactory(user=other_user, name=self.category.name)
        foreign_budget_item = BudgetItemFactory(
            user=other_user,
            category=other_category,
            monthly_budget=other_monthly_budget,
            yearly_budget=other_yearly_budget,
            amount=Decimal("25.00"),
        )

        response = self.client.post(
            reverse(
                "budgetitem_bulk_edit_htmx",
                kwargs={"year": self.year, "category": self.category.name},
            ),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": str(foreign_budget_item.pk),
                "form-0-amount": "9999.99",
                "next": reverse("yearly_list"),
            },
        )

        self.assertEqual(response.status_code, 200)
        foreign_budget_item.refresh_from_db()
        self.assertEqual(foreign_budget_item.amount, Decimal("25.00"))



class RolloverViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.year = datetime.date.today().year
        self.yearly_budget = YearlyBudgetFactory(
            user=self.user,
            date=datetime.date(self.year, 1, 1)
        )
        self.category = CategoryFactory(user=self.user)
        self.rollover = RolloverFactory(
            user=self.user,
            yearly_budget=self.yearly_budget,
            category=self.category,
            amount=Decimal('500.00')
        )

    def test_rollover_update_view(self):
        response = self.client.post(
            reverse('rollover_update'),
            content_type='application/json',
            data={
                'amount': '600.00',
                'category': self.category.name,
                'year': self.year
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        self.rollover.refresh_from_db()
        self.assertEqual(self.rollover.amount, Decimal('600.00'))


@override_settings(STORAGES=TEST_STORAGES)
class ExpenseSourceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="expense-source-user",
            email="expense-source@test.com",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="other-expense-source-user",
            email="other-expense-source@test.com",
            password="testpass123",
        )
        YearlyBudget.objects.create(user=self.user, date=datetime.date(2026, 1, 1))
        YearlyBudget.objects.create(
            user=self.other_user,
            date=datetime.date(2026, 1, 1),
        )
        self.january = MonthlyBudget.objects.get(
            user=self.user,
            date=datetime.date(2026, 1, 1),
        )
        self.february = MonthlyBudget.objects.get(
            user=self.user,
            date=datetime.date(2026, 2, 1),
        )
        self.client.login(
            email="expense-source@test.com",
            password="testpass123",
        )

    def monthly_url(self, month=1):
        return reverse("monthly_detail", kwargs={"year": 2026, "month": month})

    def manage_url(self, month=1):
        return reverse(
            "expense_source_manage",
            kwargs={"year": 2026, "month": month},
        )

    def create_source(self, name, months=(1,), user=None):
        user = user or self.user
        source = ExpenseSource.objects.create(user=user, name=name)
        for month in months:
            monthly_budget = MonthlyBudget.objects.get(
                user=user,
                date=datetime.date(2026, month, 1),
            )
            MonthlyExpenseSource.objects.create(
                expense_source=source,
                monthly_budget=monthly_budget,
            )
        return source

    def test_monthly_page_reads_sources_without_creating_monthly_sources(self):
        self.create_source("Bank statement")
        monthly_source_count = MonthlyExpenseSource.objects.count()
        Purchase.objects.create(
            user=self.user,
            date=datetime.date(2026, 1, 5),
            source="Unrelated purchase source",
            amount=25,
        )

        response = self.client.get(self.monthly_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["expense_source_count"], 1)
        self.assertEqual(response.context["expense_source_completed_count"], 0)
        self.assertContains(response, "Bank statement")
        self.assertContains(response, 'class="monthly-budget-companion"')
        self.assertContains(response, 'class="content content--monthly-budget"')
        self.assertContains(response, "+ Add note")
        self.assertNotContains(response, 'class="expense-source-note" open')
        self.assertEqual(ExpenseSource.objects.count(), 1)
        self.assertEqual(MonthlyExpenseSource.objects.count(), monthly_source_count)

    def test_toggle_updates_only_the_requested_month(self):
        source = self.create_source("Citi card statement")

        response = self.client.post(
            reverse(
                "expense_source_toggle",
                kwargs={
                    "year": 2026,
                    "month": 1,
                    "source_id": source.id,
                },
            ),
            {"is_checked": "on", "next": self.monthly_url()},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "budgets/_expense_source_checklist.html")
        january_monthly_source = MonthlyExpenseSource.objects.get(
            monthly_budget=self.january,
            expense_source=source,
        )
        self.assertTrue(january_monthly_source.is_checked)
        self.assertIsNotNone(january_monthly_source.checked_at)
        self.assertEqual(january_monthly_source.notes, "")
        self.assertFalse(
            MonthlyExpenseSource.objects.filter(
                monthly_budget=self.february,
                expense_source=source,
            ).exists()
        )
        self.assertContains(response, "1 / 1 complete")
        self.assertNotContains(response, "Needs review")
        self.assertNotContains(response, "Complete")
        self.assertNotContains(response, "expense-source-checked-at")
        self.assertEqual(
            response.context["expense_source_next_url"],
            self.monthly_url(),
        )

    def test_each_checklist_form_listens_only_to_its_own_checkbox(self):
        for name in ("Bank statement", "Citi statement", "Discover statement"):
            self.create_source(name)

        response = self.client.get(self.monthly_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "hx-trigger=\"change[event.target.matches('input[type=checkbox]')]\"",
            count=3,
        )
        self.assertNotContains(response, "from:input")

    def test_checkbox_update_does_not_overwrite_notes(self):
        source = self.create_source("Bank statement")
        monthly_source = MonthlyExpenseSource.objects.get(
            monthly_budget=self.january,
            expense_source=source,
        )
        monthly_source.notes = "Keep this note"
        monthly_source.save(update_fields=["notes"])

        response = self.client.post(
            reverse(
                "expense_source_toggle",
                kwargs={"year": 2026, "month": 1, "source_id": source.id},
            ),
            {"is_checked": "1", "next": self.monthly_url()},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        monthly_source.refresh_from_db()
        self.assertTrue(monthly_source.is_checked)
        self.assertEqual(monthly_source.notes, "Keep this note")

    def test_note_update_does_not_change_checked_state(self):
        source = self.create_source("Bank statement")
        checked_at = datetime.datetime.now(datetime.timezone.utc)
        monthly_source = MonthlyExpenseSource.objects.get(
            monthly_budget=self.january,
            expense_source=source,
        )
        monthly_source.is_checked = True
        monthly_source.checked_at = checked_at
        monthly_source.save(update_fields=["is_checked", "checked_at"])

        response = self.client.post(
            reverse(
                "expense_source_toggle",
                kwargs={"year": 2026, "month": 1, "source_id": source.id},
            ),
            {"notes": "Saved separately", "next": self.monthly_url()},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        monthly_source.refresh_from_db()
        self.assertTrue(monthly_source.is_checked)
        self.assertEqual(monthly_source.checked_at, checked_at)
        self.assertEqual(monthly_source.notes, "Saved separately")

    def test_unchecking_clears_checked_timestamp(self):
        source = self.create_source("Bank statement")
        monthly_source = MonthlyExpenseSource.objects.get(
            monthly_budget=self.january,
            expense_source=source,
        )
        monthly_source.is_checked = True
        monthly_source.checked_at = datetime.datetime.now(datetime.timezone.utc)
        monthly_source.save(update_fields=["is_checked", "checked_at"])

        response = self.client.post(
            reverse(
                "expense_source_toggle",
                kwargs={"year": 2026, "month": 1, "source_id": source.id},
            ),
            {"is_checked": "0", "next": self.monthly_url()},
        )

        self.assertRedirects(response, self.monthly_url())
        monthly_source.refresh_from_db()
        self.assertFalse(monthly_source.is_checked)
        self.assertIsNone(monthly_source.checked_at)

    def test_management_create_rename_remove_and_add(self):
        response = self.client.post(
            self.manage_url(),
            {
                "action": "create",
                "name": "  Discover   card statement  ",
                "next": self.monthly_url(),
            },
        )
        self.assertRedirects(response, self.monthly_url())
        source = ExpenseSource.objects.get(user=self.user)
        self.assertEqual(source.name, "Discover card statement")
        self.assertTrue(
            source.monthly_sources.filter(
                monthly_budget=self.january,
                is_included=True,
            ).exists()
        )

        response = self.client.post(
            self.manage_url(),
            {
                "action": "rename",
                "source_id": source.id,
                "name": "Citi card statement",
                "next": self.monthly_url(),
            },
        )
        self.assertRedirects(response, self.monthly_url())
        source.refresh_from_db()
        self.assertEqual(source.name, "Citi card statement")

        monthly_source = source.monthly_sources.get(monthly_budget=self.january)
        original_monthly_source_id = monthly_source.pk
        checked_at = datetime.datetime.now(datetime.timezone.utc)
        monthly_source.is_checked = True
        monthly_source.checked_at = checked_at
        monthly_source.notes = "Retain this reconciliation history"
        monthly_source.save(update_fields=["is_checked", "checked_at", "notes"])

        response = self.client.post(
            self.manage_url(),
            {
                "action": "remove_from_month",
                "source_id": source.id,
                "next": self.monthly_url(),
            },
        )
        self.assertRedirects(response, self.monthly_url())
        monthly_source.refresh_from_db()
        self.assertFalse(monthly_source.is_included)

        response = self.client.post(
            self.manage_url(),
            {
                "action": "add_to_month",
                "source_id": source.id,
                "next": self.monthly_url(),
            },
        )
        self.assertRedirects(response, self.monthly_url())
        self.assertTrue(
            source.monthly_sources.filter(
                monthly_budget=self.january,
                is_included=True,
            ).exists()
        )
        monthly_source.refresh_from_db()
        self.assertEqual(monthly_source.pk, original_monthly_source_id)
        self.assertTrue(monthly_source.is_checked)
        self.assertEqual(monthly_source.checked_at, checked_at)
        self.assertEqual(monthly_source.notes, "Retain this reconciliation history")

    def test_invalid_rename_error_stays_with_the_source_row(self):
        bank_source = self.create_source("Bank statement")
        self.create_source("Card statement")

        response = self.client.post(
            self.manage_url(),
            {
                "action": "rename",
                "source_id": bank_source.id,
                "name": "Card statement",
                "next": self.monthly_url(),
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ExpenseSource.objects.filter(user=self.user).count(), 2)
        self.assertFalse(response.context["create_form"].is_bound)
        bank_source_row = next(
            source_row
            for source_row in response.context["included_expense_source_rows"]
            if source_row["source"].pk == bank_source.pk
        )
        self.assertTrue(bank_source_row["rename_form"].is_bound)
        self.assertEqual(
            bank_source_row["rename_form"]["name"].value(),
            "Card statement",
        )
        self.assertIn("name", bank_source_row["rename_form"].errors)
        self.assertContains(response, "You already have an expense source with this name.")

        correction_response = self.client.post(
            self.manage_url(),
            {
                "action": "rename",
                "source_id": bank_source.id,
                "name": "Savings statement",
                "next": self.monthly_url(),
            },
        )

        self.assertRedirects(correction_response, self.monthly_url())
        bank_source.refresh_from_db()
        self.assertEqual(bank_source.name, "Savings statement")
        self.assertEqual(ExpenseSource.objects.filter(user=self.user).count(), 2)

    def test_management_explains_that_rename_is_global(self):
        response = self.client.get(self.manage_url())

        self.assertContains(
            response,
            "changes its name in every month",
        )

    def test_rename_updates_the_reusable_source_in_every_month(self):
        source = self.create_source("Old statement name", months=(1, 2))

        response = self.client.post(
            self.manage_url(),
            {
                "action": "rename",
                "source_id": source.id,
                "name": "Current statement name",
                "next": self.monthly_url(),
            },
        )

        self.assertRedirects(response, self.monthly_url())
        self.assertContains(self.client.get(self.monthly_url(1)), "Current statement name")
        self.assertContains(self.client.get(self.monthly_url(2)), "Current statement name")
        self.assertNotContains(self.client.get(self.monthly_url(1)), "Old statement name")

    def test_management_rejects_unknown_actions(self):
        response = self.client.post(
            self.manage_url(),
            {"action": "unexpected", "next": self.monthly_url()},
        )

        self.assertEqual(response.status_code, 400)

    def test_management_rejects_unsupported_http_methods(self):
        response = self.client.delete(self.manage_url())

        self.assertEqual(response.status_code, 405)

    def test_expense_source_routes_reject_invalid_months(self):
        source = self.create_source("Bank statement")

        detail_response = self.client.get(
            reverse("monthly_detail", kwargs={"year": 2026, "month": 13})
        )
        manage_response = self.client.get(
            reverse("expense_source_manage", kwargs={"year": 2026, "month": 13})
        )
        toggle_response = self.client.post(
            reverse(
                "expense_source_toggle",
                kwargs={"year": 2026, "month": 13, "source_id": source.id},
            ),
            {"is_checked": "1"},
        )

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(manage_response.status_code, 404)
        self.assertEqual(toggle_response.status_code, 404)

    def test_source_added_in_february_is_not_added_to_earlier_months(self):
        response = self.client.post(
            self.manage_url(month=2),
            {
                "action": "create",
                "name": "New February account",
                "next": self.monthly_url(month=2),
            },
        )

        self.assertRedirects(response, self.monthly_url(month=2))
        source = ExpenseSource.objects.get(name="New February account")
        self.assertTrue(
            source.monthly_sources.filter(
                monthly_budget=self.february,
                is_included=True,
            ).exists()
        )
        self.assertNotContains(self.client.get(self.monthly_url(month=1)), source.name)
        self.assertContains(self.client.get(self.monthly_url(month=2)), source.name)
        self.assertNotContains(self.client.get(self.monthly_url(month=3)), source.name)

    def test_source_can_be_used_in_january_skipped_in_february_and_used_in_march(self):
        source = self.create_source("Seasonal account", months=(1, 2))
        checked_at = datetime.datetime(2026, 1, 20, 15, 30, tzinfo=datetime.timezone.utc)
        january_monthly_source = MonthlyExpenseSource.objects.get(
            monthly_budget=self.january,
            expense_source=source,
        )
        january_monthly_source.is_checked = True
        january_monthly_source.checked_at = checked_at
        january_monthly_source.notes = "January reconciliation complete"
        january_monthly_source.save(
            update_fields=["is_checked", "checked_at", "notes"]
        )

        response = self.client.post(
            self.manage_url(month=2),
            {
                "action": "remove_from_month",
                "source_id": source.id,
                "next": self.monthly_url(month=2),
            },
        )

        self.assertRedirects(response, self.monthly_url(month=2))
        january_response = self.client.get(self.monthly_url(month=1))
        self.assertContains(january_response, source.name)
        self.assertContains(january_response, "January reconciliation complete")
        self.assertEqual(
            january_response.context["expense_source_completed_count"],
            1,
        )
        self.assertNotContains(self.client.get(self.monthly_url(month=2)), source.name)
        self.assertNotContains(self.client.get(self.monthly_url(month=3)), source.name)

        add_response = self.client.post(
            self.manage_url(month=3),
            {
                "action": "add_to_month",
                "source_id": source.id,
                "next": self.monthly_url(month=3),
            },
        )

        self.assertRedirects(add_response, self.monthly_url(month=3))
        self.assertNotContains(self.client.get(self.monthly_url(month=2)), source.name)
        self.assertContains(self.client.get(self.monthly_url(month=3)), source.name)
        self.assertEqual(
            list(
                source.monthly_sources.filter(is_included=True)
                .order_by("monthly_budget__date")
                .values_list("monthly_budget__date", flat=True)
            ),
            [
                self.january.date,
                datetime.date(2026, 3, 1),
            ],
        )

    def test_removing_source_hides_monthly_source_from_checklist(self):
        source = self.create_source("Current month account", months=(1, 2))
        february_monthly_source = MonthlyExpenseSource.objects.get(
            monthly_budget=self.february,
            expense_source=source,
        )
        february_monthly_source.is_checked = True
        february_monthly_source.checked_at = datetime.datetime.now(
            datetime.timezone.utc
        )
        february_monthly_source.notes = (
            "This monthly source remains stored but is no longer on the checklist"
        )
        february_monthly_source.save(
            update_fields=["is_checked", "checked_at", "notes"]
        )

        self.client.post(
            self.manage_url(month=2),
            {
                "action": "remove_from_month",
                "source_id": source.id,
                "next": self.monthly_url(month=2),
            },
        )

        response = self.client.get(self.monthly_url(month=2))
        self.assertNotContains(response, source.name)
        self.assertTrue(
            MonthlyExpenseSource.objects.filter(
                monthly_budget=self.february,
                expense_source=source,
                is_included=False,
                notes__startswith="This monthly source remains stored",
            ).exists()
        )

    def test_notes_and_checked_timestamp_are_independent_each_month(self):
        source = self.create_source("Bank statement", months=(1, 2))
        toggle_url = reverse(
            "expense_source_toggle",
            kwargs={"year": 2026, "month": 1, "source_id": source.id},
        )

        first_response = self.client.post(
            toggle_url,
            {
                "is_checked": "on",
                "notes": "Matched through transaction 42",
                "next": self.monthly_url(),
            },
            HTTP_HX_REQUEST="true",
        )
        january_monthly_source = MonthlyExpenseSource.objects.get(
            monthly_budget=self.january,
            expense_source=source,
        )
        original_checked_at = january_monthly_source.checked_at

        second_response = self.client.post(
            toggle_url,
            {
                "is_checked": "on",
                "notes": "Waiting for one pending charge",
                "next": self.monthly_url(),
            },
            HTTP_HX_REQUEST="true",
        )
        january_monthly_source.refresh_from_db()

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(
            january_monthly_source.notes,
            "Waiting for one pending charge",
        )
        self.assertEqual(january_monthly_source.checked_at, original_checked_at)
        self.assertContains(second_response, "Waiting for one pending charge")
        self.assertContains(
            second_response,
            'class="expense-source-note" open',
        )
        self.assertContains(second_response, ">Save</button>")
        self.assertNotContains(second_response, "Save note")

        february_response = self.client.get(self.monthly_url(month=2))
        self.assertContains(february_response, source.name)
        self.assertNotContains(february_response, "Waiting for one pending charge")
        self.assertEqual(
            february_response.context["expense_source_completed_count"],
            0,
        )

    def test_cannot_manage_or_toggle_another_users_source(self):
        other_source = self.create_source(
            "Other bank statement",
            user=self.other_user,
        )

        manage_response = self.client.post(
            self.manage_url(),
            {
                "action": "remove_from_month",
                "source_id": other_source.id,
                "next": self.monthly_url(),
            },
        )
        toggle_response = self.client.post(
            reverse(
                "expense_source_toggle",
                kwargs={
                    "year": 2026,
                    "month": 1,
                    "source_id": other_source.id,
                },
            ),
            {"is_checked": "on", "next": self.monthly_url()},
        )

        self.assertEqual(manage_response.status_code, 404)
        self.assertEqual(toggle_response.status_code, 404)
        self.assertTrue(
            other_source.monthly_sources.filter(
                monthly_budget__date=datetime.date(2026, 1, 1),
                is_included=True,
            ).exists()
        )

    def test_external_next_url_is_rejected(self):
        response = self.client.post(
            self.manage_url(),
            {
                "action": "create",
                "name": "Bank statement",
                "next": "https://example.com/phishing",
            },
        )

        self.assertRedirects(response, self.monthly_url())

    def test_toggle_endpoint_cannot_be_used_as_management_return_url(self):
        source = self.create_source("Bank statement")
        toggle_url = reverse(
            "expense_source_toggle",
            kwargs={"year": 2026, "month": 1, "source_id": source.id},
        )

        response = self.client.post(
            self.manage_url(),
            {
                "action": "create",
                "name": "Citi statement",
                "next": toggle_url,
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Redirect"], self.monthly_url())
