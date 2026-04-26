import os


def get_database_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "bonus_tracker")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    if user and password:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    if user:
        return f"postgresql://{user}@{host}:{port}/{database}"

    return f"postgresql://{host}:{port}/{database}"
