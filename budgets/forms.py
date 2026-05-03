from django.forms import ModelForm, CharField, ChoiceField, modelformset_factory
from django.core.exceptions import ValidationError
import datetime

from .models import MonthlyBudget, YearlyBudget, BudgetItem
from purchases.models import Category


# Constants for year selection range
MIN_YEAR = 2000
FUTURE_YEARS_OFFSET = 10


class YearlyBudgetForm(ModelForm):
    year = ChoiceField(
        choices=[],
        label="Budget Year"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = datetime.date.today().year
        # Generate year choices in descending order (most recent first)
        year_choices = [(year, str(year)) for year in range(current_year + FUTURE_YEARS_OFFSET, MIN_YEAR - 1, -1)]
        self.fields['year'].choices = year_choices
        self.fields['year'].initial = current_year
    
    class Meta:
        model = YearlyBudget
        fields = []
    
    def clean_year(self):
        year = int(self.cleaned_data['year'])
        # Check if a yearly budget already exists for this year and user
        if hasattr(self, 'instance') and self.instance.user:
            if YearlyBudget.objects.filter(user=self.instance.user, date__year=year).exists():
                raise ValidationError(f"A yearly budget for {year} already exists.")
        return year
    
    def save(self, commit=True):
        # Convert year to a date (using January 1st of that year)
        year = int(self.cleaned_data['year'])
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
