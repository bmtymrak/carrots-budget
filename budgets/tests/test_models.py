import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model

from budgets.models import YearlyBudget, MonthlyBudget

User = get_user_model()


class TestYearlyBudget(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testemail@test.com", username="testuser", password="testpass123"
        )

    def test_monthly_budgets_created(self):
        self.client.login(email="testemail@test.com", password="testpass123")

        YearlyBudget.objects.create(user=self.user1, date=datetime.datetime.now())

        self.assertEqual(MonthlyBudget.objects.all().count(), 12)
