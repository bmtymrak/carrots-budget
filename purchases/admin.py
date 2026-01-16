from django.contrib import admin
from .models import Category, Purchase, Subcategory, Income, Receipt


class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("item", "category", "amount", "date", "user", "receipt", "created_at", "updated_at")


class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Income)
admin.site.register(Receipt, ReceiptAdmin)

