from django.db import models
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=250, blank=False)
    rollover = models.BooleanField(null=False)
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


class Purchase(models.Model):
    item = models.CharField(max_length=250, blank=True)
    date = models.DateField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purchases",
        null=False,
    )
    amount = models.IntegerField(blank=True, null=True)
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

    def __str__(self):
        return self.item
