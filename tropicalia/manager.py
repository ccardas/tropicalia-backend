from tropicalia.database import Database
from tropicalia.logger import get_logger
from tropicalia.models.dataset import Dataset, DatasetRow

logger = get_logger(__name__)


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

        await self.execute(query, DatasetRow, db)

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
            await self.execute(query, DatasetRow, db)

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
        row = await self.execute(query, DatasetRow, db)

        return row

    async def execute(self, query: str, model: DatasetRow, db: Database) -> DatasetRow:
        """
        Given the database it executes the specified query and returns the involved DatasetRow model.
        Only for single-row altering queries.
        """
        res = await db.execute(query)
        row = await res.fetchall()

        await db.commit()

        if row:
            row_dict = {key: row[0][t] for t, key in enumerate(model.__fields__.keys())}
            return model(**row_dict)
