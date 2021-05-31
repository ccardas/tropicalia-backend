import pytest
from pydantic import ValidationError

import pickle

from tropicalia.storage import MinIOStorage
from tropicalia.storage.backend.minio import MinIOResource
from tropicalia.storage.storage import Resource

obj = {"i am": "a pickled object"}
bucket_name = "test"
folder_name = "test"
file_name = "pickled_obj"


def test_invalid_resource_with_no_scheme_nor_resource():
    with pytest.raises(ValidationError):
        Resource()


def test_invalid_resource_with_no_resource():
    with pytest.raises(ValidationError):
        Resource(scheme="test://")


@pytest.fixture
def minio() -> MinIOStorage:
    """
    Fixture to set up the MinIO client
    """
    minio = MinIOStorage(bucket_name=bucket_name)

    yield minio


@pytest.fixture
def upload_pickle(minio) -> MinIOResource:
    """
    Fixture to insert an object to MinIO
    """
    pickled = pickle.dumps(obj)
    resource = minio.put_file(folder_name=folder_name, file_name=file_name, data=pickled)
    yield resource


def test_upload_pickle(minio, upload_pickle):
    """
    Test to check whether the bucket uploads pickled objects
    """
    assert upload_pickle == minio.get_url(folder_name=folder_name, file_name=file_name)


def test_get_pickle(minio, upload_pickle):
    """
    Test to check whether the pickled and uploaded object has not changed
    """
    print(upload_pickle)
    path = minio.get_file(scheme=upload_pickle.resource)

    with open(path, mode="rb") as file:
        _obj = file.read()
        _obj = pickle.loads(_obj)

    assert _obj == obj


def test_delete_pickle(minio, upload_pickle):
    """
    Test to check whether the uploaded object has
    """
    deleted_resource = minio.remove_object(upload_pickle.resource)

    assert deleted_resource == upload_pickle
