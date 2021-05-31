import pytest
import pandas as pd

from tropicalia.database import Database, create_db_connection, close_db_connection


@pytest.fixture
async def setup_database() -> Database:
    """
    Fixture to set up the database
    """
    db = await create_db_connection(path=":memory:")
    await db.execute(
        """CREATE TABLE IF NOT EXISTS test (
            id_test INTEGER PRIMARY KEY,
            text_test TEXT
        )
    """
    )
    yield db

    # TEAR DOWN
    await close_db_connection()


@pytest.fixture
async def setup_test_data(setup_database) -> Database:
    """
    Fixture to setup the mock data in the DB
    """
    db = setup_database
    records = [(0, "test_0"), (1, "test_1"), (2, "test_2")]

    await db.executemany(
        """INSERT INTO test
        VALUES (?, ?)
    """,
        records,
    )
    await db.commit()

    yield db


@pytest.mark.asyncio
async def test_db(setup_test_data) -> None:
    """
    Test to check whether the database, table and rows were correctly created.
    """
    db = setup_test_data
    query_res = await db.execute(
        """SELECT * FROM test
    """
    )
    res = await query_res.fetchall()

    assert res[0][0] == 0
    assert res[0][1] == "test_0"


@pytest.mark.asyncio
async def test_pandas(setup_test_data) -> None:
    """
    Test whether pandas reads the table as a DataFrame correctly
    """
    db = setup_test_data

    query_res = await db.execute(
        """SELECT * FROM test
    """
    )
    res = await query_res.fetchall()

    df = pd.DataFrame(res)

    assert len(df) == 3
    assert len(df.columns) == 2
