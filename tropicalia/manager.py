import pandas as pd
from fastapi.encoders import jsonable_encoder
from pydantic.main import BaseModel
from pandas import DataFrame

import pickle
from datetime import datetime

from tropicalia.algorithm import AlgorithmStack, MLAlgorithm, Prophet, SARIMA
from tropicalia.database import Database
from tropicalia.logger import get_logger
from tropicalia.models.algorithm import Algorithm, AlgorithmPrediction
from tropicalia.models.dataset import Dataset, DatasetRow
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
        cur = await db.cursor()
        await cur.execute(query)
        last_rowid = cur.lastrowid
        res_query = res_query.replace("placeholder", str(last_rowid))
        res = await cur.execute(res_query)
        row = await res.fetchall()
        await cur.close()
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

    async def upsert(self, row: DatasetRow, current_user: str, db: Database) -> DatasetRow:
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
                WHERE uid = {row.uid}
            """
        else:
            query = f"""
                INSERT INTO dataset (date, crop_type, yield_values)
                VALUES ('{row.date}', '{row.crop_type}', '{row.yield_values}')
            """

        res_query = f"""
            SELECT * FROM dataset WHERE uid = 'placeholder'
        """
        res = await execute_upsert(query, res_query, DatasetRow, db)

        row_in_db = await self.find_one(res.uid, db)
        row.uid = row_in_db.uid

        if row_in_db == row:
            return row_in_db

    async def delete(self, row: DatasetRow, current_user: str, db: Database) -> DatasetRow:
        """
        Deletes a dataset entry in the database given its id.
        """
        logger.debug(f"User {current_user} has requested a row delete to the DB")

        row_in_db = await self.find_one(row.uid, db)

        if row_in_db:
            query = f"""
                DELETE FROM dataset
                WHERE uid = {row.uid}
            """
            await execute(query, DatasetRow, db)

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
            SELECT * FROM dataset WHERE uid = {uid}
        """
        row = await execute(query, DatasetRow, db)

        return row


class AlgorithmManager:
    """
    Class implementing the user's interaction with the algorithms
    """

    minio = MinIOStorage()

    async def train(self, algorithm: str, crop_type: str, current_user: str, db: Database) -> Algorithm:
        """
        Given a crop type, it trains the algorithm for the according data.
        It stores the pickled trained algorithm's object into MinIO to reuse it for predictions.
        """
        dataset = await DatasetManager().get(crop_type, current_user, db)
        df = pd.DataFrame(jsonable_encoder(dataset.data))
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

        query = f"""
            SELECT uid, algorithm, crop_type, last_date
            FROM algorithm
            WHERE algorithm = '{algorithm}' AND crop_type = '{crop_type}'
            ORDER BY uid DESC
            LIMIT 1
        """
        trained_alg = await execute(query, Algorithm, db)

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

        dataset = await DatasetManager().get(crop_type, current_user, db)
        df = pd.DataFrame(jsonable_encoder(dataset.data))

        alg = self.get_ml_algorithm(algorithm)
        pred = alg().predict(df, alg_obj)
        last_year_data, forecast = alg().forecast(df, is_monthly, alg_obj)

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
        query = f"""
            INSERT INTO algorithm (algorithm, crop_type, last_date)
            VALUES ('{algorithm}', '{crop_type}', '{last_date}')
        """

        res_query = f"""
            SELECT * FROM algorithm WHERE uid = 'placeholder'
        """

        row_in_db = await execute_upsert(query, res_query, Algorithm, db, commit=False)

        resource = self.minio.put_file(folder_name=row_in_db.last_date, file_name=row_in_db.uid, data=alg_obj)
        if resource:
            logger.debug(f"Algorithm {row_in_db.uid} has been succesfully uploaded, with path {resource.scheme}")
            await db.commit()
            return row_in_db

    async def delete_algorithm(self):
        """
        Auxiliar method to delete records for an algorithm both from DB and MinIO
        """

        # TODO
