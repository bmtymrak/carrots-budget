from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import MonthlyBudget, YearlyBudget, BudgetItem
from purchases.models import Category, Purchase
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

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(user=self.request.user)
        return queryset


class MonthlyBudgetDetailView(LoginRequiredMixin, DetailView):
    model = MonthlyBudget
    context_object_name = "monthly_budget"
    template_name = "budgets/monthly_budget_detail.html"

    def get_object(self):
        obj = self.model.objects.get(
            date__year=self.kwargs.get("year"),
            date__month=self.kwargs.get("month"),
            user=self.request.user,
        )
        return obj


class BudgetItemCreateView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = "budgets/budgetitem_create.html"
    # success_url = reverse_lazy("monthly_budget_list")

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

