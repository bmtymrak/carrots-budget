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

from .models import Purchase, Category, Income
from .forms import PurchaseForm, PurchaseFormSet, PurchaseFormSetReceipt, IncomeForm
from django_htmx.http import HttpResponseClientRedirect


class AddUserMixin:
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    context_object_name = "purchases"
    template_name = "purchase_list.html"
    ordering = "-date"
    paginate_by = 200

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(user=self.request.user).prefetch_related("category")
        
        # Filter by category
        category_id = self.request.GET.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)
        
        # Filter by year
        year = self.request.GET.get("year")
        if year:
            qs = qs.filter(date__year=year)
        
        # Filter by month (only if year is also specified)
        month = self.request.GET.get("month")
        if month and year:
            qs = qs.filter(date__month=month)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all categories for the filter dropdown
        context['categories'] = Category.objects.filter(user=self.request.user).order_by('name')
        # Pass current filter values to template
        context['selected_category'] = self.request.GET.get("category", "")
        context['selected_year'] = self.request.GET.get("year", "")
        context['selected_month'] = self.request.GET.get("month", "")
        # Get distinct years from purchases for year dropdown
        years = Purchase.objects.filter(user=self.request.user).dates('date', 'year', order='DESC')
        context['years'] = [date.year for date in years]
        return context

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
