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
        Retrieves specified data from the dataset in the DB.
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
