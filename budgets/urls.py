from django.urls import path

from .views import (
    YearlyBudgetCreateView,
    MonthlyBudgetCreateView,
    MonthlyBudgetListView,
    MonthlyBudgetDetailView,
    BudgetItemCreateView,
    BudgetItemEditView,
    BudgetItemDetailView,
    YearlyBudgetListView,
    YearlyBudgetDetailView,
)

urlpatterns = [
    path(
        "monthly-budget-list",
        MonthlyBudgetListView.as_view(),
        name="monthly_budget_list",
    ),
    path("monthly-create", MonthlyBudgetCreateView.as_view(), name="monthly_create"),
    path(
        "<int:year>/<int:month>",
        MonthlyBudgetDetailView.as_view(),
        name="monthly_detail",
    ),
    path(
        "<int:year>/<int:month>/budgetitem-create",
        BudgetItemCreateView.as_view(),
        name="budgetitem_create",
    ),
    path(
        "<int:year>/<int:month>/<str:category>/edit",
        BudgetItemEditView.as_view(),
        name="budgetitem_edit",
    ),
    path(
        "<int:year>/<int:month>/<str:category>",
        BudgetItemDetailView.as_view(),
        name="budget_item_detail",
    ),
    path("yearly-create", YearlyBudgetCreateView.as_view(), name="yearly_create"),
    path("<int:year>", YearlyBudgetDetailView.as_view(), name="yearly_detail"),
    path("", YearlyBudgetListView.as_view(), name="yearly_list"),
]

