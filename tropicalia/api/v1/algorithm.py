from fastapi import APIRouter, Depends, HTTPException

from tropicalia.auth import get_current_user
from tropicalia.database import Database, get_connection
from tropicalia.logger import get_logger
from tropicalia.manager import AlgorithmManager
from tropicalia.models.algorithm import Algorithm, AlgorithmPrediction
from tropicalia.models.user import UserInDB

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/predict",
    summary="Algorithm prediction",
    tags=["algorithm"],
    response_model=AlgorithmPrediction,
    response_description="Algorithm prediction",
)
async def predict(
    algorithm: str,
    crop_type: str,
    is_monthly: bool = False,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_connection),
) -> AlgorithmPrediction:
    """
    The specified algorithm makes a prediction for a year or a month for the given crop type.
    """
    data = await AlgorithmManager().predict(algorithm, crop_type, is_monthly, current_user.username, db)

    if not data:
        raise HTTPException(status_code=404, detail="Data prediction failed, algorithm might not be trained")

    return data


@router.get(
    "/train",
    summary="Algorithm training",
    tags=["algorithm"],
    response_description="Algorithm training",
)
async def train(
    algorithm: str,
    crop_type: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_connection),
) -> Algorithm:
    """
    User request for a specific algorithm to be trained for a given crop type data.
    """
    data = await AlgorithmManager().train(algorithm, crop_type, current_user.username, db)

    if not data:
        raise HTTPException(status_code=404, detail="Algorithm training failed")

    return data
