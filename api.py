"""Optional thin FastAPI wrapper over the same functions the Streamlit app uses.

Run locally with:  uvicorn api:app --reload
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import db
import llm

app = FastAPI(title="AI SQL Query API", version="2.0.0")


class GenerateSQLRequest(BaseModel):
    natural_language_query: str = Field(..., min_length=3)
    database_name: str | None = None
    table_names: list[str] | None = None


class ExecuteSQLRequest(BaseModel):
    sql_query: str = Field(..., min_length=1)


def _call(func, *args, status=400):
    """Run a function and turn any error into an HTTP error."""
    try:
        return func(db.get_engine(), *args)
    except Exception as exc:
        raise HTTPException(status_code=status, detail=str(exc))


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/list_databases/")
def get_databases():
    return {"databases": _call(db.list_databases, status=500)}


@app.get("/list_tables/{database_name}")
def get_tables(database_name: str):
    return {"tables": _call(db.list_tables, database_name)}


@app.get("/list_columns/{database_name}/{table_name}")
def get_columns(database_name: str, table_name: str):
    return {"columns": _call(db.list_columns, database_name, table_name)}


@app.post("/generate_sql/")
def generate_sql(request: GenerateSQLRequest):
    sql = _call(llm.generate_sql, request.natural_language_query, request.database_name, request.table_names)
    return {"sql_query": sql}


@app.post("/execute_sql/")
def execute_sql(request: ExecuteSQLRequest):
    return {"results": _call(db.run_query, request.sql_query)}
