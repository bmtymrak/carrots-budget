import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from purchases.models import Category, Purchase
from purchases.forms import IncomeForm


User = get_user_model()


class TestPurchaseEditView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email="testuser1@test.com", username="testuser1", password="testpass123"
        )
        cls.user2 = User.objects.create_user(
            email="testuser2@test.com", username="testuser2", password="testpass123"
        )

        cls.test_category = Category.objects.create(
            name="Test Category", user=cls.user1
        )
        cls.test_purchase = Purchase.objects.create(
            item="Test Item",
            date=datetime.datetime.now(),
            user=cls.user1,
            amount=10.10,
            source="Test Source",
            location="Test Location",
            category=cls.test_category,
        )

    def test_redirect_if_logged_in(self):
        response = self.client.get(
            reverse("purchase_edit", args=[self.test_purchase.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, f"/accounts/login/?next=/purchases/{self.test_purchase.pk}/edit/"
        )

    def test_logged_in_uses_correct_template(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("purchase_edit", args=[self.test_purchase.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "purchases/purchase_edit.html")

    def test_correct_object_used(self):
        self.client.login(email="testuser1@test.com", password="testpass123")

        response = self.client.get(
            reverse("purchase_edit", args=[self.test_purchase.pk])
        )

        self.assertEqual(response.context["object"], self.test_purchase)
