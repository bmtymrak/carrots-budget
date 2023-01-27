import datetime
import json
import calendar
import time

from django.db.models.fields import DecimalField, BooleanField
from django.db import connection
from django.http.response import HttpResponseRedirect
from django.http import JsonResponse
from django.views.generic.edit import DeleteView
from purchases.forms import PurchaseForm, PurchaseFormSetReceipt
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
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

from budgets.models import MonthlyBudget, YearlyBudget, BudgetItem, Rollover
from purchases.models import Category, Purchase, Income
from budgets.forms import BudgetItemForm, BudgetItemFormset


class AddUserMixin:
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class YearlyBudgetCreateView(LoginRequiredMixin, CreateView):
    model = YearlyBudget
    fields = ["date"]
    template_name = "budgets/yearly_budget_create.html"
    success_url = reverse_lazy("purchase_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()

        return HttpResponseRedirect(self.get_success_url())


class YearlyBudgetListView(LoginRequiredMixin, ListView):
    model = YearlyBudget
    context_object_name = "yearly_budgets"
    template_name = "budgets/yearly_budget_list.html"

    def get_queryset(self):
        queryset = self.model.objects.filter(user=self.request.user).order_by("-date")
        return queryset


class YearlyBudgetDetailView(LoginRequiredMixin, DetailView):
    model = YearlyBudget
    context_object_name = "yearly_budget"
    template_name = "budgets/yearly_budget_detail.html"

    def get_object(self):
        obj = self.model.objects.get(
            user=self.request.user, date__year=self.kwargs["year"]
        )

        return obj

    def get_context_data(self, **kwargs):

        if datetime.datetime.now().year > self.object.date.year:
            ytd_month = 12

        else:
            ytd_month = self.request.GET.get("ytd", datetime.datetime.now().month)

        kwargs = super().get_context_data(**kwargs)

        purchases = Purchase.objects.filter(
            user=self.request.user,
            date__year=self.object.date.year,
        )

        purchases_uncategorized = purchases.filter(category=None)

        incomes = Income.objects.filter(
            user=self.request.user,
            date__year=self.object.date.year,
        )

        budgetitems = (
            BudgetItem.objects.filter(user=self.request.user)
            .filter(
                monthly_budget__date__year=self.object.date.year,
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
                                user=self.request.user,
                                yearly_budget__date__year=self.object.date.year - 1,
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
            BudgetItem.objects.filter(user=self.request.user)
            .filter(
                monthly_budget__date__year=self.object.date.year,
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

        savings_items = (
            BudgetItem.objects.filter(
                user=self.request.user,
                monthly_budget__date__year=self.object.date.year,
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
                                user=self.request.user,
                                yearly_budget__date__year=self.object.date.year - 1,
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
                user=self.request.user,
                monthly_budget__date__year=self.object.date.year,
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

        total_spending_spent = 0
        total_spending_remaining = 0
        total_spending_budgeted = 0
        total_spending_remaining_current_year = 0
        for item in budgetitems:
            total_spending_spent += item["spent"]
            total_spending_remaining += item["diff"]
            total_spending_budgeted += item["amount_total"]
            total_spending_remaining_current_year += item["remaining_current_year"]

        total_saved = 0
        total_savings_budgeted = 0
        total_savings_remaining = 0
        for item in savings_items:
            total_saved += item["saved"]
            total_savings_remaining += item["diff"]
            total_savings_budgeted += item["amount_total"]

        total_budgeted = total_spending_budgeted + total_savings_budgeted

        total_spent_saved = total_spending_spent + total_saved

        total_remaining = total_spending_remaining + total_savings_remaining

        total_remaining_current_year = (
            total_spending_remaining_current_year + total_savings_remaining
        )

        total_spending_spent_ytd = 0
        total_spending_remaining_ytd = 0
        total_spending_budgeted_ytd = 0
        for item in budgetitems_ytd:
            total_spending_spent_ytd += item["spent"]
            total_spending_remaining_ytd += item["diff_ytd"]
            total_spending_budgeted_ytd += item["amount_total_ytd"]

        total_saved_ytd = 0
        total_savings_budgeted_ytd = 0
        total_savings_remaining_ytd = 0
        for item in savings_items_ytd:
            total_saved_ytd += item["saved"]
            total_savings_remaining_ytd += item["diff_ytd"]
            total_savings_budgeted_ytd += item["amount_total_ytd"]

        total_budgeted_ytd = total_spending_budgeted_ytd + total_savings_budgeted_ytd

        total_spent_saved_ytd = total_spending_spent_ytd + total_saved_ytd

        total_remaining_ytd = total_spending_remaining_ytd + total_savings_remaining_ytd

        incomes = (
            Income.objects.filter(
                user=self.request.user,
                date__year=self.object.date.year,
            )
            .order_by("date")
            .select_related("category")
        )

        incomes_ytd = Income.objects.filter(
            user=self.request.user,
            date__year=self.object.date.year,
            date__month__lte=ytd_month,
        ).order_by("date")

        total_income = incomes.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        total_income_ytd = incomes_ytd.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        total_income_budgeted = incomes.filter(category=None).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        total_income_budgeted_ytd = incomes_ytd.filter(category=None).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        total_income_category = incomes.filter(~Q(category=None)).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        total_income_category_ytd = incomes_ytd.filter(~Q(category=None)).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        total_income_spent_diff = total_income["amount"] - total_spent_saved
        budgeted_income_spent_diff = total_income_budgeted["amount"] - total_spent_saved
        budgeted_income_spent_diff_ytd = (
            total_income_budgeted_ytd["amount"] - total_spent_saved_ytd
        )

        budgeted_income_diff = total_income_budgeted["amount"] - total_budgeted
        budgeted_income_diff_ytd = (
            total_income_budgeted_ytd["amount"] - total_budgeted_ytd
        )

        free_income = (
            budgetitems.filter(rollover=0).aggregate(
                amount=ExpressionWrapper(
                    Coalesce(Sum("remaining_current_year"), Value(0)),
                    output_field=DecimalField(),
                )
            )["amount"]
            + savings_items.filter(rollover=0).aggregate(
                amount=ExpressionWrapper(
                    Coalesce(Sum("diff"), Value(0)), output_field=DecimalField()
                )
            )["amount"]
        )

        rollovers = (
            Rollover.objects.filter(user=self.request.user, yearly_budget=self.object)
            .annotate(
                savings=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            budgetitems.filter(category=OuterRef("category")).values(
                                "savings"
                            )
                        ),
                        Value(True),
                    ),
                    output_field=BooleanField(),
                )
            )
            .prefetch_related("category")
        )

        rollovers_spending = rollovers.filter(savings=False).order_by("category__name")
        rollovers_savings = rollovers.filter(savings=True).order_by("category__name")

        kwargs.update(
            {
                "budget_items_combined": budget_items_combined,
                "savings_items_combined": savings_items_combined,
                "incomes": incomes,
                "total_spending_spent": total_spending_spent,
                "total_spending_remaining": total_spending_remaining,
                "total_spending_budgeted": total_spending_budgeted,
                "total_spending_spent_ytd": total_spending_spent_ytd,
                "total_spending_remaining_ytd": total_spending_remaining_ytd,
                "total_spending_budgeted_ytd": total_spending_budgeted_ytd,
                "total_saved": total_saved,
                "total_savings_budgeted": total_savings_budgeted,
                "total_savings_remaining": total_savings_remaining,
                "total_saved_ytd": total_saved_ytd,
                "total_savings_budgeted_ytd": total_savings_budgeted_ytd,
                "total_savings_remaining_ytd": total_savings_remaining_ytd,
                "total_spent_saved": total_spent_saved,
                "total_budgeted": total_budgeted,
                "total_remaining": total_remaining,
                "total_remaining_current_year": total_remaining_current_year,
                "total_spent_saved_ytd": total_spent_saved_ytd,
                "total_budgeted_ytd": total_budgeted_ytd,
                "total_remaining_ytd": total_remaining_ytd,
                "total_income": total_income,
                "total_income_ytd": total_income_ytd,
                "total_income_budgeted": total_income_budgeted,
                "total_income_budgeted_ytd": total_income_budgeted_ytd,
                "total_income_category": total_income_category,
                "total_income_category_ytd": total_income_category_ytd,
                "free_income": free_income,
                "purchases_uncategorized": purchases_uncategorized,
                "rollovers_spending": rollovers_spending,
                "rollovers_savings": rollovers_savings,
                "budgeted_income_diff": budgeted_income_diff,
                "budgeted_income_diff_ytd": budgeted_income_diff_ytd,
                "total_income_spent_diff": total_income_spent_diff,
                "budgeted_income_spent_diff": budgeted_income_spent_diff,
                "budgeted_income_spent_diff_ytd": budgeted_income_spent_diff_ytd,
                "months": [
                    (calendar.month_name[month], month) for month in range(1, 13)
                ],
            }
        )

        return kwargs


class MonthlyBudgetCreateView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = MonthlyBudget
    fields = ["date", "expected_income"]
    template_name = "budgets/monthly_budget_create.html"
    success_url = reverse_lazy("monthly_budget_list")

    def form_valid(self, form):
        yearly_budget = YearlyBudget.objects.get(
            user=self.request.user, date__year=form.instance.date.year
        )
        form.instance.yearly_budget = yearly_budget
        return super().form_valid(form)


class MonthlyBudgetDetailView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = Purchase
    context_object_name = "monthly_budget"
    form_class = PurchaseForm
    template_name = "budgets/monthly_budget_detail.html"

    def get(self, request, *args, **kwargs):

        self.object = MonthlyBudget.objects.get(
            date__year=self.kwargs.get("year"),
            date__month=self.kwargs.get("month"),
            user=self.request.user,
        )

        purchase_formset = PurchaseFormSetReceipt(
            queryset=Purchase.objects.none(), form_kwargs={"user": self.request.user}
        )

        return self.render_to_response(
            self.get_context_data(purchase_formset=purchase_formset)
        )

    def post(self, request, *arg, **kwargs):
        self.object = MonthlyBudget.objects.get(
            date__year=self.kwargs.get("year"),
            date__month=self.kwargs.get("month"),
            user=self.request.user,
        )

        formset_data = self.request.POST.copy()  # Makes Querydict mutable
        formset_date = formset_data["form-0-date"]

        for key in formset_data.keys():
            if "date" in key:
                formset_data[key] = formset_date

        purchase_formset = PurchaseFormSetReceipt(
            form_kwargs={"user": self.request.user}, data=formset_data
        )

        if purchase_formset.is_valid():
            instances = purchase_formset.save(commit=False)
            source = instances[0].source
            location = instances[0].location
            for instance in instances:
                instance.user = self.request.user
                instance.source = source
                instance.location = location
                instance.save()

            return HttpResponseRedirect(self.get_success_url())

        else:
            return self.render_to_response(
                self.get_context_data(purchase_formset=purchase_formset)
            )

    def get_context_data(self, **kwargs):

        kwargs = super().get_context_data(**kwargs)

        category_purchases = Purchase.objects.filter(
            category=OuterRef("category"),
            date__year=self.object.date.year,
            date__month=self.object.date.month,
            user=self.request.user,
        ).values("category")

        category_incomes = Income.objects.filter(
            category=OuterRef("category"),
            date__year=self.object.date.year,
            date__month=self.object.date.month,
            user=self.request.user,
        ).values("category")

        budgetitems = (
            (
                BudgetItem.objects.filter(user=self.request.user)
                .filter(monthly_budget=self.object, savings=False)
                .annotate(
                    spent=ExpressionWrapper(
                        Coalesce(
                            Subquery(
                                category_purchases.annotate(total=Sum("amount")).values(
                                    "total"
                                )
                            ),
                            Value(0),
                        ),
                        output_field=DecimalField(),
                    ),
                    income=ExpressionWrapper(
                        Coalesce(
                            Subquery(
                                category_incomes.annotate(total=Sum("amount")).values(
                                    "total"
                                )
                            ),
                            Value(0),
                        ),
                        output_field=DecimalField(),
                    ),
                    diff=F("amount") - F("spent") + F("income"),
                )
            ).select_related()
        ).order_by("category__name")

        savings_items = (
            (
                BudgetItem.objects.filter(
                    user=self.request.user,
                    monthly_budget=self.object,
                    savings=True,
                ).annotate(
                    saved=ExpressionWrapper(
                        Coalesce(
                            Sum(
                                "category__purchases__amount",
                                filter=Q(
                                    category__purchases__date__month=self.object.date.month,
                                    category__purchases__date__year=self.object.date.year,
                                    category__purchases__user=self.request.user,
                                ),
                            ),
                            Value(0),
                        ),
                        output_field=DecimalField(),
                    ),
                    amount_total=Sum("amount", distinct=True),
                    diff=F("amount_total") - F("saved"),
                )
            )
            .order_by("category__name")
            .prefetch_related("category")
        )

        uncategorized_purchases_amount = Purchase.objects.filter(
            user=self.request.user,
            category__name=None,
            date__month=self.object.date.month,
            date__year=self.object.date.year,
        ).aggregate(
            amount=ExpressionWrapper(
                Coalesce(
                    Sum("amount"),
                    Value(0),
                ),
                output_field=DecimalField(),
            )
        )

        uncategorized_purchases = {
            "amount": uncategorized_purchases_amount["amount"],
            "remaining": (0 - uncategorized_purchases_amount["amount"]),
            "budgeted": 0,
        }

        total_spending_budgeted = budgetitems.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        total_spending_spent = budgetitems.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("spent"), Value(0)), output_field=DecimalField()
            )
        )

        total_spending_spent["amount"] += uncategorized_purchases_amount["amount"]

        total_spending_remaining = budgetitems.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("diff"), Value(0)), output_field=DecimalField()
            )
        )

        total_spending_remaining["amount"] -= uncategorized_purchases_amount["amount"]

        total_saved = savings_items.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("saved"), Value(0)), output_field=DecimalField()
            )
        )

        total_savings_budgeted = savings_items.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount_total"), Value(0)), output_field=DecimalField()
            )
        )

        total_savings_remaining = savings_items.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("diff"), Value(0)), output_field=DecimalField()
            )
        )

        total_budgeted = (
            total_spending_budgeted["amount"] + total_savings_budgeted["amount"]
        )

        total_spent_saved = total_spending_spent["amount"] + total_saved["amount"]

        total_remaining = (
            total_spending_remaining["amount"] + total_savings_remaining["amount"]
        )

        purchases = (
            Purchase.objects.filter(
                user=self.request.user,
                date__year=self.object.date.year,
                date__month=self.object.date.month,
            )
            .order_by("date", "source")
            .prefetch_related("category")
        )

        incomes = (
            Income.objects.filter(
                user=self.request.user,
                date__month=self.object.date.month,
                date__year=self.object.date.year,
            )
            .order_by("date", "source")
            .prefetch_related("category")
        )

        total_income = incomes.filter(category=None).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        free_income = total_income["amount"] - total_spent_saved

        kwargs.update(
            {
                "budget_items": budgetitems,
                "savings_items": savings_items,
                "purchases": purchases,
                "incomes": incomes,
                "total_budgeted": total_budgeted,
                "total_spent": total_spending_spent["amount"],
                "total_spent_saved": total_spent_saved,
                "total_spending_budgeted": total_spending_budgeted,
                "total_spending_spent": total_spending_spent,
                "total_spending_remaining": total_spending_remaining,
                "total_remaining": total_remaining,
                "total_saved": total_saved,
                "total_savings_budgeted": total_savings_budgeted,
                "total_savings_remaining": total_savings_remaining,
                "total_income": total_income,
                "free_income": free_income,
                "uncategorized_purchases": uncategorized_purchases,
                "months": [
                    (calendar.month_name[month], month) for month in range(1, 13)
                ],
            }
        )

        return kwargs

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        kwargs["instance"] = None

        return kwargs

    def get_success_url(self):
        url = reverse_lazy(
            "monthly_detail",
            kwargs={
                "year": self.kwargs["year"],
                "month": self.kwargs["month"],
            },
        )

        return url


class BudgetItemCreateView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = "budgets/budgetitem_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.cleaned_data["new_category"]:
            category, _ = Category.objects.get_or_create(
                name=form.cleaned_data["new_category"], user=self.request.user
            )

            form.instance.category = category

        BudgetItem.create_items_and_rollovers(
            self.request.user, self.kwargs["year"], form
        )

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.request.POST.get("next"):
            return self.request.POST.get("next")

        else:
            url = reverse_lazy(
                "yearly_detail",
                kwargs={"year": self.kwargs["year"]},
            )
            return url


class BudgetItemEditView(LoginRequiredMixin, AddUserMixin, UpdateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = "budgets/budgetitem_edit.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_object(self):
        obj = BudgetItem.objects.get(
            user=self.request.user,
            monthly_budget__date__year=self.kwargs["year"],
            monthly_budget__date__month=self.kwargs["month"],
            category__name=self.kwargs["category"],
        )

        return obj

    def form_valid(self, form):

        if form.cleaned_data["new_category"]:
            category, _ = Category.objects.get_or_create(
                name=form.cleaned_data["new_category"], user=self.request.user
            )

            form.instance.category = category
            form.instance.monthly_budget = MonthlyBudget.objects.get(
                user=self.request.user,
                date__year=self.kwargs["year"],
                date__month=self.kwargs["month"],
            )

        return super().form_valid(form)

    def get_success_url(self):
        url = reverse_lazy(
            "monthly_detail",
            kwargs={
                "year": self.kwargs["year"],
                "month": self.kwargs["month"],
            },
        )
        return url


class BudgetItemDetailView(LoginRequiredMixin, DetailView):
    model = BudgetItem
    context_object_name = "budget_item"
    template_name = "budgets/budgetitem_detail.html"

    def get_object(self):
        obj = BudgetItem.objects.get(
            user=self.request.user,
            monthly_budget__date__year=self.kwargs["year"],
            monthly_budget__date__month=self.kwargs["month"],
            category__name=self.kwargs["category"],
        )

        return obj

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data()

        purchases = (
            Purchase.objects.all()
            .filter(
                user=self.request.user,
                category__name=self.kwargs["category"],
                date__year=self.kwargs["year"],
                date__month=self.kwargs["month"],
            )
            .order_by("date")
        )

        kwargs.update({"purchases": purchases})

        return kwargs


class BudgetItemDeleteView(LoginRequiredMixin, DeleteView):
    model = BudgetItem
    template_name = "budgets/budgetitem_delete.html"

    def get_object(self):
        obj = self.model.objects.get(
            user=self.request.user,
            monthly_budget__date__year=self.kwargs["year"],
            monthly_budget__date__month=self.kwargs["month"],
            category__name=self.kwargs["category"],
        )

        return obj

    def delete(self, request, *args, **kwargs):

        if self.request.POST["delete-all"] == "true":
            self.model.objects.filter(
                user=self.request.user,
                monthly_budget__date__year=self.kwargs["year"],
                category__name=self.kwargs["category"],
            ).delete()

            success_url = self.get_success_url()
            return HttpResponseRedirect(success_url)

        else:
            return super().delete(self, request, *args, **kwargs)

    def get_success_url(self):
        if self.request.POST.get("next"):
            return self.request.POST.get("next")

        else:
            return reverse_lazy("yearly_list")


class BudgetItemBulkEditView(LoginRequiredMixin, TemplateView):
    template_name = "budgets/budgetitem_bulk_edit.html"

    def get(self, *args, **kwargs):
        formset = BudgetItemFormset(
            queryset=BudgetItem.objects.filter(
                user=self.request.user,
                yearly_budget=YearlyBudget.objects.get(
                    user=self.request.user, date__year=self.kwargs["year"]
                ),
                category__name=self.kwargs["category"],
            )
        )

        return self.render_to_response({"budgetitem_formset": formset})

    def post(self, *args, **kwargs):
        formset = BudgetItemFormset(data=self.request.POST)

        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save()
            return redirect(
                reverse_lazy("yearly_detail", kwargs={"year": self.kwargs["year"]})
            )


class YearlyBudgetItemDetailView(LoginRequiredMixin, TemplateView):

    template_name = "budgets/budgetitem_detail_yearly.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        year = self.kwargs["year"]
        category = self.kwargs["category"]

        purchases = (
            Purchase.objects.filter(
                user=self.request.user, date__year=year, category__name=category
            )
            .order_by("date")
            .prefetch_related("category")
        )

        incomes = Income.objects.filter(
            user=self.request.user, date__year=year, category__name=category
        )

        kwargs.update(
            {
                "category": category,
                "year": year,
                "purchases": purchases,
                "incomes": incomes,
            }
        )

        return kwargs


def rollover_update_view(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = json.load(request)
        amount = data["amount"]
        category = data["category"]
        year = data["year"]

        obj = Rollover.objects.filter(
            user=request.user, category__name=category, yearly_budget__date__year=year
        ).get()

        obj.amount = amount
        obj.save()

        return JsonResponse({"amount": amount})
