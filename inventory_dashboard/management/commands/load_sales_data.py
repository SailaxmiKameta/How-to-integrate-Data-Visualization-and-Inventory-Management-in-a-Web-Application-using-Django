import pandas as pd
from django.core.management.base import BaseCommand
from inventory_dashboard.models import Sales, Store
from django.db import transaction

class Command(BaseCommand):
    help = "Efficiently load sales data from a large CSV file using batch inserts"

    def handle(self, *args, **kwargs):
        file_path = r"C:\Users\laxmi\Downloads\rossman_sales\train.csv"  # Update if needed
        chunk_size = 10_000  # Process data in chunks to optimize memory usage
        
        # Load store IDs into a dictionary for fast lookup
        store_ids = set(Store.objects.values_list("store_id", flat=True))

        # Read CSV in chunks
        chunk_iter = pd.read_csv(file_path, low_memory=False, chunksize=chunk_size, parse_dates=["Date"])

        total_inserted = 0
        sales_batch = []  # Store batch data before bulk insert
        
        for chunk in chunk_iter:
            chunk.fillna({
                "Sales": 0, "Customers": 0, "Open": 1, "Promo": 0, 
                "StateHoliday": "NA", "SchoolHoliday": 0
            }, inplace=True)
            
            for _, row in chunk.iterrows():
                if row["Store"] not in store_ids:  
                    continue  # Skip if store does not exist

                sales_batch.append(
                    Sales(
                        store_id=row["Store"],
                        day_of_week=int(row["DayOfWeek"]),
                        date=row["Date"].date(),  # Convert datetime to date
                        sales=int(row["Sales"]),
                        customers=int(row["Customers"]),
                        open=int(row["Open"]),  # Store as 0 or 1
                        promo=int(row["Promo"]),  # Store as 0 or 1
                        state_holiday=row["StateHoliday"] if row["StateHoliday"] in ["a", "b", "c", "0"] else "NA",
                        school_holiday=int(row["SchoolHoliday"])  # Store as 0 or 1
                    )
                )

                # Bulk insert in batches
                if len(sales_batch) >= chunk_size:
                    with transaction.atomic():  # Use atomic transaction for efficiency
                        Sales.objects.bulk_create(sales_batch)
                    total_inserted += len(sales_batch)
                    self.stdout.write(f"Inserted {total_inserted} records...")
                    sales_batch = []  # Clear batch for next iteration

        # Insert any remaining data
        if sales_batch:
            with transaction.atomic():
                Sales.objects.bulk_create(sales_batch)
            total_inserted += len(sales_batch)

        self.stdout.write(self.style.SUCCESS(f"Successfully loaded {total_inserted} sales records!"))
