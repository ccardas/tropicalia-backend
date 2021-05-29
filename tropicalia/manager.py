import pandas as pd
from fastapi.encoders import jsonable_encoder
from pydantic.main import BaseModel

from tropicalia.algorithm import AlgorithmStack, MLAlgorithm
from tropicalia.database import Database
from tropicalia.logger import get_logger
from tropicalia.models.dataset import Algorithm, Dataset, DatasetRow
from tropicalia.storage.backend.minio import MinIOStorage

logger = get_logger(__name__)


async def execute(query: str, model: BaseModel, db: Database) -> BaseModel:
    """
    Given the database it executes the specified query and returns the result.
    Only for single-row involving queries.
    """
    res = await db.execute(query)
    row = await res.fetchall()

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
                INSERT INTO dataset (uid, date, crop_type, yield_values)
                VALUES ({row.uid}, '{row.date}', '{row.crop_type}', '{row.yield_values}')
            """

        await execute(query, DatasetRow, db)

        row_in_db = await self.find_one(row.uid, db)

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

    async def train(self, algorithm: str, crop_type: str, current_user: str, db: Database):
        """
        Given a crop type, it trains the algorithm for the according data.
        It stores the pickled trained algorithm's object into MinIO to reuse it for predictions.
        """
        # TODO
        # A trained algorithm object is pickled and then stored in MinIO.
        # Its filename is a random string which is stored and referenced in the DB.

        dataset = DatasetManager().get(crop_type, current_user, db)
        df = pd.DataFrame(jsonable_encoder(dataset))

        logger.debug(f"User {current_user} has requested a trained {algorithm}/{crop_type} from the DB")

    async def predict(self, algorithm: str, crop_type: str, is_monthly: bool, current_user: str, db: Database):
        """
        Loads the trained algorithm for the given crop and performs a prediction.
        """
        # TODO
        # Accessing the DB and querying for a specific algorithm and crop type should
        # return (if trained) the ID for the object stored in MinIO.
        # If the chosen combination (algorithm/crop_type) has not been trained before,
        # an error should be raised and let know the user it must be trained.
        logger.debug(f"User {current_user} has requested a prediction with {algorithm}/{crop_type}")

        query = f"""
            SELECT uid, algorithm, crop_type, date
            FROM algorithm
            WHERE algorithm = '{algorithm}' AND crop_type = '{crop_type}'
        """

        trained_alg = await execute(query, Algorithm, db)

        try:
            alg_obj = self.minio.get_file(trained_alg.uid)
        except Exception as err:
            logger.debug(f"Trained algorithm {algorithm} for crop {crop_type} was not found.")
            logger.debug(err)

        dataset = DatasetManager().get(crop_type, current_user, db)
        df = pd.DataFrame(jsonable_encoder(dataset))

        alg = self.get_ml_algorithm(algorithm)
        prediction = alg.predict(df, alg_obj)

        # TODO
        # Return pandas series object as a Dataset??? pydantic object.

    def get_ml_algorithm(self, algorithm: str) -> MLAlgorithm:
        """
        Given an algorithm name, returns an object of the class of the algorithm.

        Returns a MLAlgorithm class.
        """
        if algorithm == "SARIMA":
            return AlgorithmStack.SARIMA
        elif algorithm == "Prophet":
            return AlgorithmStack.Prophet
        else:
            return
