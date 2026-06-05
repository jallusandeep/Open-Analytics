from contextlib import contextmanager
from typing import Generator

from app.database import get_connection


@contextmanager
def db_connection() -> Generator:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
