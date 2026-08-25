import datetime
import json
import calendar
import time
from urllib.parse import urlsplit

from django.db.models.fields import DecimalField, BooleanField
from django.db import IntegrityError, connection, transaction
from django.http.response import HttpResponseRedirect
from django.http import Http404, HttpResponseBadRequest, JsonResponse, QueryDict
from django.views.generic.edit import DeleteView
from purchases.forms import PurchaseForm, PurchaseFormSetReceipt
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
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
    Subquery,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce

from budgets.models import (
    MonthlyBudget,
    YearlyBudget,
    BudgetItem,
    Rollover,
    ExpenseSource,
    MonthlyExpenseSource,
)
from purchases.models import Category, Purchase, Income
from budgets.forms import (
    BudgetItemForm,
    BudgetItemFormset,
    YearlyBudgetForm,
    ExpenseSourceForm,
)
from budgets.services import BudgetService
from django_htmx.http import HttpResponseClientRedirect
from purchases.services import save_purchases_with_receipts


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


class YearlyBudgetDetailView(LoginRequiredMixin, DetailView):
    model = YearlyBudget
    context_object_name = "yearly_budget"
    template_name = "budgets/yearly_budget_detail.html"

    def get_object(self):
        year_start, next_year_start = BudgetService.year_bounds(self.kwargs["year"])
        obj = self.model.objects.get(
            user=self.request.user,
            date__gte=year_start,
            date__lt=next_year_start,
        )

        return obj

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        if datetime.datetime.now().year > self.object.date.year:
            ytd_month = 12
        else:
            current_month = datetime.datetime.now().month
            try:
                ytd_month = int(self.request.GET.get("ytd", current_month))
            except (TypeError, ValueError):
                ytd_month = current_month

            if not 1 <= ytd_month <= 12:
                ytd_month = current_month


        service = BudgetService()
        budget_context = service.get_yearly_budget_context(
            user=self.request.user,
            year=self.object.date.year,
            ytd_month=ytd_month,
        )

        kwargs["ytd_month"] = ytd_month
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

    def _get_monthly_budget(self):
        return _get_user_monthly_budget(
            self.request,
            self.kwargs["year"],
            self.kwargs["month"],
        )

    def get(self, request, *args, **kwargs):

        self.object = self._get_monthly_budget()

        purchase_formset = PurchaseFormSetReceipt(
            queryset=Purchase.objects.none(), form_kwargs={"user": self.request.user}
        )

        return self.render_to_response(
            self.get_context_data(purchase_formset=purchase_formset)
        )

    def post(self, request, *arg, **kwargs):
        self.object = self._get_monthly_budget()

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
            if not instances:
                return HttpResponseRedirect(self.get_success_url())

            save_purchases_with_receipts(self.request.user, instances)

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
            month=self.object.date.month,
            monthly_budget=self.object,
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
        request, "budgets/yearly_budget_create_modal.html", {"form": form, "next": next}
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
        "budgets/budgetitem_edit_modal.html",
        {"form": form, "budget_item": budget_item, "next": next},
    )


@login_required
def budgetitem_bulk_edit(request, year, category):

    budget_items = BudgetItem.objects.filter(
        user=request.user,
        yearly_budget=YearlyBudget.objects.get(user=request.user, date__year=year),
        category__name=category,
    )
    formset = BudgetItemFormset(queryset=budget_items)

    if request.method == "POST":
        next = request.POST.get("next")
        formset = BudgetItemFormset(data=request.POST, queryset=budget_items)

        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]

    return render(
        request,
        "budgets/budgetitem_bulk_edit_modal.html",
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
        "budgets/budgetitem_delete_modal.html",
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
        "budgets/budgetitem_create_modal.html",
        {"form": form, "next": next, "year": year},
    )


def _get_user_monthly_budget(request, year, month):
    try:
        month_start, next_month_start = BudgetService.month_bounds(year, month)
    except ValueError as error:
        raise Http404("Invalid budget month") from error
    return get_object_or_404(
        MonthlyBudget,
        user=request.user,
        date__gte=month_start,
        date__lt=next_month_start,
    )


def _expense_source_next_url(request, year, month):
    default_url = reverse("monthly_detail", kwargs={"year": year, "month": month})
    requested_url = request.POST.get("next") or request.GET.get("next")
    if requested_url and url_has_allowed_host_and_scheme(
        requested_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ) and urlsplit(requested_url).path == default_url:
        return requested_url
    return default_url


def _expense_source_redirect(request, next_url):
    if request.headers.get("HX-Request") == "true":
        return HttpResponseClientRedirect(next_url)
    return redirect(next_url)


def _expense_source_modal_context(
    request,
    monthly_budget,
    create_form,
    next_url,
    rename_form=None,
):
    user_sources = list(ExpenseSource.objects.filter(user=request.user))
    monthly_sources_by_source_id = {
        monthly_source.expense_source_id: monthly_source
        for monthly_source in MonthlyExpenseSource.objects.filter(
            expense_source__user=request.user,
            monthly_budget=monthly_budget,
        )
    }
    included_sources = [
        source
        for source in user_sources
        if source.pk in monthly_sources_by_source_id
        and monthly_sources_by_source_id[source.pk].is_included
    ]
    available_sources = [
        source
        for source in user_sources
        if source.pk not in monthly_sources_by_source_id
        or not monthly_sources_by_source_id[source.pk].is_included
    ]
    included_source_rows = []
    for source in included_sources:
        if rename_form and rename_form.instance.pk == source.pk:
            row_rename_form = rename_form
        else:
            row_rename_form = ExpenseSourceForm(
                instance=source,
                user=request.user,
                auto_id=f"expense-source-{source.pk}-%s",
            )
        included_source_rows.append(
            {"source": source, "rename_form": row_rename_form}
        )

    return {
        "monthly_budget": monthly_budget,
        "create_form": create_form,
        "included_expense_source_rows": included_source_rows,
        "available_expense_sources": available_sources,
        "next": next_url,
    }


@login_required
@require_http_methods(["GET", "POST"])
def expense_source_manage(request, year, month):
    monthly_budget = _get_user_monthly_budget(request, year, month)
    next_url = _expense_source_next_url(request, year, month)
    create_form = ExpenseSourceForm(user=request.user)
    rename_form = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            create_form = ExpenseSourceForm(request.POST, user=request.user)
            if create_form.is_valid():
                try:
                    with transaction.atomic():
                        expense_source = create_form.save(commit=False)
                        expense_source.user = request.user
                        expense_source.save()
                        MonthlyExpenseSource.objects.create(
                            expense_source=expense_source,
                            monthly_budget=monthly_budget,
                        )
                except IntegrityError:
                    create_form.add_error(
                        "name",
                        "You already have an expense source with this name.",
                    )
                else:
                    return _expense_source_redirect(request, next_url)
        elif action == "rename":
            expense_source = get_object_or_404(
                ExpenseSource,
                pk=request.POST.get("source_id"),
                user=request.user,
            )
            rename_form = ExpenseSourceForm(
                request.POST,
                instance=expense_source,
                user=request.user,
                auto_id=f"expense-source-{expense_source.pk}-%s",
            )
            if rename_form.is_valid():
                try:
                    with transaction.atomic():
                        expense_source = rename_form.save(commit=False)
                        expense_source.user = request.user
                        expense_source.save()
                except IntegrityError:
                    rename_form.add_error(
                        "name",
                        "You already have an expense source with this name.",
                    )
                else:
                    return _expense_source_redirect(request, next_url)
        elif action in {"remove_from_month", "add_to_month"}:
            expense_source = get_object_or_404(
                ExpenseSource,
                pk=request.POST.get("source_id"),
                user=request.user,
            )
            if action == "remove_from_month":
                monthly_source = get_object_or_404(
                    MonthlyExpenseSource,
                    expense_source=expense_source,
                    monthly_budget=monthly_budget,
                )
                monthly_source.is_included = False
                monthly_source.save(update_fields=["is_included"])
            else:
                monthly_source, _ = MonthlyExpenseSource.objects.get_or_create(
                    expense_source=expense_source,
                    monthly_budget=monthly_budget,
                )
                if not monthly_source.is_included:
                    monthly_source.is_included = True
                    monthly_source.save(update_fields=["is_included"])
            return _expense_source_redirect(request, next_url)
        else:
            return HttpResponseBadRequest("Unsupported expense source action")

    return render(
        request,
        "budgets/expense_source_manage_modal.html",
        _expense_source_modal_context(
            request,
            monthly_budget,
            create_form,
            next_url,
            rename_form=rename_form,
        ),
    )


@login_required
@require_POST
def expense_source_toggle(request, year, month, source_id):
    monthly_budget = _get_user_monthly_budget(request, year, month)
    monthly_source = get_object_or_404(
        MonthlyExpenseSource.objects.select_related("expense_source"),
        monthly_budget=monthly_budget,
        expense_source_id=source_id,
        expense_source__user=request.user,
        is_included=True,
    )
    update_fields = []
    if "is_checked" in request.POST:
        was_checked = monthly_source.is_checked
        monthly_source.is_checked = request.POST.get("is_checked") in {
            "1",
            "on",
            "true",
        }
        if monthly_source.is_checked and not was_checked:
            monthly_source.checked_at = timezone.now()
        elif not monthly_source.is_checked:
            monthly_source.checked_at = None
        update_fields.extend(["is_checked", "checked_at"])
    if "notes" in request.POST:
        monthly_source.notes = request.POST["notes"].strip()
        update_fields.append("notes")
    if update_fields:
        monthly_source.save(update_fields=update_fields)

    next_url = _expense_source_next_url(request, year, month)
    if request.headers.get("HX-Request") == "true":
        checklist_context = BudgetService().get_expense_source_checklist(
            user=request.user,
            monthly_budget=monthly_budget,
        )
        return render(
            request,
            "budgets/_expense_source_checklist.html",
            {
                "monthly_budget": monthly_budget,
                "expense_source_next_url": next_url,
                **checklist_context,
            },
        )
    return redirect(next_url)
