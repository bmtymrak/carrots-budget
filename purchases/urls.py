from purchases.models import Income
from django.urls import path

from .views import (
    PurchaseListView,
    PurchaseAddView,
    PurchaseDeleteView,
    PurchaseEditView,
    CategoryCreateView,
    IncomeAddView,
    IncomeEditView,
    IncomeDeleteView,
)

urlpatterns = [
    path("add/", PurchaseAddView.as_view(), name="purchase_add"),
    path("category-create/", CategoryCreateView.as_view(), name="category_create"),
    path("<int:pk>/delete/", PurchaseDeleteView.as_view(), name="purchase_delete"),
    path("<int:pk>/edit/", PurchaseEditView.as_view(), name="purchase_edit"),
    path("income-add/", IncomeAddView.as_view(), name="income_add"),
    path("income/<int:pk>/edit/", IncomeEditView.as_view(), name="income_edit"),
    path("income/<int:pk>/delete/", IncomeDeleteView.as_view(), name="income_delete"),
    path("", PurchaseListView.as_view(), name="purchase_list"),
]
