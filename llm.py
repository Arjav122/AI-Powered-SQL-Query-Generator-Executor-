"""OpenAI prompts that turn English questions into MySQL queries."""
import re

from openai import OpenAI

import db
import safety

MAX_TABLES = 5
MAX_COLUMNS_PER_TABLE = 5


def get_client() -> OpenAI:
    api_key = db.get_setting("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing (set it in .env or Streamlit secrets).")
    return OpenAI(api_key=api_key)


def get_model() -> str:
    return db.get_setting("OPENAI_MODEL", "gpt-4o-mini")


def clean_sql_output(response_text: str) -> str:
    """Pull the SQL statement out of the model's reply."""
    fenced = re.findall(r"```sql\s*(.*?)\s*```", response_text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced[0].strip()
        return candidate if candidate.endswith(";") else f"{candidate};"

    clean = response_text.strip()
    patterns = [
        r"(SELECT\s+.*?;)",
        r"(SHOW\s+.*?;)",
        r"(DESCRIBE\s+.*?;)",
        r"(EXPLAIN\s+.*?;)",
        r"(WITH\s+\w+\s+AS\s*\(.*?\)\s*SELECT\s+.*?;)",
    ]
    for pattern in patterns:
        match = re.search(pattern, clean, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    first_line = clean.splitlines()[0].strip() if clean else ""
    if re.match(r"^(SELECT|SHOW|DESCRIBE|EXPLAIN)\b", first_line, flags=re.IGNORECASE):
        return f"{first_line.rstrip(';')};"
    return clean


def build_schema_text(engine, database: str | None = None, tables: list[str] | None = None) -> str:
    """Schema as 'db.table: col1, col2' lines (limited to keep the prompt small)."""
    selected = set(tables or [])
    databases = [database] if database else db.list_databases(engine)
    lines = []
    for database_name in databases:
        db_tables = db.list_tables(engine, database_name)
        chosen = [t for t in db_tables if t in selected] if selected else db_tables[:MAX_TABLES]
        for table in chosen:
            columns = db.list_columns(engine, database_name, table)
            # Selected tables get all columns to reduce hallucinated column names.
            if table not in selected:
                columns = columns[:MAX_COLUMNS_PER_TABLE]
            lines.append(f"{database_name}.{table}: {', '.join(columns)}")
    return "\n".join(lines)


def generate_sql(engine, question: str, database: str | None = None, tables: list[str] | None = None) -> str:
    """Generate one read-only MySQL query for the question. Raises ValueError on failure."""
    client = get_client()
    schema_text = build_schema_text(engine, database, tables)

    hint = ""
    if database and tables:
        table_list = ", ".join(f"`{database}`.`{t}`" for t in tables)
        hint = (
            f"Use database `{database}` and prioritize these tables: {table_list}. "
            "Use fully qualified table names. "
            "If user asks JOIN/UNION, operate only on these selected tables."
        )
    elif database:
        hint = f"Use database `{database}` only and prefer fully qualified table names."

    prompt = f"""
    You are an SQL expert. Convert the following natural language query into an optimized MySQL query.
    - Prefer JOINS over subqueries.
    - Use GROUP BY for aggregations if needed.
    - Return only one read-only SQL query.
    - Use ONLY tables and columns present in the schema below.
    - Do not invent column names.
    - For JOIN queries, prefer joining on matching key columns (for example: id, student_id, user_id).
    - For UNION queries, ensure both SELECT branches return the same number of columns with compatible types.
    - Prefer `SELECT *` only when the user asks for all details.
    - {hint}

    Database Schema (Limited View):
    {schema_text}

    User Query: {question}

    SQL Query:
    """

    response = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": "You are a SQL optimization expert. Generate only read-only MySQL SQL statements."},
            {"role": "user", "content": prompt},
        ],
    )
    sql = clean_sql_output(response.choices[0].message.content or "")

    safety.check_read_only(sql)
    if re.match(r"^\s*(SELECT|WITH)\b", sql, flags=re.IGNORECASE):
        try:
            db.explain(engine, sql)
        except Exception as exc:
            raise ValueError(f"Generated SQL looks invalid for your schema. MySQL error: {exc}") from exc
    return sql
