from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Purchase, Category
from .forms import PurchaseForm


class AddUserMixin:
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    context_object_name = "purchases"
    template_name = "purchase_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class PurchaseAddView(LoginRequiredMixin, AddUserMixin, CreateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "purchases/purchase_add.html"
    success_url = reverse_lazy("purchase_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


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
