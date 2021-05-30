from __future__ import annotations

import warnings
from enum import Enum
from itertools import product
from typing import List

import pandas as pd
from pandas import DataFrame, Series
from fbprophet import Prophet as pr
from statsmodels.tsa.statespace.sarimax import SARIMAX

from tropicalia.logger import get_logger

logger = get_logger(__name__)


class AlgorithmStack(Enum):
    """
    Enumeration of all considered algorithms
    """

    SARIMA = "SARIMA"
    Prophet = "Prophet"


class MLAlgorithm:
    """
    Class representing the Machine Learning Algorithms
    """

    def train(self, df: DataFrame) -> MLAlgorithm:
        pass

    def predict(self, df: DataFrame) -> Series:
        pass

    def forecast(self, df: DataFrame) -> tuple(Series, Series):
        pass


class SARIMA(MLAlgorithm):
    """
    Class representing the Seasonal AutoRegressive Integrated Moving Average algorithm from statsmodels
    """

    def train(self, df: DataFrame):
        """
        Trains a SARIMA model with the best parameter configuration for the given data.

        Returns the fitted model.
        """
        configs = self.sarima_configs()
        best_config = self.evaluate_models(df, configs)
        fit_model = self.sarima_fit(df, best_config)

        return fit_model

    def predict(self, df: DataFrame, ml_model) -> Series:
        """
        Given a fitted model and the data, it performs a prediction to obtain validation data
        for the last 3 years of harvesting.

        - ml_model: A statsmodels SARIMA fitted model.

        Returns a pandas series of validation data.
        """
        last_year = df.index[-1]
        last3_years = pd.to_datetime(last_year) - pd.DateOffset(years=3) + pd.DateOffset(months=1)

        prediction = ml_model.get_prediction(start=pd.to_datetime(last3_years), dynamic=False)

        return prediction

    def forecast(self, df: DataFrame, is_monthly: bool, ml_model) -> tuple(Series, Series):
        """
        Given a fitted model, it performs a forecast for the next harvesting year.

        - ml_model: A statsmodels SARIMA fitted model.

        Returns a tuple of pandas Series: (last year values, forecasted values).
        """
        last_year = df.index[-1]
        start_date = pd.to_datetime(last_year) + pd.DateOffset(months=1)
        date_range = pd.date_range(start=start_date, periods=12, freq="MS")

        if is_monthly:
            forecast = ml_model.get_forecast(steps=1)
            return df["yield_values"].iloc[-12], forecast.predicted_mean

        forecast = ml_model.get_forecast(steps=12)
        forecast = forecast.predicted_mean

        forecast.index = date_range

        return (df["yield_values"].iloc[-12:], forecast)

    def fit(self, df: DataFrame, config: List[tuple]):
        """
        Method to train SARIMA given data and its parameters.

        Returns the fitted model.
        """
        order, s_order = config

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            model = SARIMAX(
                endog=df["yield_values"],
                order=order,
                seasonal_order=s_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            model_fit = model.fit(disp=False)

        return model_fit

    def configs(self, seasonality: int = 12) -> List[tuple]:
        """
        Method to get all posible parameter configurations for Grid Search.

        Returns a list of tuples with parameters
        """
        p_params = [0, 1, 2]
        d_params = [0, 1]
        q_params = [0, 1, 2, 3]
        P_params = [0, 1, 2]
        D_params = [0, 1]
        Q_params = [0, 1, 2, 3]

        configs = product(p_params, d_params, q_params, P_params, D_params, Q_params, [seasonality])

        return configs

    def evaluate_models(self, df: DataFrame, configs: List[tuple]) -> List[tuple]:
        """
        Evaluates all possible SARIMA parameters.

        Returns the best parameter selection.
        """
        best_score, best_cfg = float("inf"), None

        for config in configs:
            p, d, q, P_value, D_value, Q_value, seasonality = config
            order = (p, d, q)
            s_order = (P_value, D_value, Q_value, seasonality)
            try:
                aic = self.evaluate_sarima_model(df, order, s_order)
                if aic < best_score:
                    best_score, best_cfg = aic, [order, s_order]
            except Exception as err:
                logger.debug(f"SARIMA config {config} has raised an error.")
                logger.debug(err)
                continue

        return best_cfg

    def evaluate_sarima_model(self, df: DataFrame, order: tuple, s_order: tuple) -> float:
        """
        Evaluates the SARIMA model given certain parameters using the Akaike Information Criterion.

        Returns the AIC coefficient as a float value.
        """
        try:
            model = SARIMAX(
                endog=df["yield_values"],
                order=order,
                seasonal_order=s_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            results = model.fit(disp=False)
            return results.aic
        except Exception as err:
            logger.debug(err)
            return float("inf")


class Prophet(MLAlgorithm):
    """
    Class representing the Prophet algorithm from fbprophet.
    """

    def train(self, df: DataFrame):
        """
        Trains a Prophet model for the given data.

        Returns the fitted model.
        """
        df_prophet = df.reset_index().rename(columns={"date": "ds", "yield_values": "y"})
        model = pr(seasonality_mode="multiplicative")

        # Allows to Pickle the model, as you cannot pickle loggers.
        model.stan_backend.logger = None

        fit_model = model.fit(df_prophet)

        return fit_model

    def predict(self, df: DataFrame, ml_model) -> Series:
        """
        Given a fitted model and the data, it performs a prediction to obtain validation data
        for the last 3 years of harvesting.

        - ml_model: A fbprophet Prophet fitted model.

        Returns a pandas series of validation data.
        """
        future = ml_model.make_future_dataframe(periods=12, freq="MS")
        prediction = ml_model.predict(future)
        prediction = prediction[-48:-12][["ds", "yhat"]]

        return prediction

    def forecast(self, df: DataFrame, is_monthly: bool, ml_model) -> tuple(Series, Series):
        """
        Given a fitted model, it performs a forecast for the next harvesting year.

        - ml_model: A fbprophet Prophet fitted model.

        Returns a tuple of pandas Series: (last year values, forecasted values).
        """
        future = ml_model.make_future_dataframe(periods=12, freq="MS")
        prediction = ml_model.predict(future)
        forecast = prediction[-12:][["ds", "yhat"]]

        if is_monthly:
            return (df["yield_values"].iloc[-12], forecast[[0]])

        return (df["yield_values"].iloc[-12:], forecast)
