from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    DeleteView,
    UpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView

from .models import Purchase, Category, Income
from .forms import PurchaseForm, PurchaseFormSet, IncomeForm


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


class PurchaseDetailView(LoginRequiredMixin, DetailView):
    model = Purchase


class PurchaseEditView(LoginRequiredMixin, UpdateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "purchases/purchase_edit.html"
    success_url = reverse_lazy("purchase_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_object(self):
        obj = Purchase.objects.get(user=self.request.user, id=self.kwargs.get("pk"))
        return obj

    def get_success_url(self):
        if self.request.POST.get("next"):
            return self.request.POST.get("next")

        else:
            return reverse_lazy("purchase_list")


class PurchaseDeleteView(LoginRequiredMixin, DeleteView):
    model = Purchase
    context_object_name = "purchase"
    template_name = "purchases/purchase_delete.html"

    def get_object(self):
        obj = self.model.objects.get(user=self.request.user, id=self.kwargs.get("pk"))
        return obj

    def get_success_url(self):
        if self.request.POST.get("next"):
            return self.request.POST.get("next")

        else:
            return reverse_lazy("purchase_list")


class PurchaseAddView(LoginRequiredMixin, TemplateView):
    template_name = "purchases/purchase_add.html"

    def get(self, *args, **kwargs):
        formset = PurchaseFormSet(
            queryset=Purchase.objects.none(), form_kwargs={"user": self.request.user}
        )
        return self.render_to_response({"purchase_formset": formset})

    def post(self, *args, **kwargs):
        formset = PurchaseFormSet(
            form_kwargs={"user": self.request.user}, data=self.request.POST
        )

        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.user = self.request.user
                instance.save()
            return redirect(reverse_lazy("purchase_list"))

        else:
            return self.render_to_response({"purchase_formset": formset})


class CategoryCreateView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = Category
    fields = ["name", "rollover"]
    template_name = "purchases/category_create.html"
    success_url = reverse_lazy("monthly_budget_list")

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        categories = Category.objects.filter(user=self.request.user)
        kwargs.update({"categories": categories})
        return kwargs


class IncomeAddView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = Income
    form_class = IncomeForm
    template_name = "purchases/income_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        if self.request.POST.get("next"):
            return self.request.POST.get("next")

        else:
            return reverse_lazy("yearly_list")


class IncomeEditView(LoginRequiredMixin, UpdateView):
    model = Income
    form_class = IncomeForm
    template_name = "purchases/income_edit.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        if self.request.POST.get("next"):
            return self.request.POST.get("next")

        else:
            return reverse_lazy("purchase_list")
