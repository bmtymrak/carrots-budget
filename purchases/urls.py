from django.urls import path

from .views import (
    PurchaseListView,
    PurchaseAddView,
    PurchaseDeleteView,
    PurchaseEditView,
    CategoryCreateView,
)

urlpatterns = [
    path("add/", PurchaseAddView.as_view(), name="purchase_add"),
    path("category-create/", CategoryCreateView.as_view(), name="category_create"),
    path("<int:pk>/delete/", PurchaseDeleteView.as_view(), name="purchase_delete"),
    path("<int:pk>/edit/", PurchaseEditView.as_view(), name="purchase_edit"),
    path("", PurchaseListView.as_view(), name="purchase_list"),
]
