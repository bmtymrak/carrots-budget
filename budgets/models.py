from django.db import models
from django.conf import settings

from djmoney.models.fields import MoneyField

from purchases.models import Category


class YearlyBudget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="yearly_budgets",
        null=False,
    )

    date = models.DateField(null=False, default=None, blank=False)

    def __str__(self):
        return f"{self.user}-{self.date.year}"


class MonthlyBudget(models.Model):
    monthly = models.BooleanField(null=True, blank=True, default=True)
    date = models.DateField()
    expected_income = MoneyField(
        max_digits=19, decimal_places=4, default_currency="USD", blank=True, null=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="monthly_budgets",
        null=False,
    )
    yearly_budget = models.ForeignKey(
        YearlyBudget,
        on_delete=models.CASCADE,
        related_name="monthly_budgets",
        null=False,
        default=None,
    )

    def __str__(self):
        return f"{self.date.year} - {self.date.month} - {self.user}"


class BudgetItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budget_items",
        null=False,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="budget_items",
        blank=True,
        null=False,
    )
    amount = MoneyField(
        max_digits=19, decimal_places=4, default_currency="USD", blank=True, null=True
    )
    monthly_budget = models.ForeignKey(
        MonthlyBudget,
        null=False,
        on_delete=models.CASCADE,
        related_name="budget_items",
        default=None,
    )

    yearly_budget = models.ForeignKey(
        YearlyBudget,
        null=True,
        on_delete=models.CASCADE,
        related_name="budget_items",
        default=None,
        blank=True,
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        if self.monthly_budget:
            return f"{self.category}-{self.monthly_budget.date.month}-{self.monthly_budget.date.year}"
        else:
            return f"{self.category}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["monthly_budget", "category", "user"], name="unique_budgetitem"
            )
        ]
