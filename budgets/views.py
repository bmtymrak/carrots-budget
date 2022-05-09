import datetime
import json
from collections import Counter

from django.db.models.fields import DecimalField, BooleanField
from django.http.response import HttpResponseRedirect
from django.http import JsonResponse
from django.views.generic.edit import DeleteView
from purchases.forms import PurchaseForm
from django.shortcuts import render, redirect
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

from .models import MonthlyBudget, YearlyBudget, BudgetItem, Rollover
from purchases.models import Category, Purchase, Income
from .forms import BudgetItemForm, BudgetItemFormset


class AddUserMixin:
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class YearlyBudgetCreateView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = YearlyBudget
    fields = ["date"]
    template_name = "budgets/yearly_budget_create.html"
    success_url = reverse_lazy("purchase_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        # print(form.instance.date.year)
        self.object = form.save()

        for month in range(1, 13):
            MonthlyBudget.objects.create(
                date=datetime.date(self.object.date.year, month, 1),
                user=self.request.user,
                yearly_budget=self.object,
            )

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
        kwargs = super().get_context_data(**kwargs)

        purchases = Purchase.objects.filter(
            # category=OuterRef("category"),
            user=self.request.user,
            date__year=self.object.date.year,
        )

        purchases_uncategorized = purchases.filter(category=None)

        incomes = Income.objects.filter(
            category=OuterRef("category"),
            user=self.request.user,
            date__year=self.object.date.year,
        )

        budgetitems = (
            BudgetItem.objects.filter(user=self.request.user)
            .filter(
                monthly_budget__date__year=self.object.date.year,
                # monthly_budget__date__month__lte=datetime.datetime.now().month - 2,
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
                            incomes.values("category")
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
                            # .annotate(amount="amount")
                            # .values("amount")
                        ),
                        Value(0),
                    ),
                    output_field=DecimalField(),
                ),
                amount_total=Sum("amount", distinct=False),
                diff=F("amount_total") - F("spent") + F("income") + F("rollover"),
            )
        ).order_by("category__name")

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
                amount_total=Sum("amount", distinct=False),
                diff=F("amount_total") - F("saved"),
            )
        ).order_by("category__name")

        total_spending_spent = budgetitems.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("spent"), Value(0)), output_field=DecimalField()
            )
        )
        total_spending_remaining = budgetitems.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("diff"), Value(0)), output_field=DecimalField()
            )
        )
        total_spending_budgeted = budgetitems.aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount_total"), Value(0)), output_field=DecimalField()
            )
        )

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

        total_spent = total_spending_spent["amount"] + total_saved["amount"]

        total_remaining = (
            total_spending_remaining["amount"] + total_savings_remaining["amount"]
        )

        monthly_purchases = Purchase.objects.filter(
            category=OuterRef("category"),
            date__year=self.object.date.year,
            date__month=OuterRef("monthly_budget__date__month"),
            user=self.request.user,
        ).values("date__month", "category")

        monthly_budgetitems = (
            (
                BudgetItem.objects.filter(user=self.request.user)
                .filter(monthly_budget__date__year=self.object.date.year,)
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
            )
            .order_by("monthly_budget__date__month", "savings", "category__name",)
            .select_related()
        )

        monthly_savings_transactions = Purchase.objects.filter(
            category=OuterRef("category"),
            date__year=self.object.date.year,
            date__month=OuterRef("monthly_budget__date__month"),
            user=self.request.user,
        ).values("date__month", "category")

        monthly_savingsitems = (
            (
                BudgetItem.objects.filter(user=self.request.user)
                .filter(monthly_budget__date__year=self.object.date.year, savings=True)
                .annotate(
                    spent=ExpressionWrapper(
                        Coalesce(
                            Subquery(
                                monthly_savings_transactions.annotate(
                                    total=Sum("amount")
                                ).values("total")
                            ),
                            Value(0),
                        ),
                        output_field=DecimalField(),
                    ),
                )
                .annotate(diff=F("amount") - F("spent"))
            )
            .order_by("monthly_budget__date__month", "category__name")
            .select_related()
        )

        number_of_budget_items = monthly_budgetitems.filter(
            monthly_budget__date__month=1
        ).count()

        if number_of_budget_items:
            monthly_budgs = [
                list(monthly_budgetitems)[i : i + number_of_budget_items]
                for i in range(
                    0, len(list(monthly_budgetitems)), number_of_budget_items
                )
            ]
        else:
            monthly_budgs = [[] for i in range(12)]

        number_of_savings_items = monthly_savingsitems.filter(
            monthly_budget__date__month=1
        ).count()

        if number_of_savings_items:
            monthly_saves = [
                list(monthly_savingsitems)[i : i + number_of_savings_items]
                for i in range(
                    0, len(list(monthly_savingsitems)), number_of_savings_items
                )
            ]
        else:
            monthly_saves = [[] for i in range(12)]

        monthly_budgeted = []
        monthly_spent = []
        monthly_remaining = []
        for month in monthly_budgs:
            budgeted = 0
            spent = 0
            remaining = 0
            for bud in month:
                budgeted += bud.amount
                spent += bud.spent
                remaining += bud.diff
            monthly_budgeted.append(budgeted)
            monthly_spent.append(spent)
            monthly_remaining.append(remaining)

        monthly_bs = list(
            zip(
                [
                    (1, "January"),
                    (2, "February"),
                    (3, "March"),
                    (4, "April"),
                    (5, "May"),
                    (6, "June"),
                    (7, "July"),
                    (8, "August"),
                    (9, "September"),
                    (10, "October"),
                    (11, "November"),
                    (12, "December"),
                ],
                monthly_budgs,
                monthly_budgeted,
                monthly_spent,
                monthly_remaining,
            )
        )

        incomes = Income.objects.filter(
            user=self.request.user, date__year=self.object.date.year,
        ).order_by("date")

        total_income = incomes.filter(category=None).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        free_income = total_income["amount"] - total_spent

        monthly_budgets = MonthlyBudget.objects.filter(date__year=self.object.date.year)

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

        # Shouldn't be creating new objects on GET request
        # next_year = YearlyBudget.objects.get_or_404(
        #     user=self.request.user, date__year=(self.object.date.year + 1)
        # )
        # print(next_year)

        kwargs.update(
            {
                "budget_items": budgetitems,
                "savings_items": savings_items,
                "total_spending_spent": total_spending_spent,
                "total_spending_remaining": total_spending_remaining,
                "total_spending_budgeted": total_spending_budgeted,
                "total_saved": total_saved,
                "total_savings_budgeted": total_savings_budgeted,
                "total_savings_remaining": total_savings_remaining,
                "total_spent": total_spent,
                "total_budgeted": total_budgeted,
                "total_remaining": total_remaining,
                "total_income": total_income,
                "free_income": free_income,
                "monthly_budgets": monthly_budgets,
                "monthly_bs": monthly_bs,
                "purchases_uncategorized": purchases_uncategorized,
                "rollovers_spending": rollovers_spending,
                "rollovers_savings": rollovers_savings,
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
                            # Sum(
                            # "category__purchases__amount",
                            # filter=Q(
                            #     category__purchases__date__month=self.object.date.month,
                            #     category__purchases__date__year=self.object.date.year,
                            #     category__purchases__user=self.request.user,
                            # ),
                            # distinct=True,
                            # ),
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
                                # )
                                # Sum(
                                #     "category__incomes__amount",
                                #     filter=Q(
                                #         category__incomes__date__month=self.object.date.month,
                                #         category__incomes__date__year=self.object.date.year,
                                #         category__incomes__user=self.request.user,
                                #     ),
                                #     distinct=True,
                            ),
                            Value(0),
                        ),
                        output_field=DecimalField(),
                    ),
                    diff=F("amount") - F("spent") + F("income"),
                )
            ).select_related()
        ).order_by("category__name")

        # for item in budgetitems:
        #     print(item.income)
        savings_items = (
            (
                BudgetItem.objects.filter(
                    user=self.request.user, monthly_budget=self.object, savings=True,
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
                Coalesce(Sum("amount"), Value(0),), output_field=DecimalField()
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

        total_spent = total_spending_spent["amount"] + total_saved["amount"]

        total_remaining = (
            total_spending_remaining["amount"] + total_savings_remaining["amount"]
        )

        purchases = (
            Purchase.objects.filter(
                user=self.request.user,
                date__year=self.object.date.year,
                date__month=self.object.date.month,
            )
            .order_by("date")
            .prefetch_related("category")
        )

        incomes = (
            Income.objects.filter(
                user=self.request.user,
                date__month=self.object.date.month,
                date__year=self.object.date.year,
            )
            .order_by("date")
            .prefetch_related("category")
        )

        total_income = incomes.filter(category=None).aggregate(
            amount=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            )
        )

        # try:
        free_income = total_income["amount"] - total_spent
        # except TypeError:
        #     free_income = 0

        kwargs.update(
            {
                "budget_items": budgetitems,
                "savings_items": savings_items,
                "purchases": purchases,
                "incomes": incomes,
                "total_budgeted": total_budgeted,
                "total_spent": total_spent,
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

        # form.instance.monthly_budget = MonthlyBudget.objects.get(
        #     user=self.request.user,
        #     date__year=self.kwargs["year"],
        #     date__month=self.kwargs["month"],
        # )

        monthly_budgets = list(
            MonthlyBudget.objects.filter(date__year=self.kwargs["year"])
        )

        for monthly_budget in monthly_budgets:
            # if monthly_budget != form.instance.monthly_budget:
            BudgetItem.objects.create(
                user=self.request.user,
                category=form.instance.category,
                amount=form.instance.amount,
                monthly_budget=monthly_budget,
                yearly_budget=YearlyBudget.objects.get(
                    user=self.request.user, date__year=self.kwargs["year"]
                ),
                savings=form.instance.savings,
            )

        Rollover.objects.create(
            user=self.request.user,
            category=form.instance.category,
            yearly_budget=YearlyBudget.objects.get(
                user=self.request.user, date__year=self.kwargs["year"]
            ),
        )
        # print(monthly_budgets)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.request.POST.get("next"):
            return self.request.POST.get("next")

        else:
            url = reverse_lazy("yearly_detail", kwargs={"year": self.kwargs["year"]},)
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
        print(self.kwargs)

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

