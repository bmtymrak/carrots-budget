import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from budgets.models import YearlyBudget, MonthlyBudget


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

        cls.monthly_budget_user1 = MonthlyBudget.objects.create(
            user=cls.user1,
            yearly_budget=cls.yearly_budget_user1,
            date=datetime.datetime.now(),
        )

        MonthlyBudget.objects.create(
            user=cls.user2,
            yearly_budget=cls.yearly_budget_user2,
            date=datetime.datetime.now(),
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

    def test_object_is_for_the_current_loggin_in_user(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("monthly_detail", args=[datetime.datetime.now().year, 1])
        )

        self.assertEqual(self.monthly_budget_user1, response.context["object"])

    def test_formset_in_response_context(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("monthly_detail", args=[datetime.datetime.now().year, 1])
        )

        self.assertTrue("purchase_formset" in response.context)


class TestBudgetItemCreateView(TestCase):
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

        cls.monthly_budget_user1 = MonthlyBudget.objects.create(
            user=cls.user1,
            yearly_budget=cls.yearly_budget_user1,
            date=datetime.datetime.now(),
        )

        MonthlyBudget.objects.create(
            user=cls.user2,
            yearly_budget=cls.yearly_budget_user2,
            date=datetime.datetime.now(),
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse("budgetitem_create", args=[datetime.datetime.now().year])
        )

        self.assertRedirects(
            response,
            f"/accounts/login/?next=/budgets/{datetime.datetime.now().year}/budgetitem-create",
        )

    def test_budget_item_create_uses_correct_template(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("budgetitem_create", args=[datetime.datetime.now().year])
        )

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "budgets/budgetitem_create.html")
