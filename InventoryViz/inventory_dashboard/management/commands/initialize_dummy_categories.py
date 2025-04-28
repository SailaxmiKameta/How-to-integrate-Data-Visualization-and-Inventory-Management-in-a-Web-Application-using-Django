# inventory_dashboard/management/commands/initialize_dummy_categories.py

from django.core.management.base import BaseCommand
from inventory_dashboard.models import Store, Inventory, DummyCategoryInventory
from inventory_dashboard.utils import get_dummy_category_split

class Command(BaseCommand):
    help = "Splits inventory into dummy categories dynamically based on store properties"

    def handle(self, *args, **kwargs):
        stores = Store.objects.all()

        for store in stores:
            try:
                inventory = Inventory.objects.get(store=store)
                total_quantity = inventory.quantity

                split = get_dummy_category_split(store)

                for category, fraction in split.items():
                    category_quantity = int(total_quantity * fraction)

                    DummyCategoryInventory.objects.update_or_create(
                        store=store,
                        category_name=category,
                        defaults={"quantity": category_quantity}
                    )

                self.stdout.write(self.style.SUCCESS(f"Dummy categories created for Store {store.store_id}."))

            except Inventory.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No inventory found for Store {store.store_id}. Skipping."))
