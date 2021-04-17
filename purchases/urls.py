from django.urls import path

from .views import PurchaseListView, PurchaseAddView, CategoryCreateView

urlpatterns = [
    path("add/", PurchaseAddView.as_view(), name="purchase_add"),
    path("category-create/", CategoryCreateView.as_view(), name="category_create"),
    path("", PurchaseListView.as_view(), name="purchase_list"),
]
