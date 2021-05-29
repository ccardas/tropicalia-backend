from datetime import date
from pydantic import BaseModel


class Algorithm(BaseModel):
    uid: int
    algorithm: str
    crop_type: str
    last_date: date
