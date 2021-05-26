from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from tropicalia.database import Database, get_connection
from tropicalia.models.user import UserInDB, UserCreateRequest


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

async def get_user_by_email(db: Database = Depends(get_connection), username: str) -> UserInDB:
    return

async def get_user_by_username(db: Database = Depends(get_connection), email: str) -> UserInDB:
    return

