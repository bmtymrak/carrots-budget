from django.urls import path

from .views import PurchaseListView, PurchaseAddView

urlpatterns = [
    path("add/", PurchaseAddView.as_view(), name="purchase_add"),
    path("", PurchaseListView.as_view(), name="purchase_list"),
]
