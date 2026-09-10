import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from purchases.models import Purchase, Receipt
from purchases.services import (
    save_purchase_with_receipt,
    save_purchases_with_individual_receipts,
    save_purchases_with_receipts,
    save_receipt_with_purchases,
)


User = get_user_model()


class PurchaseReceiptServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="receipt-service-user",
            email="receipt-service@example.com",
            password="testpass123",
        )
        cls.other_user = User.objects.create_user(
            username="other-receipt-service-user",
            email="other-receipt-service@example.com",
            password="testpass123",
        )
        cls.old_date = datetime.date(2024, 1, 1)
        cls.new_date = datetime.date(2024, 2, 1)

    def _new_purchase(self, user, item="Purchase", source="Store", location="City"):
        return Purchase(
            user=user,
            item=item,
            date=self.old_date,
            amount=Decimal("10.00"),
            source=source,
            location=location,
        )

    def _receipt_with_purchases(self):
        receipt = Receipt.objects.create(
            user=self.user,
            date=self.old_date,
            source="Old Store",
            location="Old City",
        )
        first = Purchase.objects.create(
            user=self.user,
            receipt=receipt,
            item="First",
            date=self.old_date,
            amount=Decimal("10.00"),
            source="Old Store",
            location="Old City",
        )
        second = Purchase.objects.create(
            user=self.user,
            receipt=receipt,
            item="Second",
            date=self.old_date,
            amount=Decimal("20.00"),
            source="Old Store",
            location="Old City",
        )
        return receipt, first, second

    def test_grouping_services_create_their_documented_receipts(self):
        grouped = [
            self._new_purchase(self.user, "Grouped first", "First store", "First city"),
            self._new_purchase(self.user, "Grouped second", "Second store", "Second city"),
        ]
        receipts = save_purchases_with_receipts(self.user, grouped)

        self.assertEqual(len(receipts), 1)
        grouped_receipt = receipts[0]
        grouped_rows = list(Purchase.objects.order_by("item"))
        self.assertEqual(
            [row.receipt_id for row in grouped_rows],
            [grouped_receipt.pk, grouped_receipt.pk],
        )
        self.assertEqual(
            [(row.source, row.location) for row in grouped_rows],
            [("First store", "First city"), ("First store", "First city")],
        )

        individual = [
            self._new_purchase(self.user, "Individual first", "First store", "First city"),
            self._new_purchase(self.user, "Individual second", "Second store", "Second city"),
        ]
        individual_receipts = save_purchases_with_individual_receipts(
            self.user, individual
        )

        self.assertEqual(len(individual_receipts), 2)
        individual_rows = list(Purchase.objects.order_by("item"))[2:]
        self.assertEqual(
            [row.receipt_id for row in individual_rows],
            [individual_receipts[0].pk, individual_receipts[1].pk],
        )
        self.assertEqual(
            [(row.source, row.location) for row in individual_rows],
            [("First store", "First city"), ("Second store", "Second city")],
        )

    def test_grouping_services_reject_empty_and_mixed_user_batches_without_writes(self):
        for save_service in (
            save_purchases_with_receipts,
            save_purchases_with_individual_receipts,
        ):
            with self.subTest(service=save_service.__name__):
                self.assertEqual(save_service(self.user, []), [])

                valid_purchase = self._new_purchase(self.user)
                foreign_purchase = self._new_purchase(self.other_user, "Foreign")
                with self.assertRaises(ValidationError):
                    save_service(self.user, [valid_purchase, foreign_purchase])

                self.assertEqual(Purchase.objects.count(), 0)
                self.assertEqual(Receipt.objects.count(), 0)

    def test_grouping_services_roll_back_everything_when_a_row_save_fails(self):
        original_save = Purchase.save

        for save_service in (
            save_purchases_with_receipts,
            save_purchases_with_individual_receipts,
        ):
            with self.subTest(service=save_service.__name__):
                purchases = [
                    self._new_purchase(self.user, "First"),
                    self._new_purchase(self.user, "Second"),
                ]
                save_count = 0

                def fail_on_second_save(instance, *args, **kwargs):
                    nonlocal save_count
                    save_count += 1
                    if save_count == 2:
                        raise RuntimeError("simulated row failure")
                    return original_save(instance, *args, **kwargs)

                with patch.object(Purchase, "save", new=fail_on_second_save):
                    with self.assertRaisesRegex(RuntimeError, "simulated row failure"):
                        save_service(self.user, purchases)

                self.assertEqual(save_count, 2)
                self.assertEqual(Purchase.objects.count(), 0)
                self.assertEqual(Receipt.objects.count(), 0)

    def test_receipt_update_rejects_incomplete_submission_without_mutation(self):
        receipt, first, second = self._receipt_with_purchases()
        receipt.date = self.new_date
        receipt.source = "New Store"
        receipt.location = "New City"

        with self.assertRaises(ValidationError):
            save_receipt_with_purchases(receipt, [first])

        receipt.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(Receipt.objects.count(), 1)
        self.assertEqual(Purchase.objects.filter(receipt=receipt).count(), 2)
        self.assertEqual(receipt.date, self.old_date)
        self.assertEqual(receipt.source, "Old Store")
        self.assertEqual(first.date, self.old_date)
        self.assertEqual(second.source, "Old Store")

    def test_receipt_update_rejects_duplicate_and_foreign_lines_without_mutation(self):
        receipt, first, second = self._receipt_with_purchases()
        foreign_receipt = Receipt.objects.create(
            user=self.user,
            date=self.old_date,
            source="Other Store",
            location="Other City",
        )
        foreign_line = Purchase.objects.create(
            user=self.user,
            receipt=foreign_receipt,
            item="Foreign line",
            date=self.old_date,
            amount=Decimal("30.00"),
            source="Other Store",
            location="Other City",
        )

        with self.assertRaises(ValidationError):
            save_receipt_with_purchases(receipt, [first, second, second])
        with self.assertRaises(ValidationError):
            save_receipt_with_purchases(receipt, [first, foreign_line])

        receipt.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(Receipt.objects.count(), 2)
        self.assertEqual(Purchase.objects.count(), 3)
        self.assertEqual(receipt.source, "Old Store")
        self.assertEqual(first.receipt_id, receipt.pk)
        self.assertEqual(second.receipt_id, receipt.pk)
        self.assertEqual(foreign_line.receipt_id, foreign_receipt.pk)

    def test_receipt_update_rolls_back_metadata_and_all_rows_on_failure(self):
        receipt, first, second = self._receipt_with_purchases()
        receipt.date = self.new_date
        receipt.source = "New Store"
        receipt.location = "New City"
        original_save = Purchase.save
        save_count = 0

        def fail_on_second_save(instance, *args, **kwargs):
            nonlocal save_count
            save_count += 1
            if save_count == 2:
                raise RuntimeError("simulated row failure")
            return original_save(instance, *args, **kwargs)

        with patch.object(Purchase, "save", new=fail_on_second_save):
            with self.assertRaisesRegex(RuntimeError, "simulated row failure"):
                save_receipt_with_purchases(receipt, [first, second])

        db_receipt = Receipt.objects.get(pk=receipt.pk)
        db_purchases = list(Purchase.objects.order_by("item"))
        self.assertEqual(save_count, 2)
        self.assertEqual(db_receipt.date, self.old_date)
        self.assertEqual(db_receipt.source, "Old Store")
        self.assertEqual(db_receipt.location, "Old City")
        self.assertEqual(
            [(purchase.date, purchase.source, purchase.location) for purchase in db_purchases],
            [
                (self.old_date, "Old Store", "Old City"),
                (self.old_date, "Old Store", "Old City"),
            ],
        )

    def test_legacy_receiptless_purchase_can_be_saved(self):
        purchase = self._new_purchase(self.user, "Legacy purchase")

        result = save_purchase_with_receipt(purchase)

        self.assertEqual(result.pk, purchase.pk)
        self.assertIsNone(result.receipt_id)
        self.assertEqual(Purchase.objects.count(), 1)
        self.assertEqual(Receipt.objects.count(), 0)

    def test_single_purchase_update_synchronizes_receipt_and_sibling_metadata(self):
        receipt, first, second = self._receipt_with_purchases()
        first.date = self.new_date
        first.source = "New Store"
        first.location = "New City"

        save_purchase_with_receipt(first)

        receipt.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(receipt.date, self.new_date)
        self.assertEqual(receipt.source, "New Store")
        self.assertEqual(receipt.location, "New City")
        self.assertEqual(first.date, self.new_date)
        self.assertEqual(second.date, self.new_date)
        self.assertEqual(second.source, "New Store")
        self.assertEqual(second.location, "New City")

    def test_deleting_one_sibling_preserves_receipt_until_last_sibling(self):
        receipt, first, second = self._receipt_with_purchases()

        first.delete()

        self.assertFalse(Purchase.objects.filter(pk=first.pk).exists())
        self.assertTrue(Purchase.objects.filter(pk=second.pk).exists())
        self.assertTrue(Receipt.objects.filter(pk=receipt.pk).exists())

        second.delete()

        self.assertFalse(Purchase.objects.filter(pk=second.pk).exists())
        self.assertFalse(Receipt.objects.filter(pk=receipt.pk).exists())
