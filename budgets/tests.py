from django.test import TestCase
from accounts.models import CustomUser
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import YearlyBudget

from datetime import datetime

User = get_user_model()


class TestYearlyDetailView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="testemail@test.com", username="testuser", password="testpass123"
        )
        cls.yearly_budget = YearlyBudget.objects.create(
            user=cls.user, date=datetime.now()
        )

    def test_yearly_detail_view_no_data(self):
        self.client.login(email="testemail@test.com", password="testpass123")
        response = self.client.get(reverse("yearly_detail", args=[datetime.now().year]))
        self.assertEqual(response.status_code, 200)


class TestYearlyBudgetCreateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="testemail@test.com", username="testuser", password="testpass123"
        )

    def test_view_get(self):
        self.client.login(email="testemail@test.com", password="testpass123")
        response = self.client.get(reverse("yearly_create"))
        self.assertEqual(response.status_code, 200)


class TestYearlyBudgetListView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="testemail@test.com", username="testuser", password="testpass123"
        )

    def test_view_get_no_budgets(self):
        self.client.login(email="testemail@test.com", password="testpass123")
        response = self.client.get(reverse("yearly_list"))
        self.assertEqual(response.status_code, 200)

    def test_view_get_with_budgets(self):
        self.client.login(email="testemail@test.com", password="testpass123")
        self.yearly_budget = YearlyBudget.objects.create(
            user=self.user, date=datetime.now()
        )
        response = self.client.get(reverse("yearly_list"))
        self.assertEqual(response.status_code, 200)
