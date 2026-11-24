# AI SQL Assistant

This project converts natural language to SQL and executes read-only SQL queries against MySQL.

## Features

- Explore databases, tables, and columns (Schema tab).
- Schema-aware RAG: one ChromaDB document per table (columns, types, keys, sample values); only the
  top-5 relevant tables + foreign-key-linked tables are sent to the LLM. Toggle it off to compare with full-schema mode.
- Few-shot examples: the 3 most similar question→SQL pairs are added to the prompt; 👍 adds new ones.
- Connect to the demo database or your own (host/port/user/password/database/SSL). Private/local hosts are blocked
  for user connections; credentials stay in session memory only.
- Results table, CSV download, automatic bar/line chart, and a 20-item query history.
- Generate SQL from plain English using OpenAI, with a plain-English explanation.
- Self-correction: generated SQL is checked with `EXPLAIN`; on error the SQL + error go back to the model (max 3 attempts).
- Execute read-only SQL (`SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`), validated with sqlglot.
- View results in a Streamlit dashboard.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI (calls the functions below directly) |
| `api.py` | Optional thin FastAPI wrapper over the same functions |
| `db.py` | Config, MySQL connection (SSL optional), schema reading, query execution |
| `llm.py` | OpenAI prompts: generate SQL (JSON), fix SQL, explain SQL |
| `rag.py` | ChromaDB: index schema (re-index only when the schema hash changes), retrieve tables, few-shot examples |
| `few_shot.json` | Seed question→SQL examples for the demo database |
| `safety.py` | sqlglot read-only validation + auto `LIMIT 100` (`python safety.py` shows examples) |

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
- SQL is parsed with sqlglot: exactly one statement, only `SELECT` / `WITH…SELECT` / `SHOW` / `DESCRIBE` / `EXPLAIN`.
  Write clauses (`INSERT`, `UPDATE`, `DELETE`, DDL, `SELECT … INTO`, `FOR UPDATE`) and risky functions
  (`LOAD_FILE`, `SLEEP`, `BENCHMARK`) are rejected with a clear reason.
- `LIMIT 100` is added to `SELECT` queries that have no limit.
- Queries time out after 10 seconds (`max_execution_time`).

### Use a read-only MySQL user (recommended)

App-level checks are one layer; the database should be the second. Create a user that can only read:

```sql
CREATE USER 'sql_assistant_ro'@'%' IDENTIFIED BY 'choose-a-strong-password';
GRANT SELECT, SHOW VIEW ON college.* TO 'sql_assistant_ro'@'%';
FLUSH PRIVILEGES;
```

Then put this user in `MYSQL_USER` / `MYSQL_PASSWORD`. Even if a bad query slipped past the app, MySQL itself would refuse to change data.
