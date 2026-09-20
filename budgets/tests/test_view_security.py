import datetime
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from budgets.models import BudgetItem, Rollover, YearlyBudget
from purchases.models import Category


User = get_user_model()


class BudgetEndpointSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="owner", email="owner@example.com"
        )
        cls.other_user = User.objects.create_user(
            username="other", email="other@example.com"
        )
        cls.other_yearly_budget = YearlyBudget.objects.create(
            user=cls.other_user, date=datetime.date(2024, 1, 1)
        )
        cls.other_monthly_budget = cls.other_yearly_budget.monthly_budgets.get(
            date=datetime.date(2024, 1, 1)
        )
        cls.other_category = Category.objects.create(
            user=cls.other_user, name="Private category"
        )
        cls.other_budget_item = BudgetItem.objects.create(
            user=cls.other_user,
            yearly_budget=cls.other_yearly_budget,
            monthly_budget=cls.other_monthly_budget,
            category=cls.other_category,
            amount=Decimal("100.00"),
            savings=False,
        )
        cls.other_rollover = Rollover.objects.create(
            user=cls.other_user,
            yearly_budget=cls.other_yearly_budget,
            category=cls.other_category,
            amount=Decimal("50.00"),
        )
        cls.yearly_budget = YearlyBudget.objects.create(
            user=cls.user, date=datetime.date(2025, 1, 1)
        )
        cls.monthly_budget = cls.yearly_budget.monthly_budgets.get(
            date=datetime.date(2025, 1, 1)
        )
        cls.category = Category.objects.create(user=cls.user, name="Food")
        cls.budget_item = BudgetItem.objects.create(
            user=cls.user,
            yearly_budget=cls.yearly_budget,
            monthly_budget=cls.monthly_budget,
            category=cls.category,
            amount=Decimal("100.00"),
            savings=False,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_foreign_budget_objects_are_not_accessible(self):
        urls = [
            reverse("yearly_detail", args=[2024]),
            reverse("budget_item_detail", args=[2024, 1, self.other_category.name]),
            reverse("budget_item_delete", args=[2024, 1, self.other_category.name]),
            reverse("budgetitem_edit_htmx", args=[2024, 1, self.other_category.name]),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_rollover_update_cannot_modify_another_users_rollover(self):
        response = self.client.post(
            reverse("rollover_update"),
            data=json.dumps(
                {
                    "amount": "999.00",
                    "category": self.other_category.name,
                    "year": 2024,
                }
            ),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 404)
        self.other_rollover.refresh_from_db()
        self.assertEqual(self.other_rollover.amount, Decimal("50.00"))

    def test_rollover_update_rejects_bad_requests(self):
        url = reverse("rollover_update")
        cases = [
            ({}, {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}),
            ("not json", {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}),
            (
                {"amount": "NaN", "category": "Anything", "year": 2024},
                {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
            ),
            (
                {"amount": "1.001", "category": "Anything", "year": 2024},
                {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
            ),
            (
                {"amount": "10000000000", "category": "Anything", "year": 2024},
                {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
            ),
            (
                {"amount": "1.00", "category": "Anything", "year": 10000},
                {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
            ),
        ]

        for data, headers in cases:
            with self.subTest(data=data, headers=headers):
                response = self.client.post(
                    url,
                    data=json.dumps(data) if not isinstance(data, str) else data,
                    content_type="application/json",
                    **headers,
                )
                self.assertEqual(response.status_code, 400)

        self.assertEqual(self.client.get(url).status_code, 405)

    def test_budget_item_create_without_next_uses_yearly_detail(self):
        response = self.client.get(reverse("budgetitem_create_htmx", args=[2025]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], reverse("yearly_detail", args=[2025]))

    def test_budget_item_modals_use_safe_default_return_urls(self):
        cases = [
            (
                reverse("budgetitem_edit_htmx", args=[2025, 1, self.category.name]),
                reverse("monthly_detail", args=[2025, 1]),
            ),
            (
                reverse("budgetitem_bulk_edit_htmx", args=[2025, self.category.name]),
                reverse("yearly_detail", args=[2025]),
            ),
            (
                reverse("budget_item_delete_htmx", args=[2025, self.category.name]),
                reverse("yearly_detail", args=[2025]),
            ),
        ]

        for url, expected_next in cases:
            with self.subTest(url=url):
                response = self.client.get(url, {"next": "https://example.org/leave"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["next"], expected_next)

    def test_yearly_create_rejects_external_return(self):
        response = self.client.post(reverse('yearly_create'), {'year': 2026, 'next': 'https://evil.test'})
        self.assertEqual(response['HX-Redirect'], reverse('yearly_list'))
        self.assertEqual(YearlyBudget.objects.get(user=self.user, date__year=2026).monthly_budgets.count(), 12)

    def test_monthly_create_route_is_removed(self):
        from django.urls import Resolver404, resolve
        with self.assertRaises(Resolver404):
            resolve('/budgets/monthly-create')

    def test_rollover_contract(self):
        rollover = Rollover.objects.create(user=self.user, category=self.category,
                                          yearly_budget=self.yearly_budget, amount='5.00')
        url = reverse('rollover_update')
        valid = {'amount': '-125.5', 'category': self.category.name, 'year': '2025'}
        response = self.client.post(url, json.dumps(valid), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'amount': '-125.50'})
        rollover.refresh_from_db()
        self.assertEqual(rollover.amount, Decimal('-125.50'))
        invalid_fields = {
            'year': [True, False, 2025.5, 2025.0, '2025.0', None, [], {}, 0, 10000],
            'amount': ['NaN', 'Infinity', '-Infinity', '1.001', '10000000000',
                       '-10000000000', None, True, [], {}],
            'category': [None, True, 123, [], {}, '', 'x' * 251],
        }
        for field, values in invalid_fields.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    response = self.client.post(url, json.dumps({**valid, field: value}), content_type='application/json')
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.json()['errors'])
                    rollover.refresh_from_db()
                    self.assertEqual(rollover.amount, Decimal('-125.50'))
        for body in ['{', '[]', 'null', '1', '"text"', b'\xff', '{"amount":1e99999999999999999999999}']:
            with self.subTest(body=body):
                response = self.client.post(url, body, content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('__all__', response.json()['errors'])

    def test_rollover_precision_edges_and_exact_category_names(self):
        category = Category.objects.create(user=self.user, name=' Food ')
        rollover = Rollover.objects.create(user=self.user, category=category,
                                          yearly_budget=self.yearly_budget, amount='0')
        for raw, expected in [('9999999999.99', '9999999999.99'), ('-9999999999.99', '-9999999999.99'),
                              ('0', '0.00'), ('1e2', '100.00')]:
            with self.subTest(raw=raw):
                # Raw JSON numbers must not be rounded through binary floating point.
                body = '{"amount":' + raw + ',"category":" Food ","year":2025}'
                response = self.client.post(reverse('rollover_update'), body, content_type='application/json')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'amount': expected})
        response = self.client.post(reverse('rollover_update'),
                                    '{"amount":0.10000000000000001,"category":" Food ","year":2025}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)
        rollover.refresh_from_db()
        self.assertEqual(rollover.amount, Decimal('100.00'))

    def test_rollover_missing_records_and_inconsistent_owners_are_404(self):
        from django.db import transaction
        for category, year in [(self.category, self.other_yearly_budget),
                               (self.other_category, self.yearly_budget)]:
            with self.subTest(category=category), transaction.atomic():
                rollover = Rollover.objects.create(user=self.user, category=category, yearly_budget=year, amount='5')
                response = self.client.post(reverse('rollover_update'), json.dumps({
                    'amount': '10', 'category': category.name, 'year': year.date.year,
                }), content_type='application/json')
                self.assertEqual(response.status_code, 404)
                rollover.refresh_from_db()
                self.assertEqual(rollover.amount, Decimal('5'))
                transaction.set_rollback(True)
        before = Rollover.objects.count()
        for category, year in [('Unknown', 2025), (self.category.name, 1), (self.category.name, 9999)]:
            response = self.client.post(reverse('rollover_update'), json.dumps({
                'amount': '10', 'category': category, 'year': year,
            }), content_type='application/json')
            self.assertEqual(response.status_code, 404)
        self.assertEqual(Rollover.objects.count(), before)

    def test_rollover_authentication_csrf_and_methods(self):
        from django.test import Client
        rollover = Rollover.objects.create(user=self.user, category=self.category,
                                          yearly_budget=self.yearly_budget, amount='5')
        url = reverse('rollover_update')
        body = json.dumps({'amount': '10', 'category': self.category.name, 'year': 2025})
        anonymous = Client()
        response = anonymous.post(url, body, content_type='application/json')
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=', response['Location'])
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(url, body, content_type='application/json').status_code, 403)
        csrf_client.get(reverse('yearly_create'))
        token = csrf_client.cookies['csrftoken'].value
        self.assertEqual(csrf_client.post(url, body, content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        for method in ['get', 'put', 'patch', 'delete']:
            self.assertEqual(getattr(self.client, method)(url).status_code, 405)
        rollover.refresh_from_db()
        self.assertEqual(rollover.amount, Decimal('10'))

    def test_budget_mutation_redirect_matrix(self):
        from django.db import transaction
        from urllib.parse import urlencode
        from budgets.models import ExpenseSource, MonthlyExpenseSource

        monthly = reverse('monthly_detail', args=[2025, 1])
        annual = reverse('yearly_detail', args=[2025])
        listing = reverse('yearly_list')
        source = ExpenseSource.objects.create(user=self.user, name='Bank')
        MonthlyExpenseSource.objects.create(expense_source=source, monthly_budget=self.monthly_budget)
        item_data = {'category': self.category.pk, 'amount': '10'}
        cases = [
            ('yearly_create', [], 'post', {'year': 2026}, listing, False),
            ('budgetitem_create_htmx', [2025], 'post', {'new_category': 'New', 'amount': '10'}, annual, False),
            ('budgetitem_edit_htmx', [2025, 1, self.category.name], 'post', item_data, monthly, False),
            ('budgetitem_bulk_edit_htmx', [2025, self.category.name], 'post', {
                'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '1',
                'form-0-id': self.budget_item.pk, 'form-0-amount': '12',
            }, annual, False),
            ('budget_item_delete_htmx', [2025, self.category.name], 'delete', {}, annual, False),
            ('budget_item_delete', [2025, 1, self.category.name], 'post', {}, listing, False),
            ('budget_item_delete', [2025, 1, self.category.name], 'post', {'delete-all': 'on'}, listing, False),
            ('expense_source_manage', [2025, 1], 'post', {'action': 'create', 'name': 'Card'}, monthly, True),
            ('expense_source_toggle', [2025, 1, source.pk], 'post', {'is_checked': 'on'}, monthly, True),
        ]
        for name, args, method, payload, fallback, exact in cases:
            destinations = [('https://evil.test/leave', fallback),
                            ('', fallback),
                            (fallback + '?filter=food&page=2', fallback + '?filter=food&page=2'),
                            ('/purchases/?search=food', fallback if exact else '/purchases/?search=food'),
                            ('http://testserver' + fallback + '?q=2', 'http://testserver' + fallback + '?q=2')]
            for destination, expected in destinations:
                with self.subTest(name=name, payload=payload, destination=destination), transaction.atomic():
                    url = reverse(name, args=args) + '?' + urlencode({'next': destination})
                    response = getattr(self.client, method)(url, payload)
                    header = 'HX-Redirect' if name not in {'budget_item_delete', 'expense_source_manage', 'expense_source_toggle'} else 'Location'
                    self.assertEqual(response.status_code, 200 if header == 'HX-Redirect' else 302)
                    self.assertEqual(response.get(header), expected)
                    transaction.set_rollback(True)
        # Explicit blank POST must win over an otherwise safe query destination.
        response = self.client.post(reverse('budgetitem_edit_htmx', args=[2025, 1, self.category.name]) + '?next=/other',
                                    {**item_data, 'next': ''})
        self.assertEqual(response['HX-Redirect'], monthly)
