from django.contrib import admin
from .models import YearlyBudget, MonthlyBudget, BudgetItem, Rollover


class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ("category", "amount", "monthly_budget", "user")


admin.site.register(YearlyBudget)
admin.site.register(MonthlyBudget)
admin.site.register(BudgetItem, BudgetItemAdmin)
admin.site.register(Rollover)
