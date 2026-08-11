from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Purchase, Receipt


def _validate_purchase_user(user, purchase):
    if purchase.user_id not in (None, user.pk):
        raise ValidationError("Purchase belongs to a different user.")
    purchase.user = user


def save_purchases_with_receipts(user, purchases):
    """Save purchases under one receipt using the first row's metadata."""
    purchases = list(purchases)
    if not purchases:
        return []

    for purchase in purchases:
        _validate_purchase_user(user, purchase)

    first_purchase = purchases[0]

    with transaction.atomic():
        receipt = Receipt.objects.create(
            user=user,
            date=first_purchase.date,
            source=first_purchase.source,
            location=first_purchase.location,
        )
        for purchase in purchases:
            purchase.receipt = receipt
            purchase.source = first_purchase.source
            purchase.location = first_purchase.location
            purchase.save()

    return [receipt]


def save_purchases_with_individual_receipts(user, purchases):
    """Save each purchase with its own receipt in one atomic batch."""
    purchases = list(purchases)
    if not purchases:
        return []

    for purchase in purchases:
        _validate_purchase_user(user, purchase)

    receipts = []
    with transaction.atomic():
        for purchase in purchases:
            receipt = Receipt.objects.create(
                user=user,
                date=purchase.date,
                source=purchase.source,
                location=purchase.location,
            )
            purchase.receipt = receipt
            purchase.save()
            receipts.append(receipt)

    return receipts


def save_receipt_with_purchases(receipt, purchases):
    """Save receipt details and all of its purchases atomically."""
    purchases = list(purchases)
    if not purchases:
        return receipt

    for purchase in purchases:
        _validate_purchase_user(receipt.user, purchase)
        if purchase.receipt_id != receipt.pk:
            raise ValidationError("Purchase does not belong to this receipt.")

    with transaction.atomic():
        locked_receipt = Receipt.objects.select_for_update().get(
            pk=receipt.pk,
            user_id=receipt.user_id,
        )
        expected_ids = set(
            Purchase.objects.filter(
                user_id=receipt.user_id,
                receipt_id=locked_receipt.pk,
            ).values_list("pk", flat=True)
        )
        submitted_ids = {purchase.pk for purchase in purchases}
        if submitted_ids != expected_ids:
            raise ValidationError(
                "All purchases on this receipt must be submitted together."
            )

        locked_receipt.date = receipt.date
        locked_receipt.source = receipt.source
        locked_receipt.location = receipt.location
        locked_receipt.save()

        for purchase in purchases:
            purchase.date = locked_receipt.date
            purchase.source = locked_receipt.source
            purchase.location = locked_receipt.location
            purchase.save()

    return receipt


def save_purchase_with_receipt(purchase):
    """Save an edited purchase and keep its receipt metadata in sync."""
    with transaction.atomic():
        if not purchase.receipt_id:
            purchase.save()
            return purchase

        receipt = Receipt.objects.select_for_update().get(
            pk=purchase.receipt_id,
            user_id=purchase.user_id,
        )
        purchase.save()
        Receipt.objects.filter(pk=receipt.pk).update(
            date=purchase.date,
            source=purchase.source,
            location=purchase.location,
            updated_at=timezone.now(),
        )
        Purchase.objects.filter(receipt_id=receipt.pk).exclude(pk=purchase.pk).update(
            date=purchase.date,
            source=purchase.source,
            location=purchase.location,
            updated_at=timezone.now(),
        )
        return purchase
