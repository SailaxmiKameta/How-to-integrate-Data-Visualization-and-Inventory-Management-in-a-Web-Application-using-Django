import pandas as pd
import numpy as np
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
    store_data = merged_data[merged_data['Store'] == 1]

    store_data.set_index('Date', inplace=True)
    store_data = store_data[store_data['Open'] == 1]
    store_data.index = pd.to_datetime(store_data.index)

    store_data = store_data.asfreq('D')

    # Fill missing values
    store_data['Sales'] = store_data['Sales'].ffill()
    store_data[['Promo', 'StateHoliday', 'SchoolHoliday']] = store_data[['Promo', 'StateHoliday', 'SchoolHoliday']].ffill()

    store_data = store_data[['Sales', 'Promo', 'StateHoliday', 'SchoolHoliday']]
    store_data = store_data.replace([np.inf, -np.inf], np.nan).dropna()

    return store_data

def evaluate_arima_model(train, test, train_exog, test_exog):
    train_log = np.log1p(train)

    best_arima = auto_arima(train_log, seasonal=False, stepwise=True, trace=True, exogenous=train_exog)

    model = ARIMA(train_log, order=best_arima.order, exog=train_exog)
    model_fit = model.fit()

    forecast_log = model_fit.forecast(steps=len(test), exog=test_exog)
    forecast = np.expm1(forecast_log)

    error = rmse(test, forecast)
    print(f"Best ARIMA Model: {best_arima.order} with RMSE: {error:.2f}")

    return model_fit, forecast, error

def forecast_next_30_days(model_fit, last_train_data, train_exog, forecast_steps=30):
    forecast_dates = pd.date_range(start=last_train_data.index[-1] + pd.Timedelta(days=1), periods=forecast_steps)

    exog_forecast = pd.DataFrame({
        'Promo': [0] * forecast_steps,
        'StateHoliday': [0] * forecast_steps,
        'SchoolHoliday': [0] * forecast_steps
    }, index=forecast_dates)

    for col in exog_forecast.columns:
        exog_forecast[col] = exog_forecast[col].astype(train_exog[col].dtype)

    forecast_log = model_fit.forecast(steps=forecast_steps, exog=exog_forecast)
    forecast = np.expm1(forecast_log)

    forecast_df = pd.DataFrame(forecast, index=forecast_dates, columns=['Forecasted Sales'])

    return forecast_df

def plot_forecast(test, forecast, best_rmse, forecast_30_days=None):
    plt.figure(figsize=(12, 6))
    plt.plot(test.index, test, label='Actual Sales', color='blue')
    plt.plot(test.index, forecast, label='Predicted Sales', color='red')

    if forecast_30_days is not None:
        plt.plot(forecast_30_days.index, forecast_30_days['Forecasted Sales'], label='30-Day Forecast', color='green', linestyle='--')
        print(forecast_30_days)

    plt.title(f'ARIMA Sales Forecasting with RMSE: {best_rmse:.2f}')
    plt.xlabel('Date')
    plt.ylabel('Sales')
    plt.legend()
    plt.tight_layout()
    plt.savefig("arima_forecast_plot.png")  # Optional: save plot
    plt.show()
