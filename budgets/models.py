import datetime

from django.db import models
from django.conf import settings

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not MonthlyBudget.objects.filter(yearly_budget=self, user=self.user):
            for month in range(1, 13):
                MonthlyBudget.objects.create(
                    date=datetime.date(self.date.year, month, 1),
                    user=self.user,
                    yearly_budget=self,
                )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["date", "user"], name="unique_yearlybudget")
        ]
        ordering = ["date"]


class MonthlyBudget(models.Model):
    monthly = models.BooleanField(null=True, blank=True, default=True)
    date = models.DateField()
    expected_income = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "user"], name="unique_monthlybudget"
            )
        ]


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
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, default=0
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

    savings = models.BooleanField(blank=True, null=False)

    def __str__(self):
        if self.monthly_budget:
            return f"{self.category}-{self.monthly_budget.date.month}-{self.monthly_budget.date.year}"
        else:
            return f"{self.category}"

    @classmethod
    def create_items_and_rollovers(cls, user, year, form):

        monthly_budgets = list(MonthlyBudget.objects.filter(date__year=year, user=user))

        for monthly_budget in monthly_budgets:
            cls.objects.create(
                user=user,
                category=form.instance.category,
                amount=form.instance.amount,
                monthly_budget=monthly_budget,
                yearly_budget=YearlyBudget.objects.get(user=user, date__year=year),
                savings=form.instance.savings,
            )

        Rollover.objects.create(
            user=user,
            category=form.instance.category,
            yearly_budget=YearlyBudget.objects.get(user=user, date__year=year),
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["monthly_budget", "category", "user"], name="unique_budgetitem"
            )
        ]


class Rollover(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rollovers",
        null=False,
    )

    yearly_budget = models.ForeignKey(
        YearlyBudget,
        on_delete=models.CASCADE,
        related_name="rollovers",
        blank=True,
        null=False,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="rollovers",
        blank=True,
        null=False,
    )

    amount = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, default=0
    )

    def __str__(self):
        return f"Rollover {self.yearly_budget.date.year}-{self.category}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["yearly_budget", "category", "user"], name="unique_rollover"
            )
        ]
