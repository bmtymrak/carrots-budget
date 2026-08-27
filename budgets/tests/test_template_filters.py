from decimal import Decimal

from django.test import SimpleTestCase

from budgets.templatetags.value_styles import negative_class


class NegativeClassFilterTests(SimpleTestCase):
    def test_returns_negative_class_only_for_values_below_zero(self):
        self.assertEqual(negative_class(Decimal("-0.01")), "value-negative")
        self.assertEqual(negative_class(-4), "value-negative")
        self.assertEqual(negative_class(0), "")
        self.assertEqual(negative_class(Decimal("12.50")), "")
        self.assertEqual(negative_class(None), "")
        self.assertEqual(negative_class("not a number"), "")
