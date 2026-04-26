import os
import re
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database import engine, list_databases, list_tables, list_columns
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

MAX_TABLES = 5
MAX_COLUMNS_PER_TABLE = 5
READ_ONLY_SQL_PATTERN = re.compile(r"^\s*(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN)\b", re.IGNORECASE)
BLOCKED_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|RENAME|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def clean_sql_output(response_text):
    fenced_sql_blocks = re.findall(r"```sql\s*(.*?)\s*```", response_text, flags=re.DOTALL | re.IGNORECASE)
    if fenced_sql_blocks:
        candidate = fenced_sql_blocks[0].strip()
        if candidate.endswith(";"):
            return candidate
        return f"{candidate};"

    clean_query = response_text.strip()
    sql_patterns = [
        r"(SELECT\s+.*?;)",
        r"(SHOW\s+.*?;)",
        r"(DESCRIBE\s+.*?;)",
        r"(EXPLAIN\s+.*?;)",
        r"(WITH\s+\w+\s+AS\s*\(.*?\)\s*SELECT\s+.*?;)",
    ]

    for pattern in sql_patterns:
        sql_match = re.search(pattern, clean_query, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()

    # Fallback: if response appears to be bare SQL without semicolon, normalize it.
    line_candidate = clean_query.splitlines()[0].strip()
    if re.match(r"^(SELECT|SHOW|DESCRIBE|EXPLAIN)\b", line_candidate, flags=re.IGNORECASE):
        return f"{line_candidate.rstrip(';')};"

    return clean_query


def get_limited_schema(database_name: str | None = None, table_names: list[str] | None = None):
    schema = {}
    selected_tables = set(table_names or [])
    if database_name:
        databases = [database_name]
    else:
        databases = list_databases().get("databases", [])

    for db in databases:
        schema[db] = {}
        db_tables = list_tables(db).get("tables", [])
        if selected_tables:
            tables = [table for table in db_tables if table in selected_tables]
        else:
            tables = db_tables[:MAX_TABLES]
        for table in tables:
            columns = list_columns(db, table).get("columns", [])
            # Give fuller context for explicitly selected tables to reduce hallucinations.
            if table in selected_tables:
                schema[db][table] = columns
            else:
                schema[db][table] = columns[:MAX_COLUMNS_PER_TABLE]
    return schema


def _validate_generated_sql(sql_query: str) -> None:
    _validate_sql_read_only(sql_query)
    explainable = re.match(r"^\s*(SELECT|WITH)\b", sql_query, flags=re.IGNORECASE)
    if not explainable:
        return

    try:
        with engine.connect() as connection:
            connection.execute(text(f"EXPLAIN {sql_query}"))
    except SQLAlchemyError as exc:
        raise ValueError(
            "Generated SQL looks invalid for your schema. "
            f"MySQL error: {str(exc)}"
        ) from exc


def generate_sql_query(
    nl_query: str,
    database_name: str | None = None,
    table_names: list[str] | None = None,
):
    if not client:
        return "Error generating SQL query: OPENAI_API_KEY is missing in .env"

    selected_tables = table_names or []
    schema = get_limited_schema(database_name=database_name, table_names=selected_tables)
    schema_text = "\n".join([
        f"{db}.{table}: {', '.join(columns)}" for db, tables in schema.items() for table, columns in tables.items()
    ])

    selection_hint = ""
    if database_name and selected_tables:
        table_list_text = ", ".join([f"`{database_name}`.`{table}`" for table in selected_tables])
        selection_hint = (
            f"Use database `{database_name}` and prioritize these tables: {table_list_text}. "
            "Use fully qualified table names. "
            "If user asks JOIN/UNION, operate only on these selected tables."
        )
    elif database_name:
        selection_hint = (
            f"Use database `{database_name}` only and prefer fully qualified table names."
        )

    prompt = f"""
    You are an SQL expert. Convert the following natural language query into an optimized MySQL query.
    - Use indexing where applicable.
    - Prefer JOINS over subqueries.
    - Use GROUP BY for aggregations if needed.
    - Return only one read-only SQL query.
    - Use ONLY tables and columns present in the schema below.
    - Do not invent column names.
    - For JOIN queries, prefer joining on matching key columns (for example: id, student_id, user_id).
    - For UNION queries, ensure both SELECT branches return the same number of columns with compatible types.
    - Prefer `SELECT *` only when the user asks for all details.
    - {selection_hint}

    Database Schema (Limited View):
    {schema_text}

    User Query: {nl_query}

    SQL Query:
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a SQL optimization expert. "
                        "Generate only read-only MySQL SQL statements."
                    ),
                },
                {"role": "user", "content": prompt}
            ]
        )
        
        raw_sql_query = response.choices[0].message.content.strip()
        cleaned_sql_query = clean_sql_output(raw_sql_query)
        _validate_generated_sql(cleaned_sql_query)
        return cleaned_sql_query

    except ValueError as e:
        return f"Error generating SQL query: {e}"
    except Exception as e:
        return f"Error generating SQL query: {e}"


def _validate_sql_read_only(sql_query: str) -> None:
    if not READ_ONLY_SQL_PATTERN.search(sql_query):
        raise ValueError("Only read-only SQL is allowed (SELECT/WITH/SHOW/DESCRIBE/EXPLAIN).")
    if BLOCKED_SQL_PATTERN.search(sql_query):
        raise ValueError("Write/DDL SQL statements are blocked for safety.")


def execute_query(sql_query):
    try:
        _validate_sql_read_only(sql_query)
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            rows = result.fetchall()

            column_names = result.keys()
            formatted_results = [dict(zip(column_names, row)) for row in rows]

        return {"results": formatted_results}
    except ValueError as e:
        return {"error": str(e)}
    except SQLAlchemyError as e:
        return {"error": str(e)}
