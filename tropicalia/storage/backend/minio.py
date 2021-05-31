import json
from io import BytesIO
from pathlib import Path
from typing import Union

from filelock import FileLock
from minio import Minio
from minio.error import S3Error

from tropicalia.config import settings
from tropicalia.logger import get_logger
from tropicalia.storage.storage import NotValidScheme, Resource, Storage

logger = get_logger(__name__)


class MinIOResource(Resource):
    scheme = "minio://"


class MinIOStorage(Storage):
    def __init__(self, bucket_name: str = "algorithm"):
        super().__init__(bucket_name, folder_name="")
        self.client = Minio(
            settings.MINIO_CONN,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        self.setup()

    def setup(self) -> MinIOResource:

        policy_read_only = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/*",
                }
            ],
        }

        try:
            self.client.make_bucket(self.bucket_name)
            self.client.set_bucket_policy(self.bucket_name, json.dumps(policy_read_only))
        except S3Error as err:
            if err.code != "BucketAlreadyOwnedByYou":
                raise

        return MinIOResource(resource=f"minio://{self.bucket_name}/")

    def put_file(self, folder_name: Union[str, Path], file_name: str, data) -> MinIOResource:
        """
        Given a folder name, the desired file name and the data object in Bytes,
        the object is uploaded to MinIO.
        """
        object_name = str(Path(str(folder_name), str(file_name)))

        try:
            self.client.put_object(
                bucket_name=self.bucket_name, object_name=object_name, data=BytesIO(data), length=len(data)
            )
        except S3Error as err:
            logger.error(f"Could not upload file {object_name} to {self.bucket_name}")
            logger.exception(err)
            raise

        return MinIOResource(resource=f"minio://{self.bucket_name}/{folder_name}/{file_name}")

    def get_file(self, scheme: str) -> str:
        """
        Given a MinIO path scheme, it returns the local path for the downloaded file
        """
        if not scheme.startswith("minio://"):
            raise NotValidScheme("Object file prefix is invalid: expected `minio://`")

        bucket_name, object_name = scheme[len("minio://") :].split("/", 1)

        file_path = Path(self.temp_dir, bucket_name, object_name)
        file_path.parents[0].mkdir(parents=True, exist_ok=True)
        file_lock = FileLock(str(file_path) + ".lock")  # avoid race: https://github.com/minio/minio-py/issues/854

        with file_lock:
            if not file_path.is_file():
                try:
                    self.client.fget_object(
                        bucket_name=bucket_name,
                        object_name=object_name,
                        file_path=(str(file_path)),
                    )
                except S3Error as err:
                    logger.error(f"Could not get file {object_name} from {self.bucket_name}")
                    logger.exception(err)
                    raise

        return str(file_path)

    def remove_object(self, scheme: str) -> MinIOResource:
        """
        Given a MinIO path scheme, it removes the file from MinIO.
        """
        if not scheme.startswith("minio://"):
            raise NotValidScheme("Object file prefix is invalid: expected `minio://`")

        bucket_name, object_name = scheme[len("minio://") :].split("/", 1)
        try:
            self.client.remove_object(bucket_name=bucket_name, object_name=object_name)
        except S3Error as err:
            logger.error(f"Could not remove file {object_name} from {self.bucket_name}")
            logger.exception(err)

        return MinIOResource(resource=scheme)

    def get_url(self, folder_name: Union[str, Path], file_name: str) -> MinIOResource:
        """
        From a folder name and a filename, returns the according MinIOResource object.
        """
        return MinIOResource(resource=f"minio://{self.bucket_name}/{folder_name}/{file_name}")
