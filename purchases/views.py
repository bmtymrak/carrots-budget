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

from .models import Purchase, Category, Income, Receipt
from .forms import PurchaseForm, PurchaseFormSet, PurchaseFormSetReceipt, IncomeForm
from django_htmx.http import HttpResponseClientRedirect


def parse_date_for_form_kwargs(user, date_str):
    """Helper function to parse date and create form kwargs"""
    if date_str:
        try:
            parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return {"user": user, "date": parsed_date}
        except ValueError:
            return {"user": user}
    return {"user": user}


def apply_common_fields_to_purchases(instances):
    """Helper function to apply source and location from first purchase to all"""
    if instances:
        source = instances[0].source
        location = instances[0].location
        for instance in instances:
            instance.source = source
            instance.location = location


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
        form_kwargs = parse_date_for_form_kwargs(request.user, formset_date)

        purchase_formset = PurchaseFormSetReceipt(
            form_kwargs=form_kwargs, data=formset_data
        )

        if purchase_formset.is_valid():
            instances = purchase_formset.save(commit=False)
            
            # Apply common fields from first purchase to all
            apply_common_fields_to_purchases(instances)
            
            # Create a receipt for this group of purchases
            receipt = Receipt.objects.create(user=request.user)
            
            for instance in instances:
                instance.user = request.user
                instance.receipt = receipt
                instance.save()
            return HttpResponseClientRedirect(next)

    if request.method == "GET":
        next = request.GET["next"]
        
        # Check if a date is provided as a query parameter
        date_param = request.GET.get("date")
        form_kwargs = parse_date_for_form_kwargs(request.user, date_param)
            
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
    
    # Get all purchases from the same receipt if it exists
    if purchase.receipt:
        purchases_queryset = Purchase.objects.filter(
            receipt=purchase.receipt, user=request.user
        ).order_by('id')
    else:
        # If no receipt, just edit the single purchase
        purchases_queryset = Purchase.objects.filter(pk=pk)

    if request.method == "POST":
        next = request.POST.get("next")
        formset_data = request.POST.copy()
        
        # Get the date from the first form to apply to all
        formset_date = formset_data.get("form-0-date")
        
        # Parse the date to pass to forms
        form_kwargs = parse_date_for_form_kwargs(request.user, formset_date)
        
        purchase_formset = PurchaseFormSet(
            form_kwargs=form_kwargs, data=formset_data, queryset=purchases_queryset
        )
        
        if purchase_formset.is_valid():
            instances = purchase_formset.save(commit=False)
            # Apply source and location from first form to all purchases
            apply_common_fields_to_purchases(instances)
            for instance in instances:
                instance.save()
            return HttpResponseClientRedirect(next)
    
    if request.method == "GET":
        next = request.GET["next"]
        
        # Get date from the first purchase to filter categories
        first_purchase = purchases_queryset.first()
        date_str = first_purchase.date.strftime("%Y-%m-%d") if first_purchase and first_purchase.date else None
        form_kwargs = parse_date_for_form_kwargs(request.user, date_str)
        
        purchase_formset = PurchaseFormSet(
            form_kwargs=form_kwargs, queryset=purchases_queryset
        )

    return render(
        request,
        "purchases/purchase_edit_htmx.html",
        {"purchase_formset": purchase_formset, "purchase": purchase, "next": next},
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
