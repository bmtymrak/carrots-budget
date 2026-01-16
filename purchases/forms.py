from django.forms import ModelForm, modelformset_factory

from .models import Purchase, Category, Subcategory, Income, RecurringPurchase
from budgets.models import BudgetItem, YearlyBudget


class PurchaseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.date = kwargs.pop("date", None)
        super().__init__(*args, **kwargs)
        
        if self.date:
            # Filter categories to only those associated with budget items in the yearly budget for this date
            
            year = self.date.year
            
            try:
                yearly_budget = YearlyBudget.objects.get(user=self.user, date__year=year)
                
                # Find budget items for this user and yearly budget, and get their categories
                budget_item_categories = BudgetItem.objects.filter(
                    user=self.user,
                    yearly_budget=yearly_budget
                ).values_list('category', flat=True)
                
                self.fields["category"].queryset = Category.objects.filter(
                    id__in=budget_item_categories
                ).distinct()
            except YearlyBudget.DoesNotExist:
                # If no yearly budget exists for this year, show all categories for the user
                self.fields["category"].queryset = Category.objects.filter(user=self.user)
        else:
            # Default behavior: show all categories for the user
            self.fields["category"].queryset = Category.objects.filter(user=self.user)
            
        self.fields["category"].empty_label = "Category"
        self.fields["subcategory"].queryset = Subcategory.objects.filter(user=self.user)
        self.fields["subcategory"].empty_label = "Sub-category"

        self.fields["item"].widget.attrs.update(placeholder="Item", size="12")
        self.fields["amount"].widget.attrs.update(
            placeholder="Price",
        )
        self.fields["source"].widget.attrs.update(placeholder="Source", size="12")
        self.fields["location"].widget.attrs.update(placeholder="Location", size="12")
        self.fields["notes"].widget.attrs.update(
            placeholder="Notes", rows="1", cols="15"
        )
        self.fields["date"].widget.attrs.update(placeholder="Date", size="10")
        self.fields["savings"].label = "Savings"

    class Meta:
        model = Purchase
        fields = [
            "date",
            "item",
            "amount",
            "source",
            "location",
            "category",
            "subcategory",
            "notes",
            "savings",
        ]


PurchaseFormSet = modelformset_factory(Purchase, form=PurchaseForm, extra=10)
PurchaseFormSetReceipt = modelformset_factory(Purchase, form=PurchaseForm, extra=1)


class IncomeForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.user)

    class Meta:
        model = Income
        fields = [
            "date",
            "amount",
            "source",
            "payer",
            "category",
            "notes",
        ]


class RecurringPurchaseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.user)
        self.fields["category"].empty_label = "Category"
        
        # Add placeholders and styling
        self.fields["name"].widget.attrs.update(placeholder="Name")
        self.fields["amount"].widget.attrs.update(placeholder="Amount")
        self.fields["merchant"].widget.attrs.update(placeholder="Merchant")
        self.fields["notes"].widget.attrs.update(placeholder="Notes", rows="2")

    class Meta:
        model = RecurringPurchase
        fields = [
            "name",
            "amount",
            "category",
            "merchant",
            "notes",
            "is_active",
        ]
