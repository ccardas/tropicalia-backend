from datetime import date
from typing import List, Optional, Union
from pydantic import BaseModel


class DatasetRow(BaseModel):
    uid: Optional[str] = None
    date: date
    crop_type: str
    yield_values: float


class Dataset(BaseModel):
    data: List[DatasetRow]


class MonthRow(BaseModel):
    date: date
    crop_type: str
    yield_values: float
    children: Union[Dataset, List]


class TableDataset(BaseModel):
    data: List[MonthRow]
