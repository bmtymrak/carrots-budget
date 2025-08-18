from django.db import models
from django.conf import settings
from django.db.models.fields.related import ForeignKey


class Category(models.Model):
    name = models.CharField(db_index=True, max_length=250, blank=False)
    rollover = models.BooleanField(null=False, default=False)
    notes = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
        null=False,
        default=None,
    )

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name", "user"], name="unique_category")
        ]
        ordering = ["name"]


class Subcategory(models.Model):
    name = models.CharField(max_length=250, blank=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subcategories",
        null=False,
        default=None,
    )

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name", "user"], name="unique_subcategory")
        ]


class Purchase(models.Model):
    item = models.CharField(max_length=250, blank=True)
    date = models.DateField(db_index=True, null=True, default=None)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purchases",
        null=False,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    source = models.CharField(max_length=250, blank=True)
    location = models.CharField(max_length=250, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchases",
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchases",
    )
    notes = models.TextField(blank=True)
    savings = models.BooleanField(null=False, default=False)

    def __str__(self):
        return self.item
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'date'], name='idx_purchase_user_date'),
            models.Index(fields=['user', 'category', 'date'], name='idx_purchase_user_cat_date'),
            models.Index(fields=['category', 'date'], name='idx_purchase_category_date'),
        ]


class Income(models.Model):
    user = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incomes",
        null=False,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    source = models.CharField(max_length=250, blank=True)
    payer = models.CharField(max_length=250, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incomes",
    )
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'date'], name='idx_income_user_date'),
            models.Index(fields=['user', 'category', 'date'], name='idx_income_user_cat_date'),
        ]
