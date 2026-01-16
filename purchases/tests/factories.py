import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory
from factory import fuzzy
import datetime

from purchases.models import Category, Subcategory, Purchase, Income, RecurringPurchase

class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ('name', 'user')

    name = factory.Sequence(lambda n: f'Category {n}')
    rollover = False
    notes = factory.Faker('text', max_nb_chars=200)
    user = factory.SubFactory(UserFactory)

class SubcategoryFactory(DjangoModelFactory):
    class Meta:
        model = Subcategory
        django_get_or_create = ('name', 'user')

    name = factory.Sequence(lambda n: f'Subcategory {n}')
    user = factory.SubFactory(UserFactory)

class PurchaseFactory(DjangoModelFactory):
    class Meta:
        model = Purchase

    item = factory.Faker('word')
    date = factory.LazyFunction(datetime.date.today)
    user = factory.SubFactory(UserFactory)
    amount = fuzzy.FuzzyDecimal(0, 1000, precision=2)
    source = factory.Faker('company')
    location = factory.Faker('city')
    category = factory.SubFactory(CategoryFactory)
    subcategory = factory.SubFactory(SubcategoryFactory)
    notes = factory.Faker('text', max_nb_chars=200)
    savings = False

class IncomeFactory(DjangoModelFactory):
    class Meta:
        model = Income

    user = factory.SubFactory(UserFactory)
    amount = fuzzy.FuzzyDecimal(1000, 10000, precision=2)
    date = factory.LazyFunction(datetime.date.today)
    source = factory.Faker('company')
    payer = factory.Faker('company')
    category = factory.SubFactory(CategoryFactory)
    notes = factory.Faker('text', max_nb_chars=200)


class RecurringPurchaseFactory(DjangoModelFactory):
    class Meta:
        model = RecurringPurchase

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Recurring Purchase {n}')
    amount = fuzzy.FuzzyDecimal(10, 500, precision=2)
    category = factory.SubFactory(CategoryFactory)
    merchant = factory.Faker('company')
    notes = factory.Faker('text', max_nb_chars=200)
    is_active = True