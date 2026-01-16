from purchases.models import Income
from django.urls import path

from .views import (
    PurchaseListView,
    CategoryCreateView,
    purchase_delete_htmx,
    income_delete_htmx,
    purchase_create,
    purchase_edit,
    income_edit,
    income_create,
    recurringpurchase_manage,
    recurringpurchase_edit,
    recurringpurchase_delete,
    recurringpurchase_add_to_month,
)

urlpatterns = [
    path("add/", purchase_create, name="purchase_create"),
    path("category-create/", CategoryCreateView.as_view(), name="category_create"),
    path("<int:pk>/delete/htmx", purchase_delete_htmx, name="purchase_delete_htmx"),
    path("<int:pk>/edit/htmx", purchase_edit, name="purchase_edit_htmx"),
    path("income-create/", income_create, name="income_create"),
    path("income/<int:pk>/edit/htmx", income_edit, name="income_edit_htmx"),
    path("income/<int:pk>/delete/htmx", income_delete_htmx, name="income_delete_htmx"),
    path("recurring/manage/", recurringpurchase_manage, name="recurringpurchase_manage"),
    path("recurring/<int:pk>/edit/", recurringpurchase_edit, name="recurringpurchase_edit"),
    path("recurring/<int:pk>/delete/", recurringpurchase_delete, name="recurringpurchase_delete"),
    path("recurring/add-to-month/", recurringpurchase_add_to_month, name="recurringpurchase_add_to_month"),
    path("", PurchaseListView.as_view(), name="purchase_list"),
]
