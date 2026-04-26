from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.config import get_database_url


@contextmanager
def get_connection():
    with psycopg.connect(get_database_url(), row_factory=dict_row) as connection:
        yield connection
