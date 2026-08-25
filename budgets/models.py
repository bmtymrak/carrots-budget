import datetime

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower

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
        indexes = [
            models.Index(fields=['user', 'date'], name='idx_monthly_budget_user_date'),
            models.Index(fields=['yearly_budget', 'user'], name='idx_monthly_yearly_user'),
        ]


class ExpenseSource(models.Model):
    """A reusable statement or account that a user reviews each month."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expense_sources",
    )
    name = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @staticmethod
    def normalize_name(name):
        return " ".join(name.split())

    def clean(self):
        super().clean()
        self.name = self.normalize_name(self.name)

    def save(self, *args, **kwargs):
        self.name = self.normalize_name(self.name)
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "user",
                Lower("name"),
                name="unique_expense_source_user_name",
            )
        ]
        ordering = ["name", "id"]


class MonthlyExpenseSource(models.Model):
    """A source's inclusion and review details for one monthly budget."""

    expense_source = models.ForeignKey(
        ExpenseSource,
        on_delete=models.CASCADE,
        related_name="monthly_sources",
    )
    monthly_budget = models.ForeignKey(
        MonthlyBudget,
        on_delete=models.CASCADE,
        related_name="monthly_expense_sources",
    )
    is_included = models.BooleanField(default=True)
    is_checked = models.BooleanField(default=False)
    checked_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.monthly_budget.date:%Y-%m} - {self.expense_source.name}"

    def clean(self):
        super().clean()
        validation_errors = []
        if (
            self.expense_source_id
            and self.monthly_budget_id
            and self.expense_source.user_id != self.monthly_budget.user_id
        ):
            validation_errors.append(
                "The expense source and monthly budget must belong to the same user."
            )
        if self.is_checked != (self.checked_at is not None):
            validation_errors.append(
                "Checked monthly expense sources must have a timestamp, and unchecked "
                "sources cannot retain one."
            )
        if validation_errors:
            raise ValidationError(validation_errors)

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["monthly_budget", "expense_source"],
                name="unique_monthly_expense_source",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_checked=True, checked_at__isnull=False)
                    | models.Q(is_checked=False, checked_at__isnull=True)
                ),
                name="monthly_expense_source_checked_at_matches_state",
            ),
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
        yearly_budget = YearlyBudget.objects.get(user=user, date__year=year)

        for monthly_budget in monthly_budgets:
            cls.objects.create(
                user=user,
                category=form.instance.category,
                amount=form.instance.amount,
                monthly_budget=monthly_budget,
                yearly_budget=yearly_budget,
                savings=form.instance.savings,
            )

        Rollover.objects.create(
            user=user,
            category=form.instance.category,
            yearly_budget=yearly_budget,
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["monthly_budget", "category", "user"], name="unique_budgetitem"
            )
        ]
        indexes = [
            models.Index(fields=['user', 'yearly_budget', 'savings'], name='idx_bi_user_yearly_savings'),
            models.Index(fields=['monthly_budget', 'category', 'user'], name='idx_bi_monthly_cat_user'),
            models.Index(fields=['user', 'category'], name='idx_budgetitem_user_category'),
            models.Index(fields=['yearly_budget', 'savings'], name='idx_budgetitem_yearly_savings'),
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
        indexes = [
            models.Index(fields=['user', 'yearly_budget', 'category'], name='idx_rollover_user_yearly_cat'),
            models.Index(fields=['yearly_budget', 'category'], name='idx_rollover_yearly_category'),
        ]
