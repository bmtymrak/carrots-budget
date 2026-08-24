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
    ExpenseSourceCheck,
    ExpenseSourceMonth,
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
            ExpenseSourceMonth.objects.create(
                expense_source=source,
                monthly_budget=monthly_budget,
            )
        return source

    def test_monthly_page_reads_sources_without_creating_checks(self):
        self.create_source("Bank statement")
        Purchase.objects.create(
            user=self.user,
            date=datetime.date(2026, 1, 5),
            source="Unrelated purchase source",
            amount=25,
        )

        response = self.client.get(self.monthly_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["expense_source_total"], 1)
        self.assertEqual(response.context["expense_source_completed"], 0)
        self.assertContains(response, "Bank statement")
        self.assertContains(response, 'class="monthly-budget-companion"')
        self.assertContains(response, 'class="content content--monthly-budget"')
        self.assertContains(response, "+ Add note")
        self.assertNotContains(response, 'class="expense-source-note" open')
        self.assertEqual(ExpenseSource.objects.count(), 1)
        self.assertEqual(ExpenseSourceCheck.objects.count(), 0)

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
        january_check = ExpenseSourceCheck.objects.get(
            monthly_budget=self.january,
            expense_source=source,
        )
        self.assertTrue(january_check.is_checked)
        self.assertIsNotNone(january_check.checked_at)
        self.assertEqual(january_check.notes, "")
        self.assertFalse(
            ExpenseSourceCheck.objects.filter(
                monthly_budget=self.february,
                expense_source=source,
            ).exists()
        )
        self.assertContains(response, "1 / 1 complete")
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
            "hx-trigger=\"change[event.target.matches('input[type=checkbox]')], submit\"",
            count=3,
        )
        self.assertNotContains(response, "from:input")

    def test_unchecking_clears_checked_timestamp(self):
        source = self.create_source("Bank statement")
        check = ExpenseSourceCheck.objects.create(
            monthly_budget=self.january,
            expense_source=source,
            is_checked=True,
            checked_at=datetime.datetime.now(datetime.timezone.utc),
        )

        response = self.client.post(
            reverse(
                "expense_source_toggle",
                kwargs={"year": 2026, "month": 1, "source_id": source.id},
            ),
            {"next": self.monthly_url()},
        )

        self.assertRedirects(response, self.monthly_url())
        check.refresh_from_db()
        self.assertFalse(check.is_checked)
        self.assertIsNone(check.checked_at)

    def test_management_create_rename_archive_and_restore(self):
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
            source.monthly_memberships.filter(monthly_budget=self.january).exists()
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

        response = self.client.post(
            self.manage_url(),
            {
                "action": "archive",
                "source_id": source.id,
                "next": self.monthly_url(),
            },
        )
        self.assertRedirects(response, self.monthly_url())
        self.assertFalse(
            source.monthly_memberships.filter(monthly_budget=self.january).exists()
        )

        response = self.client.post(
            self.manage_url(),
            {
                "action": "restore",
                "source_id": source.id,
                "next": self.monthly_url(),
            },
        )
        self.assertRedirects(response, self.monthly_url())
        self.assertTrue(
            source.monthly_memberships.filter(monthly_budget=self.january).exists()
        )

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
            source.monthly_memberships.filter(monthly_budget=self.february).exists()
        )
        self.assertNotContains(self.client.get(self.monthly_url(month=1)), source.name)
        self.assertContains(self.client.get(self.monthly_url(month=2)), source.name)
        self.assertNotContains(self.client.get(self.monthly_url(month=3)), source.name)

    def test_source_can_be_used_in_january_skipped_in_february_and_used_in_march(self):
        source = self.create_source("Seasonal account", months=(1, 2))
        checked_at = datetime.datetime(2026, 1, 20, 15, 30, tzinfo=datetime.timezone.utc)
        ExpenseSourceCheck.objects.create(
            monthly_budget=self.january,
            expense_source=source,
            is_checked=True,
            checked_at=checked_at,
            notes="January reconciliation complete",
        )

        response = self.client.post(
            self.manage_url(month=2),
            {
                "action": "archive",
                "source_id": source.id,
                "next": self.monthly_url(month=2),
            },
        )

        self.assertRedirects(response, self.monthly_url(month=2))
        january_response = self.client.get(self.monthly_url(month=1))
        self.assertContains(january_response, source.name)
        self.assertContains(january_response, "January reconciliation complete")
        self.assertEqual(january_response.context["expense_source_completed"], 1)
        self.assertNotContains(self.client.get(self.monthly_url(month=2)), source.name)
        self.assertNotContains(self.client.get(self.monthly_url(month=3)), source.name)

        restore_response = self.client.post(
            self.manage_url(month=3),
            {
                "action": "restore",
                "source_id": source.id,
                "next": self.monthly_url(month=3),
            },
        )

        self.assertRedirects(restore_response, self.monthly_url(month=3))
        self.assertNotContains(self.client.get(self.monthly_url(month=2)), source.name)
        self.assertContains(self.client.get(self.monthly_url(month=3)), source.name)
        self.assertEqual(
            list(
                source.monthly_memberships.order_by("monthly_budget__date")
                .values_list("monthly_budget__date", flat=True)
            ),
            [
                self.january.date,
                datetime.date(2026, 3, 1),
            ],
        )

    def test_archiving_hides_state_from_the_archive_month(self):
        source = self.create_source("Current month account", months=(1, 2))
        ExpenseSourceCheck.objects.create(
            monthly_budget=self.february,
            expense_source=source,
            is_checked=True,
            checked_at=datetime.datetime.now(datetime.timezone.utc),
            notes="This state remains stored but is no longer on the checklist",
        )

        self.client.post(
            self.manage_url(month=2),
            {
                "action": "archive",
                "source_id": source.id,
                "next": self.monthly_url(month=2),
            },
        )

        response = self.client.get(self.monthly_url(month=2))
        self.assertNotContains(response, source.name)
        self.assertTrue(
            ExpenseSourceCheck.objects.filter(
                monthly_budget=self.february,
                expense_source=source,
                notes__startswith="This state remains stored",
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
        january_check = ExpenseSourceCheck.objects.get(
            monthly_budget=self.january,
            expense_source=source,
        )
        original_checked_at = january_check.checked_at

        second_response = self.client.post(
            toggle_url,
            {
                "is_checked": "on",
                "notes": "Waiting for one pending charge",
                "next": self.monthly_url(),
            },
            HTTP_HX_REQUEST="true",
        )
        january_check.refresh_from_db()

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(january_check.notes, "Waiting for one pending charge")
        self.assertEqual(january_check.checked_at, original_checked_at)
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
        self.assertEqual(february_response.context["expense_source_completed"], 0)

    def test_cannot_manage_or_toggle_another_users_source(self):
        other_source = self.create_source(
            "Other bank statement",
            user=self.other_user,
        )

        manage_response = self.client.post(
            self.manage_url(),
            {
                "action": "archive",
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
            other_source.monthly_memberships.filter(
                monthly_budget__date=datetime.date(2026, 1, 1)
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
