import json
import pickle
from datetime import datetime
from secrets import token_hex

import pandas as pd
from fastapi.encoders import jsonable_encoder
from pydantic.main import BaseModel
from pandas import DataFrame

from tropicalia.algorithm import AlgorithmStack, MLAlgorithm, Prophet, SARIMA
from tropicalia.database import Database
from tropicalia.logger import get_logger
from tropicalia.models.algorithm import Algorithm, AlgorithmPrediction
from tropicalia.models.dataset import Dataset, DatasetRow, MonthRow, TableDataset
from tropicalia.storage.backend.minio import MinIOStorage

logger = get_logger(__name__)


async def execute(query: str, model: BaseModel, db: Database, commit: bool = True) -> BaseModel:
    """
    Given the database it executes the specified query and returns the result.
    Only for single-row involving queries.
    """
    try:
        res = await db.execute(query)
        row = await res.fetchall()
    except Exception as err:
        logger.debug(err)
        row = None

    if commit:
        await db.commit()

    if row:
        row_dict = {key: row[0][t] for t, key in enumerate(model.__fields__.keys())}
        return model(**row_dict)


async def execute_upsert(query: str, res_query: str, model: BaseModel, db: Database, commit: bool = True) -> BaseModel:
    """
    Given the database it executes the query and returns the inserted/updated row.
    """
    try:
        await db.execute(query)
        res = await db.execute(res_query)
        row = await res.fetchall()
    except Exception as err:
        logger.debug(err)
        row = None

    if commit:
        await db.commit()

    if row:
        row_dict = {key: row[0][t] for t, key in enumerate(model.__fields__.keys())}
        return model(**row_dict)


class DatasetManager:
    """
    Class implementing the user's interaction with the dataset
    """

    async def get(self, crop_type: str, current_user: str, db: Database) -> Dataset:
        """
        Retrieves specified data from the dataset in the database.
        """
        logger.debug(f"User {current_user} has requested {crop_type} from the DB")

        wildcard = crop_type + "%"
        query = f"""
            SELECT uid, date, crop_type, yield_values
            FROM dataset
            WHERE LIKE('{wildcard}', crop_type)
        """
        res = await db.execute(query)
        data = await res.fetchall()
        rows = []
        for r in range(len(data)):
            rows.append({key: data[r][t] for t, key in enumerate(DatasetRow.__fields__.keys())})

        dataset_rows = [DatasetRow(**row) for row in rows]

        return Dataset(data=dataset_rows)

    async def upsert(self, row: DatasetRow, current_user: str, db: Database, commit: bool = True) -> DatasetRow:
        """
        Inserts or updates a row in the database given its id.
        """
        logger.debug(f"User {current_user} has requested an update to the DB")

        row_in_db = await self.find_one(row.uid, db)

        if row_in_db:
            query = f"""
                UPDATE dataset
                SET (date, crop_type, yield_values) =
                ('{row.date}', '{row.crop_type}', '{row.yield_values}')
                WHERE uid = '{row.uid}'
            """
        else:
            query = f"""
                INSERT INTO dataset (uid, date, crop_type, yield_values)
                VALUES ('{row.uid}', '{row.date}', '{row.crop_type}', '{row.yield_values}')
            """

        res_query = f"""
            SELECT * FROM dataset WHERE uid = '{row.uid}'
        """
        res = await execute_upsert(query, res_query, DatasetRow, db, commit)

        row_in_db = await self.find_one(res.uid, db)
        row.uid = row_in_db.uid

        if row_in_db == row:
            return row_in_db

    async def delete(self, row: DatasetRow, current_user: str, db: Database, commit: bool = True) -> DatasetRow:
        """
        Deletes a dataset entry in the database given its id.
        """
        logger.debug(f"User {current_user} has requested a row delete to the DB")

        row_in_db = await self.find_one(row.uid, db)

        if row_in_db:
            query = f"""
                DELETE FROM dataset
                WHERE uid = '{row.uid}'
            """
            await execute(query, DatasetRow, db, commit)

            row_in_db = await self.find_one(row.uid, db)

            if not row_in_db:
                return row

    async def find_one(self, uid: int, db: Database) -> DatasetRow:
        """
        Find a dataset entry in the database given its id.
        """
        if not uid:
            uid = -1
        query = f"""
            SELECT * FROM dataset WHERE uid = '{uid}'
        """
        row = await execute(query, DatasetRow, db)

        return row

    async def commit(self, db: Database):
        """
        Given the order, commits the current changes to the DB
        """
        await db.commit()

    def get_table(self, daily_data: Dataset) -> TableDataset:
        """
        Given a daily data history, groups the data per month and returns a JSON object
        with each month having the month's days as children.
        """
        monthly_data = self.get_monthly(daily_data).data
        monthly_data = list(map(lambda row: row.dict(), monthly_data))
        map(lambda row: row.pop("uid", None), monthly_data)

        daily_data = list(map(lambda row: row.dict(), daily_data.data))

        for month_data in monthly_data:
            year = month_data["date"].year
            month = month_data["date"].month
            crop_type = month_data["crop_type"]

            data_in_month = [
                x
                for x in daily_data
                if x["date"].year == year and x["date"].month == month and x["crop_type"] == crop_type
            ]
            month_data["children"] = data_in_month

        monthly_data = sorted(monthly_data, key=lambda k: k["date"])
        dataset_rows = [MonthRow(**row) for row in monthly_data]

        return TableDataset(data=dataset_rows)

    def get_monthly(self, daily_data: Dataset, models: bool = False) -> Dataset:
        """
        Given a daily data history, returns the monthly sum for each crop
        """
        daily_data = [row.dict() for row in daily_data.data]
        df_month = pd.DataFrame()
        df_daily = pd.DataFrame()
        df_daily = df_daily.from_dict(daily_data)
        df_daily["date"] = pd.to_datetime(df_daily["date"])

        crop_varieties = df_daily["crop_type"].unique()

        for v in crop_varieties:
            df_var = df_daily[df_daily["crop_type"] == v]
            df_var = df_var.set_index("date").resample("MS").sum()
            df_var["crop_type"] = v
            df_var = df_var.reset_index()

            df_month = pd.concat([df_month, df_var])

        if models:
            starting_date = min(df_daily["date"])
            ending_date = max(df_daily["date"])
            date_range = pd.date_range(start=starting_date, end=ending_date, freq="MS")
            for date in date_range:
                for v in crop_varieties:
                    res = df_month[df_month["date"] == date]["crop_type"] == v
                    # If there does NOT exists any row for the given date + crop type, append it as a new row
                    if len(res[res == True].index.values) == 0:
                        df_month = df_month.append(
                            {"date": date, "crop_type": v, "yield_values": 0.0}, ignore_index=True
                        )
        else:
            df_month = df_month[df_month["yield_values"] > 0.0]

        df_month["date"] = df_month["date"].dt.strftime("%Y-%m-%d")
        df_month = df_month[["date", "crop_type", "yield_values"]]
        month_json = df_month.to_json(orient="table", index=False)
        month_json = eval(month_json)
        month_json = eval(json.dumps(month_json["data"]))

        dataset_rows = [DatasetRow(**row) for row in month_json]

        return Dataset(data=dataset_rows)


class AlgorithmManager:
    """
    Class implementing the user's interaction with the algorithms
    """

    minio = MinIOStorage()

    async def check(self, algorithm: str, crop_type: str, current_user: str, db: Database) -> Algorithm:
        """
        Given an algorithm and a crop type, it is checked in the DB whether the pair has been trained.
        """
        logger.debug(f"User {current_user} has requested whether {algorithm}/{crop_type} is trained from the DB")

        query = f"""
            SELECT uid, algorithm, crop_type, last_date
            FROM algorithm
            WHERE algorithm = '{algorithm}' AND crop_type = '{crop_type}'
            ORDER BY last_date DESC
            LIMIT 1
        """
        trained_alg = await execute(query, Algorithm, db)

        return trained_alg

    async def train(self, algorithm: str, crop_type: str, current_user: str, db: Database) -> Algorithm:
        """
        Given a crop type, it trains the algorithm for the according data.
        It stores the pickled trained algorithm's object into MinIO to reuse it for predictions.
        """
        daily_dataset = await DatasetManager().get(crop_type, current_user, db)
        monthly_dataset = DatasetManager().get_monthly(daily_dataset, models=True)

        df = pd.DataFrame(jsonable_encoder(monthly_dataset.data))
        last_date = datetime.strptime(df["date"].iloc[-1], "%Y-%m-%d").date()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index(["date"])

        logger.debug(f"User {current_user} has requested a trained {algorithm}/{crop_type} from the DB")

        alg = self.get_ml_algorithm(algorithm)
        trained_alg = alg().train(df)
        alg_obj = pickle.dumps(trained_alg)

        row_in_db = await self.insert_algorithm(algorithm, crop_type, last_date, alg_obj, db)

        if row_in_db:
            return row_in_db

    async def predict(
        self, algorithm: str, crop_type: str, is_monthly: bool, current_user: str, db: Database
    ) -> AlgorithmPrediction:
        """
        Loads the trained algorithm for the given crop and performs a prediction.
        """
        logger.debug(f"User {current_user} has requested a prediction with {algorithm}/{crop_type}")

        trained_alg = await self.check(algorithm, crop_type, current_user, db)

        try:
            dfs_path = self.minio.get_url(trained_alg.last_date, trained_alg.uid)
            alg_path = self.minio.get_file(dfs_path.resource)
            with open(alg_path, mode="rb") as file:
                b_obj = file.read()
                alg_obj = pickle.loads(b_obj)
        except Exception as err:
            logger.debug(f"Trained algorithm {algorithm} for crop {crop_type} was not found.")
            logger.debug(err)
            return

        logger.debug(f"Selected trained model for prediction has uid: {trained_alg.uid}")

        daily_dataset = await DatasetManager().get(crop_type, current_user, db)
        monthly_dataset = DatasetManager().get_monthly(daily_dataset, models=True)
        df = pd.DataFrame(jsonable_encoder(monthly_dataset.data))

        alg = self.get_ml_algorithm(algorithm)
        last_year_data, forecast = alg().forecast(df, is_monthly, alg_obj)

        if is_monthly:
            pred = forecast
        else:
            pred = alg().predict(df, alg_obj)

        data = self.df_to_model(last_year_data, pred, forecast, trained_alg)

        if data:
            return data

    def get_ml_algorithm(self, algorithm: str) -> MLAlgorithm:
        """
        Given an algorithm name, returns an object of the class of the algorithm.

        Returns a MLAlgorithm class.
        """
        if algorithm == AlgorithmStack.SARIMA.value:
            return SARIMA
        elif algorithm == AlgorithmStack.Prophet.value:
            return Prophet
        else:
            return

    def df_to_model(
        self, ly_data: DataFrame, pred: DataFrame, fc: DataFrame, algorithm: Algorithm
    ) -> AlgorithmPrediction:
        """
        Given a pandas DataFrame, the algorithm, crop type and last date, it builds
        the pydantic `AlgorithmPrediction` model.
        """
        data_ly = []
        ly_len = len(ly_data)
        for i in range(ly_len):
            date, yield_values = ly_data.iloc[i].values
            data_ly.append(DatasetRow(date=date, crop_type=algorithm.crop_type, yield_values=yield_values))
        data_pred = []
        pred_len = len(pred)
        for i in range(pred_len):
            date, yield_values = pred.iloc[i].values
            data_pred.append(DatasetRow(date=date, crop_type=algorithm.crop_type, yield_values=yield_values))

        data_fc = []
        forecast_len = len(fc)
        for i in range(forecast_len):
            date, yield_values = fc.iloc[i].values
            data_fc.append(DatasetRow(date=date, crop_type=algorithm.crop_type, yield_values=yield_values))

        last_year_data = Dataset(data=data_ly)
        prediction = Dataset(data=data_pred)
        forecast = Dataset(data=data_fc)

        return AlgorithmPrediction(
            uid=algorithm.uid,
            algorithm=algorithm.algorithm,
            crop_type=algorithm.crop_type,
            last_date=algorithm.last_date,
            last_year_data=last_year_data,
            prediction=prediction,
            forecast=forecast,
        )

    async def insert_algorithm(
        self, algorithm: str, crop_type: str, last_date: datetime, alg_obj, db: Database
    ) -> Algorithm:
        """
        Auxiliar method to insert a new algorithm's info in the DB and to upload the object to MinIO
        """
        uid = token_hex(4)

        # Previously trained algorithms for such combination are deleted.
        await self.delete_algorithm(algorithm, crop_type, last_date, db)

        query = f"""
            INSERT INTO algorithm (uid, algorithm, crop_type, last_date)
            VALUES ('{uid}', '{algorithm}', '{crop_type}', '{last_date}')
        """

        res_query = f"""
            SELECT * FROM algorithm WHERE uid = '{uid}'
        """

        row_in_db = await execute_upsert(query, res_query, Algorithm, db, commit=False)

        resource = self.minio.put_file(folder_name=row_in_db.last_date, file_name=row_in_db.uid, data=alg_obj)
        if resource:
            logger.debug(f"Algorithm {row_in_db.uid} has been succesfully uploaded, with path {resource.scheme}")
            await db.commit()
            return row_in_db

    async def delete_algorithm(self, algorithm: str, crop_type: str, last_date: datetime, db: Database):
        """
        Auxiliar method to delete records for an algorithm both from DB and MinIO
        """
        # It is required to specify the date format, as SQL *WHEN QUERYING*
        # internally does not appear to recognize datetime
        delete_query = f"""
            DELETE FROM algorithm
            WHERE algorithm = '{algorithm}' AND crop_type = '{crop_type}' AND
            last_date = '{last_date.strftime('%Y-%m-%d')}'
        """
        await execute(delete_query, Algorithm, db, commit=False)

        # TODO
        # Delete from MinIO too.
