"""Optional thin FastAPI wrapper over the same functions the Streamlit app uses (demo database only).

Run locally with:  uvicorn api:app --reload   then open http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import db
import llm
import rag

app = FastAPI(title="AI SQL Query API", version="3.0.0")


class GenerateSQLRequest(BaseModel):
    natural_language_query: str = Field(..., min_length=3)
    use_rag: bool = True


class ExecuteSQLRequest(BaseModel):
    sql_query: str = Field(..., min_length=1)


def _call(func, *args, status=400):
    """Run a function and turn any error into an HTTP error."""
    try:
        return func(*args)
    except Exception as exc:
        raise HTTPException(status_code=status, detail=str(exc))


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/list_databases/")
def get_databases():
    return {"databases": _call(db.list_databases, db.get_engine(), status=500)}


@app.get("/list_tables/{database_name}")
def get_tables(database_name: str):
    return {"tables": _call(db.list_tables, db.get_engine(), database_name)}


@app.get("/list_columns/{database_name}/{table_name}")
def get_columns(database_name: str, table_name: str):
    return {"columns": _call(db.list_columns, db.get_engine(), database_name, table_name)}


@app.post("/reindex/")
def reindex():
    cfg = db.demo_config()
    return _call(rag.ensure_index, db.get_engine(cfg), cfg, True, status=500)


@app.post("/generate_sql/")
def generate_sql(request: GenerateSQLRequest):
    cfg = db.demo_config()
    engine = db.get_engine(cfg)
    _call(rag.ensure_index, engine, cfg, status=500)  # no-op if the schema hash is unchanged
    _call(rag.seed_examples, db.connection_key(cfg), status=500)
    result = _call(llm.generate_sql, engine, cfg, request.natural_language_query, request.use_rag)
    if result["error"]:
        raise HTTPException(status_code=400, detail=result)
    return {"sql_query": result["sql"], **result}


@app.post("/execute_sql/")
def execute_sql(request: ExecuteSQLRequest):
    return {"results": _call(db.run_query, db.get_engine(), request.sql_query)}
