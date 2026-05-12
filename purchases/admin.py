from django.contrib import admin
from .models import Category, Purchase, Subcategory, Income, RecurringPurchase, Receipt


class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("item", "category", "amount", "date", "receipt", "user", "created_at", "updated_at")


class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("date", "source", "location", "user", "created_at", "updated_at")


class RecurringPurchaseAdmin(admin.ModelAdmin):
    list_display = ("item", "category", "amount", "source", "location", "is_active", "user", "created_at", "updated_at")
    list_filter = ("is_active", "category")
    search_fields = ("item", "source", "location")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category")


admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Income)
admin.site.register(RecurringPurchase, RecurringPurchaseAdmin)
