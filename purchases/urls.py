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
    recurring_purchase_list,
    recurring_purchase_edit,
    recurring_purchase_delete,
    recurring_purchase_add_to_month,
)

urlpatterns = [
    path("add/", purchase_create, name="purchase_create"),
    path("category-create/", CategoryCreateView.as_view(), name="category_create"),
    path("<int:pk>/delete/htmx", purchase_delete_htmx, name="purchase_delete_htmx"),
    path("<int:pk>/edit/htmx", purchase_edit, name="purchase_edit_htmx"),
    path("income-create/", income_create, name="income_create"),
    path("income/<int:pk>/edit/htmx", income_edit, name="income_edit_htmx"),
    path("income/<int:pk>/delete/htmx", income_delete_htmx, name="income_delete_htmx"),
    path("recurring/", recurring_purchase_list, name="recurring_purchase_list"),
    path("recurring/<int:pk>/edit/", recurring_purchase_edit, name="recurring_purchase_edit"),
    path("recurring/<int:pk>/delete/", recurring_purchase_delete, name="recurring_purchase_delete"),
    path("recurring/add-to-month/<int:year>/<int:month>/", recurring_purchase_add_to_month, name="recurring_purchase_add_to_month"),
    path("", PurchaseListView.as_view(), name="purchase_list"),
]
