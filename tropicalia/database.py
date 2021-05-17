import aiosqlite

from tropicalia.config import settings
from tropicalia.logger import get_logger

logger = get_logger(__name__)


class Database:
    client: aiosqlite.Connection = None

db = Database()

async def create_db_connection():
    logger.debug("Connecting to the Database.")
    db.client = aiosqlite.connect(settings.DB_PATH)

async def close_db_connection():
    logger.debug("Closing Database connection")
    db.client.close()

async def get_connection() -> aiosqlite.Connection:
    return db.client.tropicalia