import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from budgets.models import YearlyBudget
from purchases.models import Category, Income, Purchase, RecurringPurchase


User = get_user_model()


class TransactionEndpointSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="owner", email="owner@example.com"
        )
        cls.other_user = User.objects.create_user(
            username="other", email="other@example.com"
        )
        cls.other_category = Category.objects.create(
            user=cls.other_user, name="Other category"
        )
        cls.other_income = Income.objects.create(
            user=cls.other_user,
            amount="100.00",
            date=datetime.date(2024, 1, 1),
        )
        cls.other_purchase = Purchase.objects.create(
            user=cls.other_user,
            item="Private purchase",
            amount="20.00",
            date=datetime.date(2024, 1, 1),
            category=cls.other_category,
        )
        cls.other_recurring = RecurringPurchase.objects.create(
            user=cls.other_user,
            item="Private recurring purchase",
            amount="25.00",
            category=cls.other_category,
        )
        YearlyBudget.objects.create(
            user=cls.other_user, date=datetime.date(2024, 1, 1)
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_foreign_transactions_are_not_accessible(self):
        urls = [
            reverse("purchase_edit_htmx", args=[self.other_purchase.pk]),
            reverse("purchase_delete_htmx", args=[self.other_purchase.pk]),
            reverse("income_edit_htmx", args=[self.other_income.pk]),
            reverse("income_delete_htmx", args=[self.other_income.pk]),
            reverse("recurring_purchase_edit", args=[self.other_recurring.pk]),
            reverse("recurring_purchase_delete", args=[self.other_recurring.pk]),
            reverse("recurring_purchase_add_to_month", args=[2024, 1]),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_missing_and_external_next_urls_use_safe_defaults(self):
        response = self.client.get(reverse("income_create"))
        external_response = self.client.get(
            reverse("recurring_purchase_list"),
            {"next": "https://example.org/leave"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], reverse("yearly_list"))
        self.assertEqual(external_response.status_code, 200)
        self.assertEqual(external_response.context["next"], reverse("yearly_list"))

    def test_transaction_mutation_redirect_matrix(self):
        from django.db import transaction
        from urllib.parse import urlencode
        from purchases.models import Receipt
        from budgets.models import BudgetItem

        category = Category.objects.create(user=self.user, name='Food')
        year = YearlyBudget.objects.create(user=self.user, date=datetime.date(2025, 1, 1))
        BudgetItem.objects.create(user=self.user, category=category, yearly_budget=year,
                                  monthly_budget=year.monthly_budgets.get(date__month=1), amount='10', savings=False)
        purchase = Purchase.objects.create(user=self.user, item='Standalone', amount='10', date=year.date, category=category)
        receipt = Receipt.objects.create(user=self.user, date=year.date)
        receipt_purchase = Purchase.objects.create(user=self.user, receipt=receipt, item='Receipt item', amount='10', date=year.date, category=category)
        income = Income.objects.create(user=self.user, amount='10', date=year.date)
        recurring = RecurringPurchase.objects.create(user=self.user, item='Rent', amount='10', category=category)
        purchase_data = {'item': 'Updated', 'amount': '15', 'date': '2025-01-01', 'category': category.pk}
        formset_data = {'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '0',
                        **{f'form-0-{key}': value for key, value in purchase_data.items()}}
        income_data = {'amount': '15', 'date': '2025-01-01'}
        recurring_data = {'item': 'Rent', 'amount': '15', 'category': category.pk, 'is_active': 'on'}
        listing = reverse('yearly_list')
        purchases = reverse('purchase_list')
        cases = [
            ('purchase_create', [], 'post', formset_data, purchases),
            ('purchase_edit_htmx', [purchase.pk], 'post', purchase_data, purchases),
            ('purchase_edit_htmx', [receipt_purchase.pk], 'post', {
                **formset_data, 'date': '2025-01-01', 'form-INITIAL_FORMS': '1', 'form-0-id': receipt_purchase.pk,
            }, purchases),
            ('purchase_delete_htmx', [purchase.pk], 'delete', {}, purchases),
            ('income_create', [], 'post', income_data, listing),
            ('income_edit_htmx', [income.pk], 'post', income_data, listing),
            ('income_delete_htmx', [income.pk], 'delete', {}, listing),
            ('recurring_purchase_edit', [recurring.pk], 'post', recurring_data, listing),
            ('recurring_purchase_delete', [recurring.pk], 'delete', {}, listing),
            ('recurring_purchase_add_to_month', [2025, 1], 'post', {
                **formset_data, 'form-0-recurring_purchase_id': recurring.pk, 'form-0-selected': 'on',
            }, reverse('monthly_detail', args=[2025, 1])),
        ]
        for name, args, method, payload, fallback in cases:
            for destination in ['https://evil.test/leave', '', '/purchases/?search=food&page=2',
                                'http://testserver/budgets/2025?ytd=4']:
                for origin in (['query', 'post'] if method == 'post' else ['query']):
                    with self.subTest(name=name, args=args, destination=destination, origin=origin), transaction.atomic():
                        expected = fallback if not destination or destination.startswith('https://evil') else destination
                        url = reverse(name, args=args)
                        data = payload.copy()
                        if origin == 'post':
                            url += '?next=/query-must-not-win'
                            data['next'] = destination
                        else:
                            url += '?' + urlencode({'next': destination})
                        response = getattr(self.client, method)(url, data)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.get('HX-Redirect'), expected)
                        transaction.set_rollback(True)

    def test_recurring_create_preserves_only_safe_downstream_returns(self):
        from django.db import transaction
        from urllib.parse import urlencode
        from django.utils.html import escape
        category = Category.objects.create(user=self.user, name='Food')
        for destination, expected in [('https://evil.test', reverse('yearly_list')),
                                      ('', reverse('yearly_list')),
                                      ('/purchases/?search=food&page=2', '/purchases/?search=food&page=2')]:
            for method in ['get', 'post']:
                with self.subTest(destination=destination, method=method), transaction.atomic():
                    recurring = RecurringPurchase.objects.create(user=self.user, item='Original', amount='10', category=category)
                    response = getattr(self.client, method)(reverse('recurring_purchase_list'),
                                                            {'next': destination, 'item': 'New', 'amount': '15', 'category': category.pk})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.context['next'], expected)
                    self.assertContains(response, f'name="next" value="{escape(expected)}"')
                    for route_name in ['recurring_purchase_edit', 'recurring_purchase_delete']:
                        action = reverse(route_name, args=[recurring.pk]) + '?' + urlencode({'next': expected})
                        # Django's urlencode template filter preserves slashes.
                        self.assertContains(response, escape(action.replace('%2F', '/')))
                    if method == 'post':
                        self.assertTrue(RecurringPurchase.objects.filter(user=self.user, item='New').exists())
                    transaction.set_rollback(True)
