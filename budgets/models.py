import datetime

from django.db import models
from django.db.models import (
    Sum,
    F,
    Value,
    Q,
    OuterRef,
    Subquery,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce
from django.db.models.fields import DecimalField
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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["date", "user"], name="unique_yearlybudget")
        ]
        ordering = ["date"]

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

    def calculate_stats(self, request, purchases, incomes, ytd_month):
        data = {}
        spending_stats = self.calculate_spending(request, purchases, incomes, ytd_month)
        savings_stats = self.calculate_savings(request, purchases, incomes, ytd_month)
        income_stats = self.calculate_income(request, incomes, ytd_month)

        total_budgeted = (
            spending_stats["total_spending_budgeted"]
            + savings_stats["total_savings_budgeted"]
        )

        total_spent_saved = (
            spending_stats["total_spending_spent"] + savings_stats["total_saved"]
        )

        total_remaining = (
            spending_stats["total_spending_remaining"]
            + savings_stats["total_savings_remaining"]
        )

        total_remaining_current_year = (
            spending_stats["total_spending_remaining_current_year"]
            + savings_stats["total_savings_remaining"]
        )

        total_budgeted_ytd = (
            spending_stats["total_spending_budgeted_ytd"]
            + savings_stats["total_savings_budgeted_ytd"]
        )

        total_spent_saved_ytd = (
            spending_stats["total_spending_spent_ytd"]
            + savings_stats["total_saved_ytd"]
        )

        total_remaining_ytd = (
            spending_stats["total_spending_remaining_ytd"]
            + savings_stats["total_savings_remaining_ytd"]
        )

        total_income_spent_diff = income_stats["total_income"] - total_spent_saved
        budgeted_income_spent_diff = (
            income_stats["total_income_budgeted"] - total_spent_saved
        )
        budgeted_income_spent_diff_ytd = (
            income_stats["total_income_budgeted_ytd"] - total_spent_saved_ytd
        )

        budgeted_income_diff = income_stats["total_income_budgeted"] - total_budgeted
        budgeted_income_diff_ytd = (
            income_stats["total_income_budgeted_ytd"] - total_budgeted_ytd
        )

        free_income = (
            spending_stats["budgetitems"]
            .filter(rollover=0)
            .aggregate(
                amount=ExpressionWrapper(
                    Coalesce(Sum("remaining_current_year"), Value(0)),
                    output_field=DecimalField(),
                )
            )["amount"]
            + savings_stats["savings_items"]
            .filter(rollover=0)
            .aggregate(
                amount=ExpressionWrapper(
                    Coalesce(Sum("diff"), Value(0)), output_field=DecimalField()
                )
            )["amount"]
        )

        data.update(**spending_stats, **savings_stats, **income_stats)
        data.update(
            {
                "total_budgeted": total_budgeted,
                "total_spent_saved": total_spent_saved,
                "total_remaining": total_remaining,
                "total_remaining_current_year": total_remaining_current_year,
                "total_budgeted_ytd": total_budgeted_ytd,
                "total_spent_saved_ytd": total_spent_saved_ytd,
                "total_remaining_ytd": total_remaining_ytd,
                "total_income_spent_diff": total_income_spent_diff,
                "budgeted_income_spent_diff": budgeted_income_spent_diff,
                "budgeted_income_spent_diff_ytd": budgeted_income_spent_diff_ytd,
                "budgeted_income_diff": budgeted_income_diff,
                "budgeted_income_diff_ytd": budgeted_income_diff_ytd,
                "free_income": free_income,
            }
        )

        return data

    def calculate_spending(self, request, purchases, incomes, ytd_month):
        budgetitems = (
            BudgetItem.objects.filter(user=request.user)
            .filter(
                monthly_budget__date__year=self.date.year,
                savings=False,
            )
            .values("category__name")
            .annotate(
                spent=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            purchases.filter(category=OuterRef("category"))
                            .values("category")
                            .annotate(total=Sum("amount"))
                            .values("total")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                income=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            incomes.filter(category=OuterRef("category"))
                            .values("category")
                            .annotate(total=Sum("amount"))
                            .values("total")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                rollover=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            Rollover.objects.filter(
                                user=request.user,
                                yearly_budget__date__year=self.date.year - 1,
                                category=OuterRef("category"),
                            ).values("amount")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                amount_total=Sum("amount", distinct=False),
                diff=F("amount_total") - F("spent") + F("income") + F("rollover"),
                remaining_current_year=F("amount_total") - F("spent") + F("income"),
            )
        ).order_by("category__name")

        budgetitems_ytd = (
            BudgetItem.objects.filter(user=request.user)
            .filter(
                monthly_budget__date__year=self.date.year,
                monthly_budget__date__month__lte=ytd_month,
                savings=False,
            )
            .values("category__name")
            .annotate(
                spent=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            purchases.filter(category=OuterRef("category"))
                            .filter(date__month__lte=ytd_month)
                            .values("category")
                            .annotate(total=Sum("amount"))
                            .values("total")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                income=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            incomes.filter(category=OuterRef("category"))
                            .filter(date__month__lte=ytd_month)
                            .values("category")
                            .annotate(total=Sum("amount"))
                            .values("total")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                amount_total_ytd=Sum("amount", distinct=False),
                diff_ytd=F("amount_total_ytd") - F("spent"),
                remaining_current_year_ytd=F("amount_total_ytd")
                - F("spent")
                + F("income"),
            )
        ).order_by("category__name")

        budget_items_combined = list(
            zip(
                budgetitems.values("category__name"),
                budgetitems.values("amount_total"),
                budgetitems.values("spent"),
                budgetitems.values("diff"),
                budgetitems_ytd.values("amount_total_ytd"),
                budgetitems_ytd.values("diff_ytd"),
                budgetitems_ytd.values("spent"),
            )
        )

        total_spending_spent = 0
        total_spending_remaining = 0
        total_spending_budgeted = 0
        total_spending_remaining_current_year = 0
        for item in budgetitems:
            total_spending_spent += item["spent"]
            total_spending_remaining += item["diff"]
            total_spending_budgeted += item["amount_total"]
            total_spending_remaining_current_year += item["remaining_current_year"]

        total_spending_spent_ytd = 0
        total_spending_remaining_ytd = 0
        total_spending_budgeted_ytd = 0
        for item in budgetitems_ytd:
            total_spending_spent_ytd += item["spent"]
            total_spending_remaining_ytd += item["diff_ytd"]
            total_spending_budgeted_ytd += item["amount_total_ytd"]

        stats = {
            "budgetitems": budgetitems,
            "budget_items_combined": budget_items_combined,
            "total_spending_spent": total_spending_spent,
            "total_spending_remaining": total_spending_remaining,
            "total_spending_budgeted": total_spending_budgeted,
            "total_spending_remaining_current_year": total_spending_remaining_current_year,
            "total_spending_spent_ytd": total_spending_spent_ytd,
            "total_spending_remaining_ytd": total_spending_remaining_ytd,
            "total_spending_budgeted_ytd": total_spending_budgeted_ytd,
        }
        return stats

    def calculate_savings(self, request, purchases, incomes, ytd_month):
        savings_items = (
            BudgetItem.objects.filter(
                user=request.user,
                monthly_budget__date__year=self.date.year,
                savings=True,
            )
            .values("category__name")
            .annotate(
                saved=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            purchases.filter(category=OuterRef("category"))
                            .values("category")
                            .annotate(total=Sum("amount"))
                            .values("total")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                rollover=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            Rollover.objects.filter(
                                user=request.user,
                                yearly_budget__date__year=self.date.year - 1,
                                category=OuterRef("category"),
                            ).values("amount")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                amount_total=Sum("amount", distinct=False),
                diff=F("amount_total") - F("saved"),
            )
        ).order_by("category__name")

        savings_items_ytd = (
            BudgetItem.objects.filter(
                user=request.user,
                monthly_budget__date__year=self.date.year,
                monthly_budget__date__month__lte=ytd_month,
                savings=True,
            )
            .values("category__name")
            .annotate(
                saved=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            purchases.filter(category=OuterRef("category"))
                            .filter(date__month__lte=ytd_month)
                            .values("category")
                            .annotate(total=Sum("amount"))
                            .values("total")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                amount_total_ytd=Sum("amount", distinct=False),
                diff_ytd=F("amount_total_ytd") - F("saved"),
            )
        ).order_by("category__name")

        savings_items_combined = list(
            zip(
                savings_items.values("category__name"),
                savings_items.values("amount_total"),
                savings_items.values("saved"),
                savings_items.values("diff"),
                savings_items_ytd.values("amount_total_ytd"),
                savings_items_ytd.values("diff_ytd"),
                savings_items_ytd.values("saved"),
            )
        )

        total_saved = 0
        total_savings_budgeted = 0
        total_savings_remaining = 0
        for item in savings_items:
            total_saved += item["saved"]
            total_savings_remaining += item["diff"]
            total_savings_budgeted += item["amount_total"]

        total_saved_ytd = 0
        total_savings_budgeted_ytd = 0
        total_savings_remaining_ytd = 0
        for item in savings_items_ytd:
            total_saved_ytd += item["saved"]
            total_savings_remaining_ytd += item["diff_ytd"]
            total_savings_budgeted_ytd += item["amount_total_ytd"]

        stats = {
            "savings_items": savings_items,
            "savings_items_combined": savings_items_combined,
            "total_saved": total_saved,
            "total_savings_budgeted": total_savings_budgeted,
            "total_savings_remaining": total_savings_remaining,
            "total_saved_ytd": total_saved_ytd,
            "total_savings_budgeted_ytd": total_savings_budgeted_ytd,
            "total_savings_remaining_ytd": total_savings_remaining_ytd,
        }

        return stats

    def calculate_income(self, request, incomes, ytd_month):

        incomes_ytd = incomes.filter(
            date__month__lte=ytd_month,
        ).order_by("date")

        total_income = incomes.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )["amount"]

        total_income_ytd = incomes_ytd.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )["amount"]

        total_income_budgeted = incomes.filter(category=None).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )["amount"]

        total_income_budgeted_ytd = incomes_ytd.filter(category=None).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )["amount"]

        total_income_category = incomes.filter(~Q(category=None)).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )["amount"]

        total_income_category_ytd = incomes_ytd.filter(~Q(category=None)).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )["amount"]

        stats = {
            "total_income": total_income,
            "total_income_ytd": total_income_ytd,
            "total_income_budgeted": total_income_budgeted,
            "total_income_budgeted_ytd": total_income_budgeted_ytd,
            "total_income_category": total_income_category,
            "total_income_category_ytd": total_income_category_ytd,
        }
        return stats


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
