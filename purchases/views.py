from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Purchase
from .forms import PurchaseForm


class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    context_object_name = "purchases"
    template_name = "purchase_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class PurchaseAddView(CreateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "purchases/purchase_add.html"
    success_url = reverse_lazy("purchase_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

