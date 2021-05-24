import aiosqlite

from tropicalia.config import settings
from tropicalia.logger import get_logger

logger = get_logger(__name__)


class Database:
    client: aiosqlite.Connection = None

db = Database()

async def create_db_connection() -> Database:
    logger.debug("Connecting to the Database.")
    db.client = await aiosqlite.connect(settings.DB_PATH)
    return db.client

async def close_db_connection() -> None:
    logger.debug("Closing Database connection")
    await db.client.close()

async def get_connection() -> Database:
    if not db.client:
        logger.debug("Client not connected")
        await create_db_connection()
    return db.client