from django.forms import ModelForm, CharField, modelformset_factory

from .models import MonthlyBudget, YearlyBudget, BudgetItem
from purchases.models import Category


class YearlyBudgetForm(ModelForm):
    class Meta:
        model = YearlyBudget
        fields = ["date"]


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
