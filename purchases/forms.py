from django.forms import ModelForm, modelformset_factory
from .models import Purchase, Category, Subcategory


class PurchaseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.user)
        self.fields["category"].empty_label = "Category"
        self.fields["subcategory"].queryset = Subcategory.objects.filter(user=self.user)
        self.fields["subcategory"].empty_label = "Sub-category"

        self.fields["item"].widget.attrs.update(placeholder="Item", size="12")
        self.fields["amount"].widget.attrs.update(placeholder="Price",)
        self.fields["source"].widget.attrs.update(placeholder="Source", size="12")
        self.fields["location"].widget.attrs.update(placeholder="Location", size="12")
        self.fields["notes"].widget.attrs.update(
            placeholder="Notes", rows="1", cols="15"
        )
        self.fields["date"].widget.attrs.update(placeholder="Date", size="10")

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
