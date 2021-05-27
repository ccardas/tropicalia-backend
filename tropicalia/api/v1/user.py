from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT

from tropicalia.database import Database, get_connection
from tropicalia.models.user import UserCreateRequest, UserInDB, Token
from tropicalia.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    get_user_by_email,
    get_user_by_username,
    register_user,
)

router = APIRouter()


@router.post(
    "/register",
    summary="Sing-up authentication endpoint",
    tags=["auth"],
    response_model=UserInDB,
    response_description="User model from database",
)
async def register_to_system(user: UserCreateRequest, db: Database = Depends(get_connection)):
    user_by_email = await get_user_by_email(user.email, db)
    if user_by_email:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Email already in use",
        )
    user_by_username = await get_user_by_username(user.username, db)
    if user_by_username:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="User already in use",
        )

    user_in_db = await register_user(user, db)
    return user_in_db


@router.post(
    "/login",
    summary="Log-in authentication endpoint",
    tags=["auth"],
    response_model=Token,
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Database = Depends(get_connection),
):
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}
