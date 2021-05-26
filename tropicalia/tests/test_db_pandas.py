import os 
import pytest
#import pandas as pd

from tropicalia.config import settings
from tropicalia.database import Database, get_connection, close_db_connection


@pytest.fixture
async def setup_database(request) -> Database:
    """
    Fixture to set up the database
    """
    db = await get_connection()
    await db.execute(
        """CREATE TABLE IF NOT EXISTS test (
        id_test INTEGER PRIMARY KEY,
        text_test TEXT
        )
    """
    )

    async def teardown():
        await close_db_connection()
        os.remove(settings.DB_PATH)
        print("Closed DB connection")

    request.addfinalizer(teardown)

    yield db

@pytest.fixture
async def setup_test_data(setup_database) -> Database:
    """
    Fixture to setup the mock data in the DB
    """
    db = setup_database
    await db.execute(
        """INSERT INTO test (
            id_test,
            text_test
        ) VALUES (
            0,
            "test"
        )
    """
    )
    await db.commit()

    yield db

@pytest.mark.asyncio
async def test_db(setup_test_data) -> None:
    """
    Test to check whether the database, table and rows were correctly created.
    """
    db = setup_test_data
    res = await db.execute(
        """SELECT * FROM test
    """
    )

    print(res)

    assert True

