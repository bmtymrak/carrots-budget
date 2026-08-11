from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Purchase, Receipt


@receiver(post_delete, sender=Purchase)
def delete_orphaned_receipt(sender, instance, **kwargs):
    if instance.receipt_id:
        Receipt.objects.filter(pk=instance.receipt_id, purchases__isnull=True).delete()
