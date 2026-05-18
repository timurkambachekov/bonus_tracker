# bonus_tracker

Local Python project for working with contract terms, player stats, and parser scripts.

## Structure

- `app/backend/`: backend API, repositories, services, domain, and DB helpers
- `app/frontend/`: Streamlit UI, auth gate, API client, and presentation helpers
- `app/loaders/`: CSV-to-Postgres import modules
- `db/schema.sql`: PostgreSQL schema
- `parsers/rpl/`: parser scripts and experiments
- `requirements.txt`: Python dependencies

## Load data

Create or activate a Python environment, install dependencies, then run the loaders you need:

```bash
pip install -r requirements.txt
python -m app.loaders.clubs
python -m app.loaders.players
python -m app.loaders.player_stats
python -m app.loaders.contract_terms
```

Competition-aware examples:

```bash
python -m app.loaders.clubs --competition rpl --season 2025
python -m app.loaders.clubs --competition russian-cup --competition fnl --season 2025
python -m app.loaders.players --competition russian-cup --season 2025
python -m app.loaders.player_stats --competition fnl --season 2025
python -m app.loaders.contract_terms --competition rpl --season 2025
```

Supported competition presets:
- `rpl`
- `russian-cup`
- `fnl`
- `second-league-a`

## Run backend

Start the API with:

```bash
uvicorn app.backend.api.app:app --reload
```

## Local development

Use local processes for normal app changes and keep Render as the deployed environment.

1. Start Postgres locally or point `DATABASE_URL` at a dev database.
2. Run the backend:

```bash
uvicorn app.backend.api.app:app --reload
```

3. In another terminal, run the frontend:

```bash
streamlit run app/frontend/streamlit_app.py
```

Local defaults:
- the frontend uses `http://127.0.0.1:8000` by default when `BONUS_TRACKER_API_URL` is unset
- local Streamlit auth should use `.streamlit/secrets.toml`

Recommended local `.streamlit/secrets.toml`:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "replace-with-a-local-secret"
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Notes:
- do not set `BONUS_TRACKER_API_URL` locally unless you intentionally want the frontend to call the deployed API
- no changes to `render.yaml` are required for local development
- only push to Render when you want to test a deployment

Available endpoints:

- `GET /` API root
- `GET /health`
- `GET /api/competitions`
- `GET /api/competitions/{competition_id}/clubs`
- `GET /api/clubs/{club_id}/players`
- `GET /api/players/{player_id}`
- `GET /api/players/{player_id}/stats`
- `GET /api/players/{player_id}/contract`
- `GET /api/contracts/{contract_id}/bonuses`
- `GET /api/bonuses/{bonus_id}/conditions`
- `GET /api/auth/by-email`
- `POST /api/auth/{user_id}/touch-login`

## Streamlit login

The Streamlit app uses built-in OIDC login, and access is limited by club assignments.

1. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml`
2. Fill in your provider values inside `[auth]`
3. Apply the schema so `app_users` and `app_user_clubs` exist
4. Add a user and assign allowed clubs:

```bash
python -m app.loaders.app_users --email rep@example.com --name "Club Rep" --role club_rep --club-id 13
```

Admins can be created without club assignments:

```bash
python -m app.loaders.app_users --email admin@example.com --name "Admin" --role admin
```

5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Run:

```bash
streamlit run app/frontend/streamlit_app.py
```

## Deploy on Render

This repo includes [render.yaml](/Users/timurkambachekov/Desktop/bonus_tracker/render.yaml:1) for:
- backend API
- Streamlit frontend
- Render Postgres database

Backend service:
- runtime: Python
- start command:

```bash
python -m app.backend.scripts.bootstrap_db && uvicorn app.backend.api.app:app --host 0.0.0.0 --port ${PORT:-10000}
```

Database:
- Render injects `DATABASE_URL`
- backend now prefers `DATABASE_URL` automatically

Frontend service:
- runtime: Python
- start command:

```bash
python -m app.frontend.scripts.bootstrap_streamlit_secrets && streamlit run app/frontend/streamlit_app.py --server.address 0.0.0.0 --server.port ${PORT:-10000}
```

Frontend env vars:
- `BONUS_TRACKER_API_URL` comes from the backend service URL
- `STREAMLIT_AUTH_COOKIE_SECRET` is auto-generated
- `STREAMLIT_AUTH_CLIENT_ID` must be provided
- `STREAMLIT_AUTH_CLIENT_SECRET` must be provided
- `STREAMLIT_AUTH_SERVER_METADATA_URL` defaults to Google OIDC

The frontend bootstrap script writes `.streamlit/secrets.toml` at runtime from these Render env vars, including:
- `redirect_uri = ${RENDER_EXTERNAL_URL}/oauth2callback`

Notes:
- `bootstrap_db` initializes `db/schema.sql` only when the database is empty
- loaders and data seeding are still separate; the Render bootstrap only creates schema
- after the frontend service URL exists, register `https://your-frontend-url.onrender.com/oauth2callback` with your OIDC provider if required

## Parsers

Parser scripts remain under `parsers/rpl/` and are intentionally separate from the application package because they are source-specific ingestion experiments rather than core app modules.
