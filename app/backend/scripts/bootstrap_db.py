from pathlib import Path

import psycopg

from app.backend.config import get_database_url


def schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "db" / "schema.sql"


def schema_already_initialized(connection) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.competitions');")
        return cursor.fetchone()[0] is not None


def apply_schema(connection):
    sql = schema_path().read_text()
    with connection.cursor() as cursor:
        cursor.execute(sql)
    connection.commit()


def main():
    with psycopg.connect(get_database_url()) as connection:
        if schema_already_initialized(connection):
            print("schema already initialized")
            return
        apply_schema(connection)
        print("schema initialized")


if __name__ == "__main__":
    main()
