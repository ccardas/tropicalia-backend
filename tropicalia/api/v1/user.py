from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_409_CONFLICT

from tropicalia.database import Database, get_connection
from tropicalia.models.user import UserCreateRequest, UserInDB
from tropicalia.auth import get_user_by_email, get_user_by_username

router = APIRouter()


@router.post(
    "/register",
    summary="Sing-up authentication endpoint",
    tags=["auth"],
    response_model=UserInDB,
    response_description="User model from database",
)
async def register_to_system(user: UserCreateRequest, db: Database = Depends(get_connection)):
    user_by_email = await get_user_by_email(db, user.email)
    if user_by_email:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Email already in use",
        )
    user_by_username = await get_user_by_username(db, user.username)
    if user_by_username:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="User already in use",
        )

    await send_mail([user.email])
    # await send_mail(["pedgm@uma.es"])

    user_in_db = await register_user(db, user)  # User is disabled until email confirmation
    return user_in_db
