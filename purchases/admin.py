from django.contrib import admin
from .models import Category, Purchase, Subcategory


class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("item", "category", "amount", "date", "user")


admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(Category)
admin.site.register(Subcategory)

