from django.db.models.fields import DecimalField
from purchases.forms import PurchaseForm
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView
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

from .models import MonthlyBudget, YearlyBudget, BudgetItem
from purchases.models import Category, Purchase, Income
from .forms import BudgetItemForm


class AddUserMixin:
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class YearlyBudgetCreateView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = YearlyBudget
    fields = ["date"]
    template_name = "budgets/yearly_budget_create.html"
    success_url = reverse_lazy("purchase_list")


class YearlyBudgetListView(LoginRequiredMixin, ListView):
    model = YearlyBudget
    context_object_name = "yearly_budgets"
    template_name = "budgets/yearly_budget_list.html"

    def get_queryset(self):
        queryset = self.model.objects.filter(user=self.request.user)
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
        kwargs = super().get_context_data(**kwargs)

        purchases = Purchase.objects.filter(
            category=OuterRef("category"),
            user=self.request.user,
            date__year=self.object.date.year,
        ).values("category")

        incomes = Income.objects.filter(
            category=OuterRef("category"),
            user=self.request.user,
            date__year=self.object.date.year,
        )

        budgetitems = (
            BudgetItem.objects.filter(user=self.request.user)
            .filter(monthly_budget__date__year=self.object.date.year,)
            .values("category__name")
            .annotate(
                spent=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            purchases.annotate(total=Sum("amount")).values("total")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                amount_total=Sum("amount", distinct=True),
                diff=F("amount_total") - F("spent"),
            )
        ).order_by("category__name")

        total_spent = budgetitems.aggregate(Sum("spent"))
        total_remaining = budgetitems.aggregate(Sum("diff"))

        monthly_purchases = Purchase.objects.filter(
            category=OuterRef("category"),
            date__year=self.object.date.year,
            date__month=OuterRef("monthly_budget__date__month"),
            user=self.request.user,
        ).values("date__month", "category")

        monthly_budgetitems = (
            BudgetItem.objects.filter(user=self.request.user)
            .filter(monthly_budget__date__year=self.object.date.year)
            .annotate(
                spent=ExpressionWrapper(
                    Coalesce(
                        Subquery(
                            monthly_purchases.annotate(total=Sum("amount")).values(
                                "total"
                            )
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
            )
            .annotate(diff=F("amount") - F("spent"))
        ).order_by("monthly_budget__date__month", "category__name")

        # print(budgetitems)

        kwargs.update({"budget_items": budgetitems})
        kwargs.update({"monthly_budgetitems": monthly_budgetitems})
        kwargs.update({"total_spent": total_spent, "total_remaining": total_remaining})

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


class MonthlyBudgetListView(LoginRequiredMixin, ListView):
    model = MonthlyBudget
    context_object_name = "monthly_budgets"
    template_name = "budgets/monthly_budget_list.html"
    ordering = "date"

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(user=self.request.user)
        return queryset


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
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        budgetitems = (
            BudgetItem.objects.filter(user=self.request.user)
            .filter(monthly_budget=self.object)
            .annotate(
                spent=ExpressionWrapper(
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
                )
            )
        ).annotate(diff=F("amount") - F("spent"))

        total_budgeted = budgetitems.aggregate(Sum("amount"))

        total_spent_budgeted = budgetitems.aggregate(amount=Sum("spent"))

        total_remaining = budgetitems.aggregate(Sum("diff"))

        purchases = Purchase.objects.filter(
            user=self.request.user,
            date__year=self.object.date.year,
            date__month=self.object.date.month,
        ).order_by("date")

        total_spent = purchases.aggregate(amount=Sum("amount"))

        incomes = Income.objects.filter(
            user=self.request.user,
            date__month=self.object.date.month,
            date__year=self.object.date.year,
        ).order_by("date")

        total_income = incomes.aggregate(amount=Sum("amount"))

        free_income = total_income["amount"] - total_spent["amount"]

        kwargs.update(
            {
                "budget_items": budgetitems,
                "purchases": purchases,
                "incomes": incomes,
                "total_budgeted": total_budgeted,
                "total_spent": total_spent,
                "total_spent_budgeted": total_spent_budgeted,
                "total_remaining": total_remaining,
                "total_income": total_income,
                "free_income": free_income,
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
            kwargs={"year": self.kwargs["year"], "month": self.kwargs["month"],},
        )

        return url


# class MonthlyBudgetDetailView(LoginRequiredMixin, DetailView):
#     model = MonthlyBudget
#     context_object_name = "monthly_budget"
#     template_name = "budgets/monthly_budget_detail.html"

#     def get_object(self):
#         obj = self.model.objects.get(
#             date__year=self.kwargs.get("year"),
#             date__month=self.kwargs.get("month"),
#             user=self.request.user,
#         )
#         return obj

#     def get_context_data(self, **kwargs):
#         kwargs = super().get_context_data(**kwargs)

#         budgetitems = (
#             BudgetItem.objects.filter(user=self.request.user)
#             .filter(monthly_budget=self.object)
#             .annotate(
#                 spent=Coalesce(
#                     Sum(
#                         "category__purchases__amount",
#                         filter=Q(
#                             category__purchases__date__month=self.object.date.month,
#                             category__purchases__date__year=self.object.date.year,
#                             category__purchases__user=self.request.user,
#                         ),
#                     ),
#                     Value(0),
#                 )
#             )
#         ).annotate(diff=F("amount") - F("spent"))

#         purchases = Purchase.objects.filter(
#             user=self.request.user,
#             date__year=self.object.date.year,
#             date__month=self.object.date.month,
#         ).order_by("date")

#         kwargs.update({"budget_items": budgetitems, "purchases": purchases})

#         return kwargs


class BudgetItemCreateView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = "budgets/budgetitem_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        if form.cleaned_data["new_category"]:
            try:
                category = Category.objects.get(name=form.cleaned_data["new_category"])
            except:
                category = Category.objects.create(
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
            kwargs={"year": self.kwargs["year"], "month": self.kwargs["month"],},
        )

        return url


class BudgetItemEditView(LoginRequiredMixin, AddUserMixin, UpdateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = "budgets/budgetitem_edit.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
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
            try:
                category = Category.objects.get(name=form.cleaned_data["new_category"])
            except:
                category = Category.objects.create(
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
            kwargs={"year": self.kwargs["year"], "month": self.kwargs["month"],},
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

        purchases = Purchase.objects.all().filter(
            user=self.request.user,
            category__name=self.kwargs["category"],
            date__year=self.kwargs["year"],
            date__month=self.kwargs["month"],
        )

        kwargs.update({"purchases": purchases})

        return kwargs

