# bonus_tracker

Local Python project for working with contract terms, player stats, and parser scripts.

## Structure

- `app/api/`: FastAPI app factory and routes
- `app/domain/`: core business entities and rules
- `app/repositories/`: database query layer
- `app/services/`: bonus and response assembly logic
- `app/loaders/`: CSV-to-Postgres import modules
- `app/`: compatibility entry points for existing commands
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
uvicorn app.api.app:app --reload
```

Available endpoints:

- `GET /` API root
- `GET /health`
- `GET /api/summary`
- `GET /api/clubs`
- `GET /api/players?limit=50`
- `GET /api/stats?limit=50`
- `GET /api/contracts/spartak`

## Run Dash UI

Start the backend first, then run Dash:

```bash
python -m app.ui.dash_app
```

Open:

```text
http://127.0.0.1:8050/
```

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
streamlit run app/ui/streamlit_app.py
```

## Parsers

Parser scripts remain under `parsers/rpl/` and are intentionally separate from the application package because they are source-specific ingestion experiments rather than core app modules.
