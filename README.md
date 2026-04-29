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

## Run backend

Start the API with:

```bash
uvicorn app.backend.api.app:app --reload
```

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

This repo includes [render.yaml](/Users/timurkambachekov/Desktop/bonus_tracker/render.yaml:1) for the backend API and a Render Postgres database.

Backend service:
- runtime: Python
- start command:

```bash
python -m app.backend.scripts.bootstrap_db && uvicorn app.backend.api.app:app --host 0.0.0.0 --port ${PORT:-10000}
```

Database:
- Render injects `DATABASE_URL`
- backend now prefers `DATABASE_URL` automatically

Notes:
- `bootstrap_db` initializes `db/schema.sql` only when the database is empty
- loaders and data seeding are still separate; the Render bootstrap only creates schema

## Parsers

Parser scripts remain under `parsers/rpl/` and are intentionally separate from the application package because they are source-specific ingestion experiments rather than core app modules.
