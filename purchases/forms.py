from django import forms
from django.forms import BaseFormSet, ModelForm, formset_factory, modelformset_factory

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
        
        self.fields["item"].widget.attrs.update(placeholder="Item", size="20")
        self.fields["amount"].widget.attrs.update(placeholder="Amount")
        self.fields["source"].widget.attrs.update(placeholder="Source", size="20")
        self.fields["location"].widget.attrs.update(placeholder="Location", size="20")
        self.fields["notes"].widget.attrs.update(placeholder="Notes", rows="2", cols="30")

    class Meta:
        model = RecurringPurchase
        fields = [
            "item",
            "amount",
            "category",
            "source",
            "location",
            "notes",
            "is_active",
        ]


class RecurringPurchaseAddRowForm(forms.Form):
    selected = forms.BooleanField(required=False)
    recurring_purchase_id = forms.IntegerField(widget=forms.HiddenInput)
    date = forms.DateField(required=False)
    amount = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=12,
        decimal_places=2,
    )
    source = forms.CharField(required=False)
    location = forms.CharField(required=False)
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)
    notes = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.recurring_purchase = kwargs.pop("recurring_purchase")
        self.purchase_date = kwargs.pop("purchase_date")
        self.already_added = kwargs.pop("already_added", False)
        self.existing_details = kwargs.pop("existing_details", None)
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = Category.objects.filter(user=self.user)
        self._configure_widgets()
        self._set_initial_values()

        if self.already_added:
            for field_name in ["selected", "date", "amount", "source", "location", "category", "notes"]:
                self.fields[field_name].disabled = True

    def _configure_widgets(self):
        self.fields["date"].widget = forms.DateInput(
            attrs={"class": "recurring-input-date", "type": "date"}
        )
        self.fields["amount"].widget.attrs.update(
            {"class": "recurring-input-amount", "step": "0.01", "min": "0"}
        )
        self.fields["source"].widget.attrs.update({"class": "recurring-input-source"})
        self.fields["location"].widget.attrs.update({"class": "recurring-input-location"})
        self.fields["category"].widget.attrs.update({"class": "recurring-input-category"})
        self.fields["notes"].widget.attrs.update({"class": "recurring-input-notes"})

    def _set_initial_values(self):
        row_values = self.existing_details or {
            "date": self.purchase_date,
            "amount": self.recurring_purchase.amount,
            "source": self.recurring_purchase.source,
            "location": self.recurring_purchase.location,
            "category": self.recurring_purchase.category,
            "notes": self.recurring_purchase.notes,
        }

        self.initial.setdefault("selected", not self.already_added)
        self.initial.setdefault("recurring_purchase_id", self.recurring_purchase.id)
        self.initial.setdefault("date", row_values["date"])
        self.initial.setdefault("amount", row_values["amount"])
        self.initial.setdefault("source", row_values["source"])
        self.initial.setdefault("location", row_values["location"])
        self.initial.setdefault("category", row_values["category"])
        self.initial.setdefault("notes", row_values["notes"])

    def clean_recurring_purchase_id(self):
        recurring_purchase_id = self.cleaned_data["recurring_purchase_id"]
        if recurring_purchase_id != self.recurring_purchase.id:
            raise forms.ValidationError("Recurring purchase does not match this row.")
        return recurring_purchase_id

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("selected"):
            return cleaned_data

        for field_name in ["date", "category"]:
            if cleaned_data.get(field_name) in (None, ""):
                self.add_error(field_name, "This field is required.")

        submitted_date = cleaned_data.get("date")
        if submitted_date and (
            submitted_date.year != self.purchase_date.year
            or submitted_date.month != self.purchase_date.month
        ):
            self.add_error(
                "date",
                "Date must be within this budget's month and year.",
            )

        return cleaned_data

    def is_selected(self):
        return bool(self.cleaned_data.get("selected")) and not self.already_added

    def to_purchase_payload(self):
        return {
            "recurring_purchase": self.recurring_purchase,
            "date": self.cleaned_data["date"],
            "amount": self.cleaned_data["amount"],
            "source": self.cleaned_data["source"],
            "location": self.cleaned_data["location"],
            "category": self.cleaned_data["category"],
            "notes": self.cleaned_data["notes"],
        }


class BaseRecurringPurchaseAddToMonthFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.recurring_purchases = list(kwargs.pop("recurring_purchases"))
        self.purchase_date = kwargs.pop("purchase_date")
        self.already_added_details = kwargs.pop("already_added_details", {})

        kwargs.setdefault("initial", [{} for _ in self.recurring_purchases])
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        if index is None:
            return kwargs

        recurring_purchase = self.recurring_purchases[index]
        kwargs.update(
            {
                "user": self.user,
                "recurring_purchase": recurring_purchase,
                "purchase_date": self.purchase_date,
                "already_added": recurring_purchase.id in self.already_added_details,
                "existing_details": self.already_added_details.get(recurring_purchase.id),
            }
        )
        return kwargs

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        seen_recurring_ids = set()
        for form in self.forms:
            if not form.is_selected():
                continue

            recurring_purchase_id = form.cleaned_data["recurring_purchase_id"]
            if recurring_purchase_id in seen_recurring_ids:
                raise forms.ValidationError(
                    "Recurring purchases can only be added once per submission."
                )

            seen_recurring_ids.add(recurring_purchase_id)

    @property
    def selected_purchases(self):
        selected_purchases = []

        for form in self.forms:
            if not form.is_selected():
                continue

            selected_purchases.append(form.to_purchase_payload())

        return selected_purchases


RecurringPurchaseAddToMonthFormSet = formset_factory(
    RecurringPurchaseAddRowForm,
    formset=BaseRecurringPurchaseAddToMonthFormSet,
    extra=0,
)
