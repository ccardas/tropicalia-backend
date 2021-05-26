from passlib.context import CryptContext
from pydantic import BaseModel, validator


class Token(BaseModel):
    access_token: str
    token_type: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    username: str
    email: str


class UserCreateRequest(User):
    password: str

    @validator("username")
    def username_alphanumeric(cls, v):
        assert v.isalnum(), "must be alphanumeric"
        return v

    @validator("email")
    def email_is_valid(cls, v):
        assert "@" in v, "email is not valid"
        return v

    @property
    def hashed_password(self) -> str:
        return pwd_context.hash(self.password)


class UserInDB(User):
    password: str

    def verify_password(self, plain_password) -> bool:
        return pwd_context.verify(plain_password, self.password)
