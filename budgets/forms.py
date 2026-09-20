from django.forms import (
    Form,
    DecimalField,
    IntegerField,
    ModelForm,
    CharField,
    ChoiceField,
    TextInput,
    modelformset_factory,
)
from django.core.exceptions import ValidationError
import datetime
import re

from .models import YearlyBudget, BudgetItem, ExpenseSource
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

    new_category = CharField(required=False, max_length=250)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.user)

    def clean(self):
        cleaned_data = super().clean()
        if "category" in self.errors or "new_category" in self.errors:
            return cleaned_data
        category = cleaned_data.get("category")
        new_category = cleaned_data.get("new_category")
        if not category and not new_category:
            self.add_error("category", "Choose an existing category or enter a new category name.")
            self.add_error("new_category", "Enter a new category name or choose an existing category.")
        elif category and new_category:
            self.add_error("category", "Choose only one category option.")
            self.add_error("new_category", "Clear the new name to use the existing category.")
        return cleaned_data

    class Meta:
        model = BudgetItem
        fields = ["category", "new_category", "amount", "savings", "notes"]


class BudgetItemEditForm(ModelForm):
    """Editing supports existing categories only; creation replicates a year."""

    class Meta:
        model = BudgetItem
        fields = ["category", "amount", "savings", "notes"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["category"].required = True

    def clean(self):
        cleaned_data = super().clean()
        if "new_category" in self.data:
            self.add_error("category", "Choose an existing category. New categories can only be added when creating a budget item.")
        return cleaned_data


class RolloverYearField(IntegerField):
    def to_python(self, value):
        # IntegerField otherwise accepts integral floats and decimal strings.
        if type(value) is not int and not (
            isinstance(value, str) and re.fullmatch(r"[0-9]{1,4}", value)
        ):
            raise ValidationError("Enter a whole-number year from 1 to 9999.", code="invalid")
        return super().to_python(value)


class RolloverCategoryField(CharField):
    def to_python(self, value):
        if not isinstance(value, str):
            raise ValidationError("Enter an existing category name.", code="invalid")
        return super().to_python(value)


class RolloverUpdateForm(Form):
    amount = DecimalField(max_digits=12, decimal_places=2)
    category = RolloverCategoryField(max_length=250, strip=False)
    year = RolloverYearField(min_value=1, max_value=9999)


class ExpenseSourceForm(ModelForm):
    class Meta:
        model = ExpenseSource
        fields = ["name"]
        labels = {"name": "Statement or account name"}
        widgets = {
            "name": TextInput(
                attrs={
                    "placeholder": "e.g. Bank statement",
                    "autocomplete": "off",
                }
            )
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = ExpenseSource.normalize_name(self.cleaned_data["name"])
        duplicate_exists = (
            ExpenseSource.objects.filter(
                user=self.user,
                name__iexact=name,
            )
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if duplicate_exists:
            raise ValidationError("You already have an expense source with this name.")
        return name


BudgetItemFormset = modelformset_factory(BudgetItem, fields=("amount",), extra=0)
