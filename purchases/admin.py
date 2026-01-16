from django.contrib import admin
from .models import Category, Purchase, Subcategory, Income, RecurringPurchase


class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("item", "category", "amount", "date", "user", "created_at", "updated_at")


class RecurringPurchaseAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "amount", "merchant", "is_active", "user", "created_at", "updated_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "merchant")


admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Income)
admin.site.register(RecurringPurchase, RecurringPurchaseAdmin)

