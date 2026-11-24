"""Config, MySQL connection, schema reading and query execution."""
import os
import re
from functools import lru_cache

import certifi
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

import safety

load_dotenv()

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def get_setting(name: str, default: str = "") -> str:
    """Read a setting from Streamlit secrets first, then from .env / environment."""
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass  # no secrets.toml, or not running under Streamlit
    return os.getenv(name, default)


def demo_config() -> dict:
    """Connection settings for the demo database (from secrets or .env)."""
    return {
        "host": get_setting("MYSQL_HOST", "localhost"),
        "port": int(get_setting("MYSQL_PORT", "3306")),
        "user": get_setting("MYSQL_USER", "root"),
        "password": get_setting("MYSQL_PASSWORD", ""),
        "database": get_setting("MYSQL_DATABASE", ""),
        "ssl": get_setting("MYSQL_SSL", "false").lower() in ("1", "true", "yes"),
    }


@lru_cache(maxsize=8)
def _cached_engine(host, port, user, password, database, ssl):
    url = URL.create(
        "mysql+pymysql",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database or None,
    )
    connect_args = {"connect_timeout": 10}
    if ssl:  # cloud MySQL such as TiDB Cloud requires TLS
        connect_args["ssl"] = {"ca": certifi.where()}
    return create_engine(url, pool_pre_ping=True, pool_recycle=280, connect_args=connect_args)


def get_engine(cfg: dict | None = None):
    """Return a (cached) SQLAlchemy engine. Defaults to the demo database."""
    cfg = cfg or demo_config()
    return _cached_engine(
        cfg["host"], int(cfg["port"]), cfg["user"], cfg["password"], cfg["database"], bool(cfg["ssl"])
    )


def _check_identifier(value: str, kind: str) -> str:
    if not value or not SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {kind} name.")
    return value


def list_databases(engine) -> list[str]:
    with engine.connect() as conn:
        return [row[0] for row in conn.execute(text("SHOW DATABASES"))]


def list_tables(engine, database: str) -> list[str]:
    db = _check_identifier(database, "database")
    with engine.connect() as conn:
        return [row[0] for row in conn.execute(text(f"SHOW TABLES FROM `{db}`"))]


def list_columns(engine, database: str, table: str) -> list[str]:
    db = _check_identifier(database, "database")
    tbl = _check_identifier(table, "table")
    with engine.connect() as conn:
        return [row[0] for row in conn.execute(text(f"SHOW COLUMNS FROM `{db}`.`{tbl}`"))]


def explain(engine, sql: str) -> None:
    """Run EXPLAIN to check SQL against the real schema. Raises on error."""
    with engine.connect() as conn:
        conn.execute(text(f"EXPLAIN {sql}"))


def run_query(engine, sql: str) -> list[dict]:
    """Run a read-only query and return rows as a list of dicts."""
    safety.check_read_only(sql)
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]
