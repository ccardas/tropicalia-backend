import platform
import tempfile
from pathlib import Path
from pydantic import BaseSettings

from tropicalia.logger import get_logger

logger = get_logger(__name__)


class _Settings(BaseSettings):
    # API settings
    API_HOST: str = ""
    API_PORT: int = 8002
    API_DEBUG: int = 0
    API_KEY: str = "DEV"
    API_KEY_NAME: str = "access_token"

    # For applications sub-mounted below a given URL path
    ROOT_PATH: str = ""

    # Database settings
    DB_PATH: str = "/.tropicalia/db.sqlite3"

    # DFS
    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_USE_SSL: bool = False

    DATA_DIR: str = str(Path("/tmp" if platform.system() == "Darwin" else tempfile.gettempdir()))

    @property
    def MINIO_CONN(self):
        return f"{self.MINIO_ENDPOINT}"

    class Config:
        env_file = ".env"
        file_path = Path(env_file)
        if not file_path.is_file():
            logger.warning("⚠️ `.env` not found in current directory")
            logger.info("⚙️ Loading settings from environment")
        else:
            logger.info(f"⚙️ Loading settings from dotenv @ {file_path.absolute()}")


settings = _Settings()
