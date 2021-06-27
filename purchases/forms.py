from django.forms import ModelForm, modelformset_factory
from .models import Purchase, Category, Subcategory


class PurchaseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.user)
        self.fields["subcategory"].queryset = Subcategory.objects.filter(user=self.user)
        self.fields["notes"].widget.attrs.update(rows="1")

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


PurchaseFormSet = modelformset_factory(Purchase, form=PurchaseForm, extra=10)
