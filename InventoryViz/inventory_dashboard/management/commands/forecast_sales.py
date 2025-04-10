from django.core.management.base import BaseCommand
from inventory_dashboard.arima_forecast import (
    load_and_preprocess_data,
    evaluate_arima_model,
    plot_forecast,
    forecast_next_30_days,
)

class Command(BaseCommand):
    help = 'Runs ARIMA model for sales forecasting'

    def handle(self, *args, **kwargs):
        data_path = 'C:/Users/laxmi/Downloads/rossman_sales'

        self.stdout.write(self.style.SUCCESS("Loading and preprocessing data..."))
        store_data = load_and_preprocess_data(data_path)

        # Split data into train/test
        train_size = int(len(store_data) * 0.8)
        train, test = store_data['Sales'][:train_size], store_data['Sales'][train_size:]

        # Exogenous features
        exog_features = ["Promo", "StateHoliday", "SchoolHoliday"]
        train_exog = store_data[exog_features][:train_size].copy()
        test_exog = store_data[exog_features][train_size:].copy()

        # Map StateHoliday to numeric values with safer mapping
        mapping = {"0": 0, "a": 1, "b": 2, "c": 3}
        train_exog["StateHoliday"] = train_exog["StateHoliday"].map(mapping).fillna(0).astype(float)
        test_exog["StateHoliday"] = test_exog["StateHoliday"].map(mapping).fillna(0).astype(float)

        self.stdout.write(self.style.SUCCESS("Evaluating ARIMA model..."))
        best_model, best_forecast, best_rmse = evaluate_arima_model(train, test, train_exog, test_exog)

        self.stdout.write(self.style.SUCCESS("Forecasting next 30 days..."))
        forecast_next_30_days_df = forecast_next_30_days(best_model, store_data[:train_size], train_exog)

        self.stdout.write(self.style.SUCCESS("Plotting forecast..."))
        plot_forecast(test, best_forecast, best_rmse, forecast_next_30_days_df)

        self.stdout.write(self.style.SUCCESS(f"ARIMA Sales Forecasting completed with RMSE: {best_rmse:.2f}"))
