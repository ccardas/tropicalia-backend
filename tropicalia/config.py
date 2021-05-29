import platform
import tempfile
from pathlib import Path
from pydantic import BaseSettings

from tropicalia.logger import get_logger

logger = get_logger(__name__)


class _Settings(BaseSettings):
    # API settings
    API_HOST = "0.0.0.0"
    API_PORT = 8001
    API_DEBUG = 0
    API_KEY = "DEV"
    API_KEY_NAME = "access_token"

    # For applications sub-mounted below a given URL path
    ROOT_PATH = ""

    # Database settings
    DB_PATH = str(Path.home()) + "/.tropicalia/db.sqlite3"

    # DFS
    MINIO_HOST: str = "localhost"
    MINIO_PORT: int = 9000
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio"

    DATA_DIR: str = str(Path("/tmp" if platform.system() == "Darwin" else tempfile.gettempdir()))

    @property
    def MINIO_CONN(self):
        return f"{self.MINIO_HOST}:{self.MINIO_PORT}"

    class Config:
        env_file = ".env"
        file_path = Path(env_file)
        if not file_path.is_file():
            logger.warning("⚠️ `.env` not found in current directory")
            logger.info("⚙️ Loading settings from environment")
        else:
            logger.info(f"⚙️ Loading settings from dotenv @ {file_path.absolute()}")


settings = _Settings()
