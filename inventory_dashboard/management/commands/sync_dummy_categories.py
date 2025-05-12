# File: inventory_dashboard/management/commands/sync_dummy_inventory.py

from django.core.management.base import BaseCommand
from inventory_dashboard.models import DummyCategoryInventory, Inventory

class Command(BaseCommand):
    help = 'Sync DummyCategoryInventory into Inventory with category names'

    def handle(self, *args, **kwargs):
        dummies = DummyCategoryInventory.objects.all()
        
        if not dummies.exists():
            self.stdout.write(self.style.WARNING('No DummyCategoryInventory records found.'))
            return

        for dummy in dummies:
            inventory, created = Inventory.objects.update_or_create(
                store=dummy.store,
                category_name=dummy.category_name,  # Important: you must have category_name field in Inventory now
                defaults={
                    'quantity': dummy.quantity,
                    'last_updated': dummy.last_updated,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created Inventory for '{dummy.category_name}' at Store {dummy.store.store_id}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"🔄 Updated Inventory for '{dummy.category_name}' at Store {dummy.store.store_id}"))
