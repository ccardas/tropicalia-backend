from fastapi import APIRouter, Depends, HTTPException

from tropicalia.auth import get_current_user
from tropicalia.database import Database, get_connection
from tropicalia.logger import get_logger
from tropicalia.manager import DatasetManager
from tropicalia.models.dataset import Dataset, DatasetRow
from tropicalia.models.user import UserInDB

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/data",
    summary="Get dataset from DB",
    tags=["data"],
    response_model=Dataset,
    response_description="Updated dataset from DB",
)
async def get(
    crop_type: str = "", current_user: UserInDB = Depends(get_current_user), db: Database = Depends(get_connection)
) -> Dataset:
    """
    Retrieves data from the Dataset based on the crop type.
    """
    data = await DatasetManager().get(crop_type, current_user.username, db)

    if not data:
        raise HTTPException(status_code=404, detail="Specified data not found")

    return data


@router.post(
    "/data/upsert",
    summary="Upsert data to DB",
    tags=["data"],
    response_model=DatasetRow,
    response_description="Upsert data to DB",
)
async def upsert(
    row: DatasetRow, current_user: UserInDB = Depends(get_current_user), db: Database = Depends(get_connection)
) -> DatasetRow:
    """
    Inserts or updates existing row in the DB.
    """
    upsert_row = await DatasetManager().upsert(row, current_user.username, db)

    if not upsert_row:
        raise HTTPException(status_code=404, detail="Upsert data error")

    return upsert_row


@router.delete(
    "/data/delete",
    summary="Delete row from DB",
    tags=["data"],
    response_model=DatasetRow,
    response_description="Delete row from DB",
)
async def delete(
    row: DatasetRow, current_user: UserInDB = Depends(get_current_user), db: Database = Depends(get_connection)
) -> DatasetRow:
    """
    Deletes given row from the DB.
    """
    deleted_row = await DatasetManager().delete(row, current_user.username, db)

    if not deleted_row:
        raise HTTPException(status_code=404, detail="Delete row error")

    return deleted_row
