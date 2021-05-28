from datetime import date
from typing import List
from pydantic import BaseModel


class DatasetRow(BaseModel):
    uid: int
    date: date
    crop_type: str
    yield_values: float


class Dataset(BaseModel):
    data: List[DatasetRow]
