from django.conf import settings
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error
from statsmodels.tools.eval_measures import rmse
from pmdarima import auto_arima
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def load_and_preprocess_data(data_path):
    train = pd.read_csv(f'{data_path}/train.csv', parse_dates=['Date'], dayfirst=False, low_memory=False)
    store = pd.read_csv(f'{data_path}/store.csv')
    merged_data = pd.merge(train, store, on='Store', how='left')
    return merged_data

def preprocess_store_data(store_data):
    store_data.set_index('Date', inplace=True)
    store_data = store_data[store_data['Open'] == 1]
    store_data.index = pd.to_datetime(store_data.index)
    store_data = store_data.asfreq('D')
    store_data['Sales'] = store_data['Sales'].ffill()
    store_data[['Promo', 'StateHoliday', 'SchoolHoliday']] = store_data[['Promo', 'StateHoliday', 'SchoolHoliday']].ffill()
    store_data = store_data[['Sales', 'Promo', 'StateHoliday', 'SchoolHoliday']]
    store_data = store_data.replace([np.inf, -np.inf], np.nan).dropna()
    return store_data


def evaluate_arima_model(train, test, train_exog, test_exog):
    train_log = np.log1p(train)
    best_arima = auto_arima(train_log, seasonal=False, stepwise=True, trace=False, exogenous=train_exog)
    model = ARIMA(train_log, order=best_arima.order, exog=train_exog)
    model_fit = model.fit()
    forecast_log = model_fit.forecast(steps=len(test), exog=test_exog)
    forecast = np.expm1(forecast_log)
    error = rmse(test, forecast)
    print(f"Best ARIMA Model: {best_arima.order} with RMSE: {error:.2f}")
    return model_fit, forecast, error

def forecast_next_30_days(model_fit, train_series, exog_df, log_transformed=True):
    last_date = train_series.index[-1]
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=30)
    exog_forecast = prepare_future_exog(exog_df, forecast_dates)
    forecast_log = model_fit.forecast(steps=30, exog=exog_forecast)
    forecast = np.expm1(forecast_log) if log_transformed else forecast_log
    forecast_df = pd.DataFrame({'Forecasted Sales': forecast.values}, index=forecast_dates)
    return forecast_df

def plot_forecast(test, forecast, best_rmse, forecast_30_days=None, store_id=None):
    plt.figure(figsize=(12, 6))
    plt.plot(test.index, test, label='Actual Sales', color='blue')
    plt.plot(test.index, forecast, label='Predicted Sales', color='red')

    if forecast_30_days is not None:
        plt.plot(forecast_30_days.index, forecast_30_days['Forecasted Sales'], label='30-Day Forecast', color='green', linestyle='--')

    plt.title(f'Store {store_id} - ARIMA Sales Forecast (RMSE: {best_rmse:.2f})')
    plt.xlabel('Date')
    plt.ylabel('Sales')
    plt.legend()
    #plt.tight_layout()
    #plt.savefig(f"arima_forecast_store_{store_id}.png")
    #plt.close()

    save_dir = os.path.join(settings.MEDIA_ROOT, 'forecast_plots')
    os.makedirs(save_dir, exist_ok=True)

    # Save the plot
    plot_path = os.path.join(save_dir, f'store_{store_id}_forecast.png')
    plt.savefig(plot_path)
    plt.close()


def prepare_future_exog(exog_df, forecast_dates):
    last_known = exog_df.iloc[-1]
    future_exog = pd.DataFrame([last_known] * len(forecast_dates), index=forecast_dates)
    return future_exog

def save_forecast_to_csv(forecast_30_days_df, store_id):
    save_dir = os.path.join(settings.MEDIA_ROOT, 'forecast_csv')
    os.makedirs(save_dir, exist_ok=True)  # Create dir if not exists

    file_path = os.path.join(save_dir, f'store_{store_id}_forecast.csv')

    # Ensure index is date-like for writing
    df_to_save = forecast_30_days_df.copy()
    df_to_save.reset_index(inplace=True)  # if index is datetime

    df_to_save.rename(columns={"index": "Date"}, inplace=True)

    df_to_save.to_csv(file_path, index=False)
    print(f"CSV saved for Store {store_id} at: {file_path}")
