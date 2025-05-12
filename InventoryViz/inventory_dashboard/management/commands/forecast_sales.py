import csv
from datetime import datetime
import os
from django.core.management.base import BaseCommand
import pandas as pd
from inventory_dashboard.models import Forecast
from inventory_dashboard.arima_forecast import (
    load_and_preprocess_data,
    evaluate_arima_model,
    plot_forecast,
    forecast_next_30_days,
    preprocess_store_data,
    save_forecast_to_csv,
)

class Command(BaseCommand):
    help = 'Runs ARIMA model for sales forecasting'

    def add_arguments(self, parser):
        parser.add_argument('--start', type=int, default=1, help='Start store index (inclusive)')
        parser.add_argument('--end', type=int, help='End store index (inclusive)')
        parser.add_argument('--store', type=int, help='Run forecast for a single store')

    def handle(self, *args, **options):
        data_path = 'C:/Users/laxmi/Downloads/rossman_sales'
        store_id = options.get('store')

        if store_id is None:
            self.stdout.write(self.style.ERROR("Please provide a --store id."))
            return

        checkpoint_file = 'forecast_checkpoint.csv'

        # Initialize checkpoint file if it doesn't exist
        if not os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Store', 'Status', 'RMSE', 'Timestamp'])

        # Load checkpoint
        checkpoints = pd.read_csv(checkpoint_file)

        # Check if this store is already completed
        if store_id in checkpoints['Store'].values:
            status = checkpoints[checkpoints['Store'] == store_id]['Status'].values[0]
            if status == 'completed':
                self.stdout.write(self.style.WARNING(f"Store {store_id} already completed. Skipping..."))
                return

        # Load data
        self.stdout.write(self.style.SUCCESS(f"Loading data for Store {store_id}..."))
        merged_data = load_and_preprocess_data(data_path)
        store_df = merged_data[merged_data['Store'] == store_id].copy()

        if store_df.empty:
            self._update_checkpoint(checkpoint_file, store_id, 'failed', None)
            self.stdout.write(self.style.WARNING(f"No data for Store {store_id}."))
            return

        store_data = preprocess_store_data(store_df)
        if store_data.empty or store_data['Sales'].isnull().all():
            self._update_checkpoint(checkpoint_file, store_id, 'failed', None)
            self.stdout.write(self.style.WARNING(f"Insufficient data for Store {store_id}."))
            return

        train_size = int(len(store_data) * 0.8)
        train, test = store_data['Sales'][:train_size], store_data['Sales'][train_size:]
        exog_features = ["Promo", "StateHoliday", "SchoolHoliday"]
        train_exog = store_data[exog_features][:train_size].copy()
        test_exog = store_data[exog_features][train_size:].copy()

        mapping = {"0": 0, "a": 1, "b": 2, "c": 3}
        train_exog["StateHoliday"] = train_exog["StateHoliday"].map(mapping).fillna(0).astype(float)
        test_exog["StateHoliday"] = test_exog["StateHoliday"].map(mapping).fillna(0).astype(float)

        try:
            model_fit, forecast, best_rmse = evaluate_arima_model(train, test, train_exog, test_exog)
            forecast_30_days_df = forecast_next_30_days(model_fit, store_data, train_exog)
            forecast_30_days_df['Store'] = store_id

            forecast_objs = [
                Forecast(store_id=store_id, date=row.name.date(), forecasted_sales=row['Forecasted Sales'])
                for _, row in forecast_30_days_df.iterrows()
            ]
            Forecast.objects.bulk_create(forecast_objs, ignore_conflicts=True)

            plot_forecast(test, forecast, best_rmse, forecast_30_days_df, store_id=store_id)
            save_forecast_to_csv(forecast_30_days_df, store_id)
            self._update_checkpoint(checkpoint_file, store_id, 'completed', best_rmse)

            self.stdout.write(self.style.SUCCESS(f"Store {store_id}: Forecast complete (RMSE: {best_rmse:.2f})"))
            
        except Exception as e:
            self._update_checkpoint(checkpoint_file, store_id, 'failed', None)
            self.stdout.write(self.style.ERROR(f"Store {store_id}: Forecasting failed. Reason: {e}"))


    def _update_checkpoint(self, filepath, store_id, status, rmse):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        row = [store_id, status, rmse if rmse else '', timestamp]

        if not os.path.exists(filepath):
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Store', 'Status', 'RMSE', 'Timestamp'])

        with open(filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
