import os
from pathlib import Path


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def secrets_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    path = root / ".streamlit" / "secrets.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_secrets_toml() -> str:
    external_url = required_env("RENDER_EXTERNAL_URL").rstrip("/")
    cookie_secret = required_env("STREAMLIT_AUTH_COOKIE_SECRET")
    client_id = required_env("STREAMLIT_AUTH_CLIENT_ID")
    client_secret = required_env("STREAMLIT_AUTH_CLIENT_SECRET")
    server_metadata_url = required_env("STREAMLIT_AUTH_SERVER_METADATA_URL")

    return (
        "[auth]\n"
        f'redirect_uri = "{external_url}/oauth2callback"\n'
        f'cookie_secret = "{cookie_secret}"\n'
        f'client_id = "{client_id}"\n'
        f'client_secret = "{client_secret}"\n'
        f'server_metadata_url = "{server_metadata_url}"\n'
    )


def main():
    path = secrets_path()
    path.write_text(build_secrets_toml())
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
