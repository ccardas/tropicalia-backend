import pandas as pd

from fastapi import Depends
from tropicalia.database import get_connection

async def create_database(db=Depends(get_connection)) -> None:
    await print(type(db))
    cursor = db.cursor()
    cursor.execute(
        """CREATE DATABASE timeseries
    """
    )
    db.commit()

async def create_table(db=Depends(get_connection)) -> None:
    cursor = db.cursor()
    cursor.execute(
        """CREATE TABLE timeseries.data (
        id INTEGER PRIMARY KEY,
        FechaRecepcion DATE,
        NombreFamilia TEXT,
        KilosEntrados DOUBLE
        )
    """
    )
    db.commit()

async def test():
    await create_database()
    await create_table()