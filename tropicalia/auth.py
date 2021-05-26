from datetime import datetime, timedelta
from typing import Union, Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from starlette.status import HTTP_401_UNAUTHORIZED

from tropicalia.database import Database, get_connection
from tropicalia.models.user import UserInDB, UserCreateRequest
from tropicalia.config import settings

SECRET_KEY = "b91a61d721b88f7e9fe8618e2e7e604663dc36ced6001d6a157bd391f604e07b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


async def get_user_by_username(username: str, db: Database = Depends(get_connection)) -> UserInDB:
    """
    Checks whether there is a registered user using `username`.
    """
    user = await db.execute(
        f"""
        SELECT * FROM users WHERE username = ?
    """,
        username,
    )

    if user:
        return UserInDB(**dict(user))


async def get_user_by_email(email: str, db: Database = Depends(get_connection)) -> UserInDB:
    """
    Checks whether there is a registered user using `email`.
    """
    user = await db.execute(
        f"""
        SELECT * FROM {settings.DB_USER_TABLE} WHERE email = ?
    """,
        email,
    )

    if user:
        return UserInDB(**dict(user))


async def register_user(user: UserCreateRequest, db: Database = Depends(get_connection)) -> UserInDB:
    """
    Inserts the registered user into the database.
    """
    user_dict = user.dict()
    user_dict["password"] = user.hashed_password

    await db.execute(
        f"""INSERT INTO {settings.DB_USER_TABLE} 
        VALUES (?, ?, ?)
    """,
        user_dict,
    )

    return UserInDB(**user_dict)


async def authenticate_user(
    username: str, password: str, db: Database = Depends(get_connection)
) -> Union[UserInDB, bool]:
    """
    Checks whether the user's credentials are correct and is then authentified.
    """
    user = await get_user_by_username(username, db)
    if not user:
        return False
    if not user.verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates user's session token, sets an expiration time and encodes it following the JWT standard.
        - data: {"sub": username}
        - expires_delta : timedelta(minutes=30)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=120)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """
    Get current user based on JWT.
    """
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_username(username=username)
    if user is None:
        raise credentials_exception

    return user
