# Generated by Django 5.0.4 on 2025-04-28 04:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory_dashboard', '0007_remove_inventory_category_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventory',
            name='category_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
