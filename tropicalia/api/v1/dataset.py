from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException

from tropicalia.auth import get_current_user
from tropicalia.database import Database, get_connection
from tropicalia.logger import get_logger
from tropicalia.manager import DatasetManager
from tropicalia.models.dataset import TableDataset, DatasetRow
from tropicalia.models.user import UserInDB

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/get",
    summary="Get dataset from DB",
    tags=["data"],
    response_model=TableDataset,
    response_description="Updated dataset from DB",
)
async def get(
    crop_type: str = "", current_user: UserInDB = Depends(get_current_user), db: Database = Depends(get_connection)
) -> TableDataset:
    """
    Retrieves data from the Dataset based on the crop type.
    """
    daily_data = await DatasetManager().get(crop_type, current_user.username, db)

    data = DatasetManager().get_table(daily_data)

    if not data:
        raise HTTPException(status_code=404, detail="Specified data not found")

    return data


@router.post(
    "/upsert",
    summary="Upsert data to DB",
    tags=["data"],
    response_model=Union[List[DatasetRow], DatasetRow],
    response_description="Upsert data to DB",
)
async def upsert(
    rows: Union[List[DatasetRow], DatasetRow],
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_connection),
) -> Union[List[DatasetRow], DatasetRow]:
    """
    Inserts or updates existing row in the DB.
    """
    if isinstance(rows, list):
        upsert_rows = [await DatasetManager().upsert(row, current_user.username, db, commit=False) for row in rows]
        if None in upsert_rows:
            raise HTTPException(status_code=404, detail="Upsert data error")
        await DatasetManager().commit(db)
    else:
        upsert_rows = await DatasetManager().upsert(rows, current_user.username, db)
        if not upsert_rows:
            raise HTTPException(status_code=404, detail="Upsert data error")

    return upsert_rows


@router.delete(
    "/delete",
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
        raise HTTPException(status_code=404, detail="Delete data error")

    return deleted_row


@router.post(
    "/apply",
    summary="Apply changes to data to DB",
    tags=["data"],
    response_model=List[List[DatasetRow]],
    response_description="Apply changes to data to DB",
)
async def apply(
    changes: List[List[DatasetRow]],
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_connection),
) -> List[List[DatasetRow]]:
    """
    Applies changes to rows in the DB.
    """
    upsert_rows, delete_rows = changes

    upserted_rows = [await DatasetManager().upsert(row, current_user.username, db, commit=False) for row in upsert_rows]
    if None in upserted_rows:
        raise HTTPException(status_code=404, detail="Upsert data error")

    deleted_rows = [await DatasetManager().delete(row, current_user.username, db, commit=False) for row in delete_rows]
    if None in deleted_rows:
        raise HTTPException(status_code=404, detail="Delete data error")

    await DatasetManager().commit(db)

    return [upsert_rows, deleted_rows]
