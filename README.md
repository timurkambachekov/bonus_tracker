# bonus_tracker

Local Python project for working with contract terms and RPL parsing scripts.

## Main files

- `app/`: minimal backend API
- `contract_terms/`: contract bonus logic
- `db/schema.sql`: PostgreSQL schema
- `parsers/rpl/`: scraping and cleaning scripts
- `requirements.txt`: Python dependencies

## Run locally

Create or activate a Python environment, install dependencies, then run the scripts you need:

```bash
pip install -r requirements.txt
python parsers/rpl/parser_rpl.py
python parsers/rpl/parser_rpl_club_stats.py
```

## Run backend

Start the API with:

```bash
uvicorn app.main:app --reload
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
python -m app.dash_ui
```

Open:

```text
http://127.0.0.1:8050/
```
