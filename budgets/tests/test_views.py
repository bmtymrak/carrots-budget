import datetime
from urllib.parse import quote

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from budgets.models import YearlyBudget, MonthlyBudget, BudgetItem, Rollover
from purchases.models import Category, Purchase
from budgets.forms import BudgetItemForm
from .factories import (
    YearlyBudgetFactory,
    MonthlyBudgetFactory,
    BudgetItemFactory,
    RolloverFactory,
)
from purchases.tests.factories import CategoryFactory, PurchaseFactory, IncomeFactory


User = get_user_model()


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

    def test_correct_budgets_created(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.post(
            reverse("yearly_create"), {"date": datetime.date.today()}
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
            reverse("yearly_create"), {"date": datetime.date.today()}
        )

        self.assertRedirects(response, f"/budgets/", 200)


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

    def test_yearly_budget_create_view(self):
        next_year = self.year + 1
        response = self.client.post(
            reverse('yearly_create'),
            {'date': f'{next_year}-01-01'}
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