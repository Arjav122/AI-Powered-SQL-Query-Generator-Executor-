# AI SQL Assistant

This project converts natural language to SQL and executes read-only SQL queries against MySQL.

## Features

- Explore databases, tables, and columns.
- Generate SQL from plain English using OpenAI.
- Execute read-only SQL (`SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`).
- View results in a Streamlit dashboard.

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
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE` (optional; you can leave it empty and pick DB in UI)
- `OPENAI_API_KEY`

## Run

Start backend:

```bash
uvicorn app:app --reload
```

Start UI (new terminal):

```bash
streamlit run ui.py
```

## Security Notes

- `.env` is ignored by git.
- Never commit real API keys/passwords.
- API blocks write/DDL SQL statements for safety.
