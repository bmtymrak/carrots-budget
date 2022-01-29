# Generated by Django 3.2.4 on 2022-01-15 17:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('purchases', '0001_initial'),
        ('budgets', '0002_budgetitem_savings'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rollover',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True)),
                ('category', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='rollovers', to='purchases.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rollovers', to=settings.AUTH_USER_MODEL)),
                ('yearly_budget', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='rollovers', to='budgets.yearlybudget')),
            ],
        ),
        migrations.AddConstraint(
            model_name='rollover',
            constraint=models.UniqueConstraint(fields=('yearly_budget', 'category', 'user'), name='unique_rollover'),
        ),
    ]
