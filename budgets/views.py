import datetime
import json
import calendar
import time

from django.db.models.fields import DecimalField, BooleanField
from django.db import connection
from django.http.response import HttpResponseRedirect
from django.http import JsonResponse, QueryDict
from django.views.generic.edit import DeleteView
from purchases.forms import PurchaseForm, PurchaseFormSetReceipt
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum,
    F,
    Value,
    Q,
    OuterRef,
    Subquery,
    ExpressionWrapper,
    Exists,
)
from django.db.models.functions import Coalesce

from budgets.models import MonthlyBudget, YearlyBudget, BudgetItem, Rollover
from purchases.models import Category, Purchase, Income
from budgets.forms import BudgetItemForm, BudgetItemFormset, YearlyBudgetForm
from budgets.services import BudgetService
from django_htmx.http import HttpResponseClientRedirect


class AddUserMixin:
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class YearlyBudgetListView(LoginRequiredMixin, ListView):
    model = YearlyBudget
    context_object_name = "yearly_budgets"
    template_name = "budgets/yearly_budget_list.html"

    def get_queryset(self):
        queryset = self.model.objects.filter(user=self.request.user).order_by("-date")
        return queryset

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        
        # Add summary metrics for each yearly budget
        service = BudgetService()
        yearly_budgets_with_summary = []
        
        for budget in kwargs['yearly_budgets']:
            summary = service.get_yearly_budget_summary(
                user=self.request.user,
                year=budget.date.year
            )
            budget.summary = summary
            yearly_budgets_with_summary.append(budget)
        
        kwargs['yearly_budgets'] = yearly_budgets_with_summary
        
        return kwargs


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

        if datetime.datetime.now().year > self.object.date.year:
            ytd_month = 12
        else:
            ytd_month = int(self.request.GET.get("ytd", datetime.datetime.now().month))


        service = BudgetService()
        budget_context = service.get_yearly_budget_context(
            user=self.request.user,
            year=self.object.date.year,
            ytd_month=ytd_month
        )
        
        kwargs.update(budget_context)

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

        service = BudgetService()
        budget_context = service.get_monthly_budget_context(
            user=self.request.user,
            year=self.object.date.year,
            month=self.object.date.month
        )

        kwargs.update(budget_context)

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

    def post(self, request, *args, **kwargs):

        if self.request.POST.get("delete-all", False):
            self.model.objects.filter(
                user=self.request.user,
                monthly_budget__date__year=self.kwargs["year"],
                category__name=self.kwargs["category"],
            ).delete()

            Rollover.objects.filter(
                user=self.request.user,
                category__name=self.kwargs["category"],
                yearly_budget__date__year=self.kwargs["year"],
            ).delete()

            success_url = self.get_success_url()
            return HttpResponseRedirect(success_url)

        else:
            self.object = self.get_object()
            self.object.amount = 0
            self.object.save()
            return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.request.POST.get("next"):
            return self.request.POST.get("next")

        else:
            return reverse_lazy("yearly_list")




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


@login_required
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


@login_required
def budget_create(request):

    form = YearlyBudgetForm()

    if request.method == "POST":
        next = request.POST.get("next", reverse("yearly_list"))
        form = YearlyBudgetForm(data=request.POST)
        form.instance.user = request.user

        if form.is_valid():
            form.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET.get("next", "")

    return render(
        request, "budgets/yearly_budget_create_htmx.html", {"form": form, "next": next}
    )


@login_required
def budgetitem_edit(request, year, month, category):

    budget_item = BudgetItem.objects.get(
        user=request.user,
        yearly_budget__date__year=year,
        monthly_budget__date__month=month,
        category__name=category,
    )

    form = BudgetItemForm(instance=budget_item, user=request.user)

    if request.method == "POST":
        next = request.POST.get("next")
        form = BudgetItemForm(
            instance=budget_item, data=request.POST, user=request.user
        )
        if form.is_valid():
            form.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]

    return render(
        request,
        "budgets/budgetitem_edit_htmx.html",
        {"form": form, "budget_item": budget_item, "next": next},
    )


@login_required
def budgetitem_bulk_edit(request, year, category):

    formset = BudgetItemFormset(
        queryset=BudgetItem.objects.filter(
            user=request.user,
            yearly_budget=YearlyBudget.objects.get(user=request.user, date__year=year),
            category__name=category,
        )
    )

    if request.method == "POST":
        next = request.POST.get("next")
        formset = BudgetItemFormset(data=request.POST)

        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]

    return render(
        request,
        "budgets/budgetitem_bulk_edit_htmx.html",
        {"formset": formset, "year": year, "category": category, "next": next},
    )


@login_required
def budgetitem_delete(request, year, category):

    budget_items = BudgetItem.objects.filter(
        user=request.user,
        yearly_budget__date__year=year,
        category__name=category,
    )

    next = request.GET["next"]

    if request.method == "DELETE":
        budget_items.delete()
        Rollover.objects.filter(
            user=request.user,
            category__name=category,
            yearly_budget__date__year=year,
        ).delete()
        return HttpResponseClientRedirect(next)

    return render(
        request,
        "budgets/budgetitem_delete_htmx.html",
        {
            "budget_items": budget_items,
            "year": year,
            "category": category,
            "next": next,
        },
    )


@login_required
def budget_item_create(request, year):

    if request.method == "POST":

        form = BudgetItemForm(data=request.POST, user=request.user)
        form.instance.user = request.user
        next = request.POST.get("next")

        if form.is_valid():

            if form.cleaned_data["new_category"]:
                category, _ = Category.objects.get_or_create(
                    name=form.cleaned_data["new_category"], user=request.user
                )

                form.instance.category = category

            BudgetItem.create_items_and_rollovers(request.user, year, form)

            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]
        form = BudgetItemForm(user=request.user)

    return render(
        request,
        "budgets/budgetitem_create_htmx.html",
        {"form": form, "next": next, "year": year},
    )
