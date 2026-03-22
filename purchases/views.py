from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    DeleteView,
    UpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
import datetime

from .models import Purchase, Category, Income, RecurringPurchase
from .forms import (
    PurchaseForm,
    PurchaseFormSetReceipt,
    IncomeForm,
    RecurringPurchaseForm,
    RecurringPurchaseAddToMonthFormSet,
)
from django_htmx.http import HttpResponseClientRedirect
from budgets.models import MonthlyBudget


class AddUserMixin:
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    context_object_name = "purchases"
    template_name = "purchase_list.html"
    ordering = "date"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user).prefetch_related("category")

class CategoryCreateView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = Category
    fields = ["name", "rollover"]
    template_name = "purchases/category_create.html"
    success_url = reverse_lazy("yearly_list")

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        categories = Category.objects.filter(user=self.request.user)
        kwargs.update({"categories": categories})
        return kwargs


@login_required
def purchase_delete_htmx(request, pk):

    purchase = Purchase.objects.get(user=request.user, pk=pk)

    next = request.GET["next"]

    if request.method == "DELETE":
        purchase.delete()
        return HttpResponseClientRedirect(next)

    return render(
        request,
        "purchases/purchase_delete_modal.html",
        {"purchase": purchase, "next": next},
    )


@login_required
def income_delete_htmx(request, pk):

    income = Income.objects.get(user=request.user, pk=pk)

    next = request.GET["next"]

    if request.method == "DELETE":
        income.delete()
        return HttpResponseClientRedirect(next)

    return render(
        request,
        "purchases/income_delete_modal.html",
        {"income": income, "next": next},
    )


@login_required
def purchase_create(request):

    if request.method == "POST":
        next = request.POST.get("next")
        formset_data = request.POST.copy()  # Makes Querydict mutable
        formset_date = formset_data["form-0-date"]

        for key in formset_data.keys():
            if "date" in key:
                formset_data[key] = formset_date

        # Parse the date to pass to forms
        try:
            parsed_date = datetime.datetime.strptime(formset_date, "%Y-%m-%d").date()
            form_kwargs = {"user": request.user, "date": parsed_date}
        except ValueError:

            form_kwargs = {"user": request.user}

        purchase_formset = PurchaseFormSetReceipt(
            form_kwargs=form_kwargs, data=formset_data
        )

        if purchase_formset.is_valid():
            instances = purchase_formset.save(commit=False)
            source = instances[0].source
            location = instances[0].location
            for instance in instances:
                instance.user = request.user
                instance.source = source
                instance.location = location
                instance.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]
        
        # Check if a date is provided as a query parameter
        date_param = request.GET.get("date")
        if date_param:
            try:
                parsed_date = datetime.datetime.strptime(date_param, "%Y-%m-%d").date()
                form_kwargs = {"user": request.user, "date": parsed_date}
            except ValueError:
                # If date parsing fails, just pass the user
                form_kwargs = {"user": request.user}
        else:
            form_kwargs = {"user": request.user}
            
        purchase_formset = PurchaseFormSetReceipt(
            queryset=Purchase.objects.none(), form_kwargs=form_kwargs
        )

    return render(
        request,
        "purchases/purchase_create.html",
        {"purchase_formset": purchase_formset, "next": next},
    )


@login_required
def purchase_edit(request, pk):
    purchase = Purchase.objects.get(user=request.user, pk=pk)

    form = PurchaseForm(instance=purchase, user=request.user)

    if request.method == "POST":
        next = request.POST.get("next")
        form = PurchaseForm(instance=purchase, data=request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]

    return render(
        request,
        "purchases/purchase_edit_modal.html",
        {"form": form, "purchase": purchase, "next": next},
    )


@login_required
def income_edit(request, pk):
    income = Income.objects.get(user=request.user, pk=pk)

    form = IncomeForm(instance=income, user=request.user)

    if request.method == "POST":
        next = request.POST.get("next")
        form = IncomeForm(instance=income, data=request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]

    return render(
        request,
        "purchases/income_edit_modal.html",
        {"form": form, "income": income, "next": next},
    )


@login_required
def income_create(request):

    form = IncomeForm(user=request.user)

    if request.method == "POST":
        next = request.POST.get("next")
        form = IncomeForm(data=request.POST, user=request.user)
        form.instance.user = request.user

        if form.is_valid():
            form.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]

    return render(
        request,
        "purchases/income_create_modal.html",
        {"form": form, "next": next},
    )


@login_required
def recurring_purchase_list(request):
    """List all recurring purchases for the user with option to create new ones."""
    recurring_purchases = RecurringPurchase.objects.filter(
        user=request.user
    ).select_related("category")
    form = RecurringPurchaseForm(user=request.user)
    next_url = request.GET.get("next", reverse("yearly_list"))

    if request.method == "POST":
        form = RecurringPurchaseForm(data=request.POST, user=request.user)
        form.instance.user = request.user

        if form.is_valid():
            form.save()
            form = RecurringPurchaseForm(user=request.user)
            recurring_purchases = RecurringPurchase.objects.filter(
                user=request.user
            ).select_related("category")

    return render(
        request,
        "purchases/recurring_purchase_list_modal.html",
        {
            "recurring_purchases": recurring_purchases,
            "form": form,
            "next": next_url,
        },
    )


@login_required
def recurring_purchase_edit(request, pk):
    """Edit a recurring purchase."""
    recurring_purchase = RecurringPurchase.objects.get(user=request.user, pk=pk)
    form = RecurringPurchaseForm(instance=recurring_purchase, user=request.user)
    next_url = request.GET.get("next", reverse("yearly_list"))

    if request.method == "POST":
        next_url = request.POST.get("next", next_url)
        form = RecurringPurchaseForm(
            instance=recurring_purchase, data=request.POST, user=request.user
        )
        if form.is_valid():
            form.save()
            return HttpResponseClientRedirect(next_url)

    return render(
        request,
        "purchases/recurring_purchase_edit_modal.html",
        {"form": form, "recurring_purchase": recurring_purchase, "next": next_url},
    )


@login_required
def recurring_purchase_delete(request, pk):
    """Delete a recurring purchase."""
    recurring_purchase = RecurringPurchase.objects.get(user=request.user, pk=pk)
    next_url = request.GET.get("next", reverse("yearly_list"))

    if request.method == "DELETE":
        recurring_purchase.delete()
        return HttpResponseClientRedirect(next_url)

    return render(
        request,
        "purchases/recurring_purchase_delete_modal.html",
        {"recurring_purchase": recurring_purchase, "next": next_url},
    )


@login_required
def recurring_purchase_add_to_month(request, year, month):
    """Add recurring purchases to a specific month as actual purchases."""
    monthly_budget = MonthlyBudget.objects.get(
        user=request.user, date__year=year, date__month=month
    )
    recurring_purchases = RecurringPurchase.objects.filter(
        user=request.user, is_active=True
    ).select_related("category")
    next_url = request.GET.get(
        "next", reverse("monthly_detail", kwargs={"year": year, "month": month})
    )
    
    # Check which recurring purchases have already been added this month
    # by looking for purchases with a foreign key to a recurring purchase
    purchase_date = monthly_budget.date
    already_added_purchases = Purchase.objects.filter(
        user=request.user,
        date__year=year,
        date__month=month,
        recurring_purchase__isnull=False
    ).select_related("category", "recurring_purchase")
    
    # Create a dict mapping recurring_purchase_id to the actual purchase details
    already_added_details = {
        p.recurring_purchase_id: {
            "date": p.date,
            "amount": p.amount,
            "source": p.source,
            "location": p.location,
            "category": p.category,
            "category_id": p.category_id,
            "notes": p.notes,
        }
        for p in already_added_purchases
    }
    already_added = set(already_added_details.keys())
    formset = RecurringPurchaseAddToMonthFormSet(
        user=request.user,
        recurring_purchases=recurring_purchases,
        purchase_date=purchase_date,
        already_added_details=already_added_details,
    )

    if request.method == "POST":
        next_url = request.POST.get("next", next_url)
        formset = RecurringPurchaseAddToMonthFormSet(
            data=request.POST,
            user=request.user,
            recurring_purchases=recurring_purchases,
            purchase_date=purchase_date,
            already_added_details=already_added_details,
        )

        if formset.is_valid():
            for selected_purchase in formset.selected_purchases:
                recurring = selected_purchase["recurring_purchase"]
                if recurring.id in already_added:
                    continue

                Purchase.objects.create(
                    user=request.user,
                    item=recurring.name,
                    date=selected_purchase["date"],
                    amount=selected_purchase["amount"],
                    source=selected_purchase["source"],
                    location=selected_purchase["location"],
                    category=selected_purchase["category"],
                    notes=selected_purchase["notes"],
                    savings=False,
                    recurring_purchase=recurring,
                )
                already_added.add(recurring.id)

            return HttpResponseClientRedirect(next_url)

    return render(
        request,
        "purchases/recurring_purchase_add_to_month_modal.html",
        {
            "already_added": already_added,
            "has_form_errors": formset.is_bound and (formset.total_error_count() > 0 or bool(formset.non_form_errors())),
            "formset": formset,
            "monthly_budget": monthly_budget,
            "all_already_added": len(already_added) == recurring_purchases.count() and recurring_purchases.exists(),
            "next": next_url,
        },
    )
