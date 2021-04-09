from django.forms import ModelForm
from .models import Purchase, Category, Subcategory


class PurchaseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(
            user=self.request.user
        )
        self.fields["subcategory"].queryset = Subcategory.objects.filter(
            user=self.request.user
        )

    class Meta:
        model = Purchase
        fields = [
            "item",
            "date",
            "amount",
            "source",
            "location",
            "category",
            "subcategory",
            "notes",
        ]

