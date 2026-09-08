import datetime

from django.test import TestCase

from .factories import (
    BudgetItemFactory,
    MonthlyBudgetFactory,
    RolloverFactory,
    UserFactory,
)


class BudgetFactoryOwnershipTests(TestCase):
    def test_nested_objects_follow_explicit_user(self):
        user = UserFactory()
        month = MonthlyBudgetFactory(
            user=user,
            date=datetime.date(datetime.date.today().year, 1, 1),
        )
        budget_item = BudgetItemFactory(user=user, monthly_budget=month)
        rollover = RolloverFactory(user=user)

        self.assertEqual(month.yearly_budget.user, user)
        self.assertEqual(budget_item.category.user, user)
        self.assertEqual(budget_item.monthly_budget.user, user)
        self.assertEqual(budget_item.yearly_budget.user, user)
        self.assertEqual(rollover.yearly_budget.user, user)
        self.assertEqual(rollover.category.user, user)
