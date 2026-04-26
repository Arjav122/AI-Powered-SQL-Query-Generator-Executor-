import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from database import list_databases, list_tables, list_columns
from query_generator import generate_sql_query, execute_query

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI SQL Query API", version="1.1.0")


class GenerateSQLRequest(BaseModel):
    natural_language_query: str = Field(..., min_length=3)
    database_name: str | None = None
    table_names: list[str] | None = None


class ExecuteSQLRequest(BaseModel):
    sql_query: str = Field(..., min_length=1)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/list_databases/")
def get_databases():
    result = list_databases()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.get("/list_tables/{database_name}")
def get_tables(database_name: str):
    result = list_tables(database_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/list_columns/{database_name}/{table_name}")
def get_columns(database_name: str, table_name: str):
    result = list_columns(database_name, table_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/generate_sql/")
def generate_sql(request: GenerateSQLRequest):
    logger.debug("Generating SQL for NL query")
    sql_query = generate_sql_query(
        nl_query=request.natural_language_query,
        database_name=request.database_name,
        table_names=request.table_names,
    )

    if sql_query and not sql_query.lower().startswith("error generating sql query:"):
        return {"sql_query": sql_query}
    raise HTTPException(status_code=400, detail=sql_query or "Failed to generate SQL")


@app.post("/execute_sql/")
def execute_sql(request: ExecuteSQLRequest):
    result = execute_query(request.sql_query)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result