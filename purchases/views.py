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
from .forms import PurchaseForm, PurchaseFormSet, PurchaseFormSetReceipt, IncomeForm, RecurringPurchaseForm
from django_htmx.http import HttpResponseClientRedirect


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
        "purchases/purchase_delete_htmx.html",
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
        "purchases/income_delete_htmx.html",
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
        "purchases/purchase_edit_htmx.html",
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
        "purchases/income_edit_htmx.html",
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
        "purchases/income_create_htmx.html",
        {"form": form, "next": next},
    )


@login_required
def recurringpurchase_manage(request):
    """Display modal with form to create new recurring purchase and list of existing ones."""
    
    form = RecurringPurchaseForm(user=request.user)
    recurring_purchases = RecurringPurchase.objects.filter(user=request.user)
    
    if request.method == "POST":
        next = request.POST.get("next")
        form = RecurringPurchaseForm(data=request.POST, user=request.user)
        form.instance.user = request.user
        
        if form.is_valid():
            form.save()
            return HttpResponseClientRedirect(next)
    
    if request.method == "GET":
        next = request.GET["next"]
    
    return render(
        request,
        "purchases/recurringpurchase_manage_modal.html",
        {
            "form": form,
            "recurring_purchases": recurring_purchases,
            "next": next,
        },
    )


@login_required
def recurringpurchase_edit(request, pk):
    """Edit an existing recurring purchase."""
    
    recurring_purchase = RecurringPurchase.objects.get(user=request.user, pk=pk)
    form = RecurringPurchaseForm(instance=recurring_purchase, user=request.user)
    
    if request.method == "POST":
        next = request.POST.get("next")
        form = RecurringPurchaseForm(instance=recurring_purchase, data=request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseClientRedirect(next)
    
    if request.method == "GET":
        next = request.GET["next"]
    
    return render(
        request,
        "purchases/recurringpurchase_edit_modal.html",
        {"form": form, "recurring_purchase": recurring_purchase, "next": next},
    )


@login_required
def recurringpurchase_delete(request, pk):
    """Delete a recurring purchase."""
    
    recurring_purchase = RecurringPurchase.objects.get(user=request.user, pk=pk)
    
    if request.method == "DELETE":
        next = request.GET.get("next", "/")
        recurring_purchase.delete()
        return HttpResponseClientRedirect(next)
    
    if request.method == "GET":
        next = request.GET["next"]
    
    return render(
        request,
        "purchases/recurringpurchase_delete_modal.html",
        {"recurring_purchase": recurring_purchase, "next": next},
    )


@login_required
def recurringpurchase_add_to_month(request):
    """
    Display a modal to select recurring purchases and add them to a monthly budget.
    Creates Purchase objects for selected recurring purchases.
    """
    
    if request.method == "GET":
        next = request.GET["next"]
        monthly_budget_id = request.GET.get("monthly_budget_id")
        
        # Get the monthly budget to determine the date
        from budgets.models import MonthlyBudget
        monthly_budget = MonthlyBudget.objects.get(pk=monthly_budget_id, user=request.user)
        
        # Get active recurring purchases for this user
        recurring_purchases = RecurringPurchase.objects.filter(
            user=request.user,
            is_active=True
        )
        
        # Check which recurring purchases have already been added this month
        # We'll check for purchases that match the name and were created on the first day of this month
        first_day_of_month = monthly_budget.date.replace(day=1)
        
        # Get existing purchases for this month that match recurring purchase names
        existing_purchase_names = set(
            Purchase.objects.filter(
                user=request.user,
                date=first_day_of_month,
                item__in=[rp.name for rp in recurring_purchases]
            ).values_list('item', flat=True)
        )
        
        # Mark which recurring purchases have already been added
        for rp in recurring_purchases:
            rp.already_added = rp.name in existing_purchase_names
        
        # Check if all active recurring purchases have been added
        all_added = all(rp.already_added for rp in recurring_purchases) if recurring_purchases else False
        
        return render(
            request,
            "purchases/recurringpurchase_add_modal.html",
            {
                "recurring_purchases": recurring_purchases,
                "monthly_budget": monthly_budget,
                "next": next,
                "all_added": all_added,
            },
        )
    
    if request.method == "POST":
        next = request.POST.get("next")
        monthly_budget_id = request.POST.get("monthly_budget_id")
        
        # Get the monthly budget
        from budgets.models import MonthlyBudget
        monthly_budget = MonthlyBudget.objects.get(pk=monthly_budget_id, user=request.user)
        
        # Get selected recurring purchases from POST data
        # Format: recurring_purchase_<id> checkbox
        # amount_<id>, source_<id>, location_<id>, notes_<id> for overrides
        
        created_count = 0
        for key in request.POST:
            if key.startswith("recurring_purchase_"):
                rp_id = key.split("_")[-1]
                recurring_purchase = RecurringPurchase.objects.get(pk=rp_id, user=request.user)
                
                # Get overridden values or use defaults
                amount = request.POST.get(f"amount_{rp_id}", recurring_purchase.amount)
                source = request.POST.get(f"source_{rp_id}", recurring_purchase.source)
                location = request.POST.get(f"location_{rp_id}", recurring_purchase.location)
                notes = request.POST.get(f"notes_{rp_id}", recurring_purchase.notes)
                
                # Create the purchase
                Purchase.objects.create(
                    user=request.user,
                    item=recurring_purchase.name,
                    date=monthly_budget.date.replace(day=1),  # First day of month
                    amount=amount,
                    source=source,
                    location=location,
                    category=recurring_purchase.category,
                    notes=notes,
                    savings=False,
                )
                created_count += 1
        
        return HttpResponseClientRedirect(next)
