from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class DatasetRow(BaseModel):
    uid: Optional[int] = None
    date: date
    crop_type: str
    yield_values: float


class Dataset(BaseModel):
    data: List[DatasetRow]
