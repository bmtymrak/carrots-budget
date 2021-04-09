from django.contrib import admin
from .models import YearlyBudget, MonthlyBudget, BudgetItem


admin.site.register(YearlyBudget)
admin.site.register(MonthlyBudget)
admin.site.register(BudgetItem)
