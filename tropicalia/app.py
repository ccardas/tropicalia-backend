import uvicorn

from fastapi import FastAPI

from tropicalia.database import close_db_connection, create_db_connection
from tropicalia.config import settings
from tropicalia.api.v1 import user

app = FastAPI()


app.add_event_handler("startup", create_db_connection)
app.add_event_handler("shutdown", close_db_connection)

app.include_router(user.router, prefix="/api/v1/auth")


@app.get("/")
async def test():
    return {"message": "Hello World"}


def run_server():
    uvicorn.run(
        app,
        port=settings.API_PORT,
        host=settings.API_HOST,
        root_path=settings.ROOT_PATH,
        log_level="trace" if settings.API_DEBUG else "info",
    )
