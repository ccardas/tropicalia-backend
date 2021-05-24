import pandas as pd
import asyncio
from unittest import TestCase

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from tropicalia.database import get_connection, close_db_connection

app = FastAPI()

client = TestClient(app)


@app.get("/table")
async def create_table(db=Depends(get_connection)) -> None:
    await db.execute(
        """CREATE TABLE IF NOT EXISTS test (
        id_test INTEGER PRIMARY KEY,
        text_test TEXT
        )
    """
    )
    await db.commit()
    # await close_db_connection()

@app.get("/insert")
async def insert_data(db=Depends(get_connection)) -> None:
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
    await db.execute(
        """SELECT * FROM test
    """
    )

    """
    Query result example
        >>> cur.execute("SELECT * FROM test")
        <sqlite3.Cursor object at 0x7fae71ddcf10>
        >>> res = cur.fetchall()
        >>> res
        [(0, 'test')]
        >>> type(res)
        <class 'list'>
        >>> res[0]
        (0, 'test')
        >>> type(res[0])
        <class 'tuple'>
        >>> res[0][1]
        'test'
        >>> res[0][0]
        0
    """

    await db.commit()
    await close_db_connection()

class Tests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        return super().tearDownClass()

    def test_create(self):
        response = client.get("/table")
        assert response.status_code == 200

    def test_insert(self):
        response = client.get("/insert")
        assert response.status_code == 200

