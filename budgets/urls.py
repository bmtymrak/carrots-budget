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
    BudgetItemDeleteView,
    YearlyBudgetItemDetailView,
    BudgetItemBulkEditView,
    rollover_update_view,
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
        "<int:year>/budgetitem-create",
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
    path(
        "<int:year>/<int:month>/<str:category>/delete",
        BudgetItemDeleteView.as_view(),
        name="budget_item_delete",
    ),
    path(
        "<int:year>/<str:category>",
        YearlyBudgetItemDetailView.as_view(),
        name="yearly_budget_item_detail",
    ),
    path(
        "<int:year>/<str:category>/edit",
        BudgetItemBulkEditView.as_view(),
        name="budgetitem_bulkedit",
    ),
    path("yearly-create", YearlyBudgetCreateView.as_view(), name="yearly_create"),
    path("<int:year>", YearlyBudgetDetailView.as_view(), name="yearly_detail"),
    path("rollover-update", rollover_update_view, name="rollover-update"),
    path("", YearlyBudgetListView.as_view(), name="yearly_list"),
]

