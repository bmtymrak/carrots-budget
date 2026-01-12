from django.forms import ModelForm, CharField, IntegerField, modelformset_factory
from django.core.exceptions import ValidationError
import datetime

from .models import MonthlyBudget, YearlyBudget, BudgetItem
from purchases.models import Category


class YearlyBudgetForm(ModelForm):
    year = IntegerField(
        min_value=2000,
        max_value=2100,
        help_text="Enter the year for the budget (e.g., 2024)"
    )
    
    class Meta:
        model = YearlyBudget
        fields = []
    
    def clean_year(self):
        year = self.cleaned_data['year']
        # Check if a yearly budget already exists for this year and user
        if hasattr(self, 'instance') and self.instance.user:
            if YearlyBudget.objects.filter(user=self.instance.user, date__year=year).exists():
                raise ValidationError(f"A yearly budget for {year} already exists.")
        return year
    
    def save(self, commit=True):
        # Convert year to a date (using January 1st of that year)
        year = self.cleaned_data['year']
        self.instance.date = datetime.date(year, 1, 1)
        return super().save(commit=commit)


class BudgetItemForm(ModelForm):

    new_category = CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.user)

    class Meta:
        model = BudgetItem
        fields = ["category", "new_category", "amount", "savings", "notes"]


BudgetItemFormset = modelformset_factory(BudgetItem, fields=("amount",), extra=0)
