from django.urls import path

from .views import (
    MonthlyBudgetCreateView,
    MonthlyBudgetDetailView,
    BudgetItemDetailView,
    YearlyBudgetListView,
    YearlyBudgetDetailView,
    BudgetItemDeleteView,
    YearlyBudgetItemDetailView,
    rollover_update_view,
    budgetitem_bulk_edit,
    budgetitem_edit,
    budgetitem_delete,
    budget_item_create,
    budget_create,
)

urlpatterns = [
    path("monthly-create", MonthlyBudgetCreateView.as_view(), name="monthly_create"),
    path(
        "<int:year>/<int:month>",
        MonthlyBudgetDetailView.as_view(),
        name="monthly_detail",
    ),
    path(
        "<int:year>/budgetitem-create-htmx",
        budget_item_create,
        name="budgetitem_create_htmx",
    ),
    path(
        "<int:year>/<int:month>/<str:category>/edit/htmx",
        budgetitem_edit,
        name="budgetitem_edit_htmx",
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
        "<int:year>/<str:category>/delete/htmx",
        budgetitem_delete,
        name="budget_item_delete_htmx",
    ),
    path(
        "<int:year>/<str:category>",
        YearlyBudgetItemDetailView.as_view(),
        name="yearly_budget_item_detail",
    ),
    path(
        "<int:year>/<str:category>/edit/htmx",
        budgetitem_bulk_edit,
        name="budgetitem_bulk_edit_htmx",
    ),
    path("yearly-create", budget_create, name="yearly_create"),
    path("<int:year>", YearlyBudgetDetailView.as_view(), name="yearly_detail"),
    path("rollover-update", rollover_update_view, name="rollover_update"),
    path("", YearlyBudgetListView.as_view(), name="yearly_list"),
]
