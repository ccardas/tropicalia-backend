from __future__ import annotations

import warnings
from enum import Enum
from itertools import product
from typing import List

import pandas as pd
from pandas import DataFrame
from fbprophet import Prophet as pr
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.statespace.sarimax import SARIMAX

from tropicalia.logger import get_logger

logger = get_logger(__name__)
warnings.simplefilter("ignore", ConvergenceWarning)


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

    def predict(self, df: DataFrame) -> DataFrame:
        pass

    def forecast(self, df: DataFrame) -> tuple(DataFrame, DataFrame):
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
        configs = self.configs()
        best_config = self.evaluate_models(df, configs)
        fit_model = self.fit(df, best_config)

        return fit_model

    def predict(self, df: DataFrame, ml_model) -> DataFrame:
        """
        Given a fitted model and the data, it performs a prediction to obtain validation data
        for the last 3 years of harvesting.

        - ml_model: A statsmodels SARIMA fitted model.

        Returns a pandas DataFrame of validation data.
        """
        last_year = df["date"].iloc[-1]
        last3_years = pd.to_datetime(last_year) - pd.DateOffset(years=3) + pd.DateOffset(months=1)

        prediction = ml_model.get_prediction(start=pd.to_datetime(last3_years), dynamic=False)
        prediction = prediction.predicted_mean.to_frame().reset_index()

        return prediction

    def forecast(self, df: DataFrame, is_monthly: bool, ml_model) -> tuple(DataFrame, DataFrame):
        """
        Given a fitted model, it performs a forecast for the next harvesting year.

        - ml_model: A statsmodels SARIMA fitted model.

        Returns a tuple of pandas DataFrame: (last year values, forecasted values).
        """
        if is_monthly:
            forecast = ml_model.get_forecast(steps=1)
            return (df[["date", "yield_values"]].iloc[[-12]], forecast.predicted_mean.to_frame().reset_index())

        forecast = ml_model.get_forecast(steps=12)
        forecast = forecast.predicted_mean.to_frame().reset_index()

        return (df[["date", "yield_values"]].iloc[-12:], forecast)

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
        # p_params = [0, 1, 2]
        # d_params = [0, 1]
        # q_params = [0, 1, 2, 3]
        # P_params = [0, 1, 2]
        # D_params = [0, 1]
        # Q_params = [0, 1, 2, 3]

        p_params = [0]
        d_params = [0]
        q_params = [0]
        P_params = [0]
        D_params = [0, 1]
        Q_params = [0]

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

    def predict(self, df: DataFrame, ml_model) -> DataFrame:
        """
        Given a fitted model and the data, it performs a prediction to obtain validation data
        for the last 3 years of harvesting.

        - ml_model: A fbprophet Prophet fitted model.

        Returns a pandas DataFrame of validation data.
        """
        future = ml_model.make_future_dataframe(periods=12, freq="MS")
        prediction = ml_model.predict(future)
        prediction = prediction[-48:-12][["ds", "yhat"]]

        return prediction

    def forecast(self, df: DataFrame, is_monthly: bool, ml_model) -> tuple(DataFrame, DataFrame):
        """
        Given a fitted model, it performs a forecast for the next harvesting year.

        - ml_model: A fbprophet Prophet fitted model.

        Returns a tuple of pandas DataFrame: (last year values, forecasted values).
        """
        future = ml_model.make_future_dataframe(periods=12, freq="MS")
        prediction = ml_model.predict(future)
        forecast = prediction[-12:][["ds", "yhat"]]
        forecast = forecast.rename(columns={"ds": "date", "yhat": "yield_values"})

        if is_monthly:
            return (df[["date", "yield_values"]].iloc[[-12]], forecast.iloc[[-12]])

        return (df[["date", "yield_values"]].iloc[-12:], forecast)
