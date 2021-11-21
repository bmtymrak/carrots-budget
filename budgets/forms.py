from django.forms import ModelForm, CharField
from .models import BudgetItem

from .models import MonthlyBudget
from purchases.models import Category


class BudgetItemForm(ModelForm):

    new_category = CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(
            user=self.request.user
        )

    class Meta:
        model = BudgetItem
        fields = ["category", "new_category", "amount", "savings", "notes"]

