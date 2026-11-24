# AI SQL Assistant

This project converts natural language to SQL and executes read-only SQL queries against MySQL.

## Features

- Explore databases, tables, and columns.
- Generate SQL from plain English using OpenAI.
- Execute read-only SQL (`SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`).
- View results in a Streamlit dashboard.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI (calls the functions below directly) |
| `api.py` | Optional thin FastAPI wrapper over the same functions |
| `db.py` | Config, MySQL connection (SSL optional), schema reading, query execution |
| `llm.py` | OpenAI prompt that generates SQL |
| `safety.py` | Read-only SQL checks |

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create your local env file:

```bash
copy .env.example .env
```

4. Edit `.env` and set your real values:
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`
- `MYSQL_DATABASE` (optional; you can leave it empty and pick a DB in the UI)
- `MYSQL_SSL` (`true` for cloud MySQL such as TiDB Cloud)
- `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`)

Settings are read from Streamlit secrets (`.streamlit/secrets.toml`) first, then from `.env`.

## Run

```bash
streamlit run app.py
```

Optional REST API (same features):

```bash
uvicorn api:app --reload
```

## Security Notes

- `.env` and `.streamlit/secrets.toml` are ignored by git.
- Never commit real API keys/passwords.
- Write/DDL SQL statements are blocked for safety.
