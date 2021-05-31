from datetime import date
from pydantic import BaseModel

from tropicalia.models.dataset import Dataset


class Algorithm(BaseModel):
    uid: int
    algorithm: str
    crop_type: str
    last_date: date


class AlgorithmPrediction(Algorithm):
    last_year_data: Dataset
    prediction: Dataset
    forecast: Dataset
