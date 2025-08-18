import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory
from factory import fuzzy
import datetime

from budgets.models import YearlyBudget, MonthlyBudget, BudgetItem, Rollover
from purchases.tests.factories import UserFactory, CategoryFactory

class YearlyBudgetFactory(DjangoModelFactory):
    class Meta:
        model = YearlyBudget
        django_get_or_create = ('date', 'user')

    user = factory.SubFactory(UserFactory)
    date = factory.LazyFunction(lambda: datetime.date(datetime.date.today().year, 1, 1))

class MonthlyBudgetFactory(DjangoModelFactory):
    class Meta:
        model = MonthlyBudget
        django_get_or_create = ('date', 'user')

    monthly = True
    date = factory.LazyFunction(datetime.date.today)
    expected_income = fuzzy.FuzzyDecimal(3000, 10000, precision=2)
    user = factory.SubFactory(UserFactory)
    yearly_budget = factory.SubFactory(YearlyBudgetFactory)

class BudgetItemFactory(DjangoModelFactory):
    class Meta:
        model = BudgetItem
        django_get_or_create = ('monthly_budget', 'category', 'user')

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    amount = fuzzy.FuzzyDecimal(0, 1000, precision=2)
    monthly_budget = factory.SubFactory(MonthlyBudgetFactory)
    yearly_budget = factory.SelfAttribute('monthly_budget.yearly_budget')
    notes = factory.Faker('text', max_nb_chars=200)
    savings = False

class RolloverFactory(DjangoModelFactory):
    class Meta:
        model = Rollover
        django_get_or_create = ('yearly_budget', 'category', 'user')

    user = factory.SubFactory(UserFactory)
    yearly_budget = factory.SubFactory(YearlyBudgetFactory)
    category = factory.SubFactory(CategoryFactory)
    amount = fuzzy.FuzzyDecimal(0, 1000, precision=2) 