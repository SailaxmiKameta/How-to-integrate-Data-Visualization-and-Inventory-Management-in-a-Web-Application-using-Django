# Generated by Django 5.0.4 on 2025-04-28 04:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory_dashboard', '0006_alter_dummycategoryinventory_category_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inventory',
            name='category_name',
        ),
    ]
