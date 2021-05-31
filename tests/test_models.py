from tropicalia.models.algorithm import Algorithm, AlgorithmPrediction
from tropicalia.models.dataset import Dataset, DatasetRow
from tropicalia.models.user import UserInDB

_user = {"username": "username", "email": "email", "password": "password"}

_dataset_row = {"uid": 1, "date": "2000-01-01", "crop_type": "Mango", "yield_values": 100}

_dataset = {
    "data": [
        {"uid": 1, "date": "2000-01-01", "crop_type": "Mango", "yield_values": 100},
        {"uid": 2, "date": "2000-01-01", "crop_type": "Avocado", "yield_values": 100},
    ]
}

_algorithm = {"uid": 1, "algorithm": "ARIMA", "crop_type": "Mango", "last_date": "2000-01-01"}

_algorithm_prediction = {
    "uid": 1,
    "algorithm": "ARIMA",
    "crop_type": "Mango",
    "last_date": "2000-01-01",
    "prediction": _dataset,
}


def test_valid_structure_users():
    print(_dataset_row)
    UserInDB(**_user)
    DatasetRow(**_dataset_row)
    Dataset(**_dataset)
    Algorithm(**_algorithm)
    AlgorithmPrediction(**_algorithm_prediction)
