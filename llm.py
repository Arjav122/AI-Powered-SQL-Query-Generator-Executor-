"""OpenAI prompts: generate SQL, fix SQL, explain SQL."""
import json

from openai import OpenAI

import db
import safety

MAX_TABLES = 5
MAX_COLUMNS_PER_TABLE = 5
MAX_ATTEMPTS = 3
SYSTEM_DATABASES = {"information_schema", "mysql", "performance_schema", "sys"}

SYSTEM_PROMPT = """You are an expert MySQL assistant that writes ONE read-only query.
Rules:
- Use ONLY tables and columns from the schema. Never invent names.
- Use fully qualified table names (database.table).
- Only SELECT, WITH...SELECT, SHOW, DESCRIBE or EXPLAIN. Never modify data.
- If the request needs INSERT/UPDATE/DELETE/DDL, return "sql": "" and say why in "explanation".
- Prefer JOINs over subqueries; join on matching key columns. Use GROUP BY for aggregations.
- UNION branches must return the same number of compatible columns.
- Use SELECT * only when the user asks for all details.
Reply with JSON only:
{"sql": "<one MySQL query>", "explanation": "<1-2 plain English sentences>", "tables_used": ["db.table", ...]}"""


def get_client() -> OpenAI:
    api_key = db.get_setting("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing (set it in .env or Streamlit secrets).")
    return OpenAI(api_key=api_key)


def get_model() -> str:
    return db.get_setting("OPENAI_MODEL", "gpt-4o-mini")


def build_schema_text(engine, database: str | None = None, tables: list[str] | None = None) -> str:
    """Schema as 'db.table: col1, col2' lines (limited to keep the prompt small)."""
    selected = set(tables or [])
    databases = [database] if database else [d for d in db.list_databases(engine) if d not in SYSTEM_DATABASES]
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


def _chat_json(messages: list[dict]) -> tuple[dict, int]:
    """Call the model in JSON mode. Returns (parsed reply, prompt tokens used)."""
    response = get_client().chat.completions.create(
        model=get_model(),
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    reply = json.loads(response.choices[0].message.content or "{}")
    sql = str(reply.get("sql") or "").strip()
    if sql.startswith("```"):  # strip code fences if the model adds them anyway
        sql = sql.strip("`").removeprefix("sql").strip()
    reply["sql"] = sql
    reply["explanation"] = str(reply.get("explanation") or "")
    reply["tables_used"] = list(reply.get("tables_used") or [])
    return reply, response.usage.prompt_tokens if response.usage else 0


def _check(engine, sql: str) -> str:
    """Validate SQL and, for SELECT-type queries, run EXPLAIN. Returns safe SQL or raises."""
    safe_sql = safety.validate(sql)
    if safety.needs_explain_check(safe_sql):
        db.explain(engine, safe_sql)
    return safe_sql


def generate_sql(engine, question: str, database: str | None = None, tables: list[str] | None = None) -> dict:
    """Generate SQL, then self-correct up to MAX_ATTEMPTS times using EXPLAIN errors.

    Returns {"sql", "explanation", "tables_used", "attempts", "prompt_tokens", "error"}.
    "error" is None on success. "attempts" lists every try as {"sql", "error"}.
    """
    schema_text = build_schema_text(engine, database, tables)
    focus = ""
    if database and tables:
        focus = f"\nFocus on database `{database}`, tables: {', '.join(tables)}."
    elif database:
        focus = f"\nUse database `{database}` only."

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nSchema:\n{schema_text}{focus}"},
        {"role": "user", "content": question},
    ]
    result = {"sql": "", "explanation": "", "tables_used": [], "attempts": [], "prompt_tokens": 0, "error": None}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        reply, tokens = _chat_json(messages)
        result["prompt_tokens"] += tokens
        result.update(sql=reply["sql"], explanation=reply["explanation"], tables_used=reply["tables_used"])

        if not reply["sql"]:  # model refused (e.g. user asked to delete data)
            result["error"] = reply["explanation"] or "The model did not return SQL."
            result["attempts"].append({"sql": "", "error": result["error"]})
            return result
        try:
            result["sql"] = _check(engine, reply["sql"])
            result["attempts"].append({"sql": result["sql"], "error": None})
            return result
        except Exception as exc:
            error = str(exc).splitlines()[0][:500]
            result["attempts"].append({"sql": reply["sql"], "error": error})
            # Feed the failed SQL and its error back so the model can fix it.
            messages += [
                {"role": "assistant", "content": json.dumps(reply)},
                {"role": "user", "content": f"That SQL failed with this error:\n{error}\nFix it. Reply with the same JSON format."},
            ]

    result["error"] = f"Could not produce valid SQL after {MAX_ATTEMPTS} attempts: {result['attempts'][-1]['error']}"
    return result


def explain_sql(sql: str) -> str:
    """Plain-English explanation of any SQL (used when the user edits the query)."""
    response = get_client().chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": "Explain what this MySQL query does in 1-2 simple sentences for a non-technical user."},
            {"role": "user", "content": sql},
        ],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()
