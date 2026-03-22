from purchases.models import Income
from django.urls import path

from .views import (
    PurchaseListView,
    CategoryCreateView,
    category_edit,
    purchase_delete_htmx,
    income_delete_htmx,
    purchase_create,
    purchase_edit,
    income_edit,
    income_create,
)

urlpatterns = [
    path("add/", purchase_create, name="purchase_create"),
    path("category-create/", CategoryCreateView.as_view(), name="category_create"),
    path("category/<int:pk>/edit/htmx", category_edit, name="category_edit_htmx"),
    path("<int:pk>/delete/htmx", purchase_delete_htmx, name="purchase_delete_htmx"),
    path("<int:pk>/edit/htmx", purchase_edit, name="purchase_edit_htmx"),
    path("income-create/", income_create, name="income_create"),
    path("income/<int:pk>/edit/htmx", income_edit, name="income_edit_htmx"),
    path("income/<int:pk>/delete/htmx", income_delete_htmx, name="income_delete_htmx"),
    path("", PurchaseListView.as_view(), name="purchase_list"),
]
