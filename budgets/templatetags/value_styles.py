from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def negative_class(value):
    """Return the shared negative-value class for numeric template values."""
    if value is None or value == "":
        return ""

    try:
        return "value-negative" if Decimal(str(value)) < 0 else ""
    except (InvalidOperation, TypeError, ValueError):
        return ""
