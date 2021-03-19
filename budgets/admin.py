from django.contrib import admin
from .models import Budget, BudgetItem


admin.site.register(Budget)
admin.site.register(BudgetItem)
