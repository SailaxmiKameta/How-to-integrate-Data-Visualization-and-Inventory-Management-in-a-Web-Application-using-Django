import pandas as pd
from django.core.management.base import BaseCommand
from inventory_dashboard.models import Store  # Import your Store model

class Command(BaseCommand):
    help = 'Update existing store data in the database'

    def handle(self, *args, **kwargs):
        file_path = r"C:\Users\laxmi\Downloads\rossman_sales\store.csv"  # Update with actual path

        # Load the CSV file
        df = pd.read_csv(file_path)

        # Fill missing values
        df.fillna({
            "CompetitionDistance": 0, "CompetitionOpenSinceMonth": 0, 
            "CompetitionOpenSinceYear": 0, "Promo2": 0, "Promo2SinceWeek": 0, 
            "Promo2SinceYear": 0, "PromoInterval": "NA"
        }, inplace=True)

        df["StoreType"].fillna("NA", inplace=True)
        df["Assortment"].fillna("NA", inplace=True)

        df["Promo2"] = df["Promo2"].apply(lambda x: int(x) if x in [0, 1] else 0)


        # Iterate through each row and update only existing stores
        for _, row in df.iterrows():
            try:
                Store.objects.update_or_create(
                    store_id=row["Store"],
                    defaults={
                        'store_type': row["StoreType"],
                        'assortment': row["Assortment"],
                        'competition_distance': int(row["CompetitionDistance"]),
                        'competition_open_since_month': int(row["CompetitionOpenSinceMonth"]),
                        'competition_open_since_year': int(row["CompetitionOpenSinceYear"]),
                        'promo2': int(row["Promo2"]),
                        'promo2_since_week': int(row["Promo2SinceWeek"]),
                        'promo2_since_year': int(row["Promo2SinceYear"]),
                        'promo_interval': row["PromoInterval"]
                    }
                )
                
                self.stdout.write(self.style.SUCCESS(f"Updated store {row['Store']}"))

            except Store.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Store {row['Store']} not found. Skipping."))
