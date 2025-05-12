from django.core.management.base import BaseCommand
import pandas as pd
from inventory_dashboard.models import Store, Inventory  # Import the Store and Inventory models

class Command(BaseCommand):
    help = "Loads initial inventory data for each store based on past sales"

    def handle(self, *args, **kwargs):
        sales_file = r"C:/Users/laxmi/Downloads/rossman_sales/train.csv"

        try:
            sales_df = pd.read_csv(sales_file, low_memory=False)

            required_columns = {"Store", "Sales", "Date"}
            if not required_columns.issubset(sales_df.columns):
                self.stdout.write(self.style.ERROR("Missing required columns in sales data."))
                return

            # Clean and process the data
            sales_df["Date"] = pd.to_datetime(sales_df["Date"])
            sales_df = sales_df[sales_df["Sales"] > 0]  # Filter out days with no sales

            avg_sales_per_store = sales_df.groupby("Store")["Sales"].mean().round().astype(int)
            estimated_inventory = avg_sales_per_store * 30  # 30 days of avg sales

            stores = Store.objects.all()
            for store in stores:
                initial_quantity = estimated_inventory.get(store.store_id)

                if pd.isna(initial_quantity) or initial_quantity <= 0:
                    initial_quantity = estimate_stock_from_store_data(store)

                Inventory.objects.update_or_create(
                    store=store,
                    defaults={"quantity": int(initial_quantity)}
                )

            self.stdout.write(self.style.SUCCESS("Successfully initialized inventory based on sales data."))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {sales_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))


def estimate_stock_from_store_data(store):
    """
    Estimate initial stock based on store characteristics if sales data is missing.
    """
    base_stock = 500  # default

    if store.CompetitionDistance and store.CompetitionDistance < 500:
        base_stock += 200

    if store.Assortment == "a":
        base_stock += 300
    elif store.Assortment == "c":
        base_stock -= 100

    return base_stock
