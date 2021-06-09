import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tropicalia.database import close_db_connection, create_db_connection
from tropicalia.config import settings
from tropicalia.api.v1 import user, dataset, algorithm

app = FastAPI()


app.add_event_handler("startup", create_db_connection)
app.add_event_handler("shutdown", close_db_connection)

app.include_router(user.router, prefix="/api/v1/auth")
app.include_router(dataset.router, prefix="/api/v1/data")
app.include_router(algorithm.router, prefix="/api/v1/algorithm")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
