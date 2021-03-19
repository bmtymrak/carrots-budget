from django.db import models
from django.conf import settings

from purchases.models import Category


class Budget(models.Model):
    monthly = models.BooleanField()
    date = models.DateField()
    expected_income = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
        null=False,
    )

    def __str__(self):
        return f"{self.date.year} - {self.date.month}"


class BudgetItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budget_items",
        null=False,
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="budget_items",
    )
    amount = models.IntegerField(blank=True, default=0)
    budget = models.ForeignKey(
        Budget, null=False, on_delete=models.CASCADE, related_name="budget_items",
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.category}-{self.budget.date.month}-{self.budget.date.year}"
