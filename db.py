"""Config, MySQL connection (SSL optional), schema reading and query execution."""
import hashlib
import ipaddress
import json
import os
import re
import socket
from functools import lru_cache

import certifi
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

import safety

load_dotenv()

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")
QUERY_TIMEOUT_SECONDS = 10
SYSTEM_DATABASES = {"information_schema", "mysql", "performance_schema", "sys"}
SENSITIVE_COLUMN = re.compile(r"password|passwd|pwd|email|phone|mobile|token|secret|api_?key|(^|_)ssn($|_)", re.IGNORECASE)
MAX_TABLES_TO_INDEX = 200


# ---------- Config ----------

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


def connection_key(cfg: dict) -> str:
    """Short id for a connection (host + port + database). Used to name its Chroma collections.

    Keys for user connections start with "mem", which tells rag.py to keep them in memory only.
    """
    raw = f"{cfg['host'].lower()}:{cfg['port']}/{cfg['database']}"
    prefix = "mem" if cfg.get("memory_only") else ""
    return prefix + hashlib.sha256(raw.encode()).hexdigest()[:12]


def is_private_host(host: str) -> bool:
    """True if the host resolves to a loopback/private/link-local address (blocked for user connections)."""
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        return False  # can't resolve; the connection test will fail anyway
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
            return True
    return False


# ---------- Connection ----------

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
    # read_timeout is a backstop; the main limit is max_execution_time in run_query().
    connect_args = {"connect_timeout": 10, "read_timeout": QUERY_TIMEOUT_SECONDS + 20}
    if ssl:  # cloud MySQL such as TiDB Cloud requires TLS
        connect_args["ssl"] = {"ca": certifi.where()}
    return create_engine(url, pool_pre_ping=True, pool_recycle=280, connect_args=connect_args)


def get_engine(cfg: dict | None = None):
    """Return a (cached) SQLAlchemy engine. Defaults to the demo database."""
    cfg = cfg or demo_config()
    return _cached_engine(
        cfg["host"], int(cfg["port"]), cfg["user"], cfg["password"], cfg["database"], bool(cfg["ssl"])
    )


def test_connection(engine) -> None:
    """Run SELECT 1. Raises if the database can't be reached."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


WRITE_PRIVILEGES = {
    "ALL", "ALL PRIVILEGES", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "INDEX",
    "TRIGGER", "CREATE VIEW", "CREATE ROUTINE", "ALTER ROUTINE", "EVENT", "FILE", "SUPER",
    "CREATE USER", "GRANT OPTION", "SHUTDOWN", "RELOAD",
}


def write_privileges(engine) -> list[str]:
    """Privileges the connected user has that could change data (empty list = read-only user).

    Uses SHOW GRANTS, which only reads the user's own permissions.
    """
    found = set()
    with engine.connect() as conn:
        grants = [row[0] for row in conn.execute(text("SHOW GRANTS FOR CURRENT_USER()"))]
    for grant in grants:
        match = re.match(r"GRANT (.+?) ON ", grant)
        if match:  # e.g. "GRANT SELECT, INSERT ON `shop`.* TO ..."
            privileges = {p.strip().upper() for p in match.group(1).split(",")}
            found |= privileges & WRITE_PRIVILEGES
        if "WITH GRANT OPTION" in grant.upper():
            found.add("GRANT OPTION")
    return sorted(found)


# ---------- Schema browsing ----------

def _check_identifier(value: str, kind: str) -> str:
    if not value or not SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {kind} name.")
    return value


def list_databases(engine) -> list[str]:
    with engine.connect() as conn:
        return [row[0] for row in conn.execute(text("SHOW DATABASES"))]


def user_databases(engine, cfg: dict) -> list[str]:
    """Databases the assistant works on: the configured one, else all non-system databases."""
    if cfg.get("database"):
        return [cfg["database"]]
    return [d for d in list_databases(engine) if d.lower() not in SYSTEM_DATABASES]


def list_tables(engine, database: str) -> list[str]:
    db = _check_identifier(database, "database")
    with engine.connect() as conn:
        return [row[0] for row in conn.execute(text(f"SHOW TABLES FROM `{db}`"))]


def list_columns(engine, database: str, table: str) -> list[dict]:
    db = _check_identifier(database, "database")
    tbl = _check_identifier(table, "table")
    with engine.connect() as conn:
        rows = conn.execute(text(f"SHOW COLUMNS FROM `{db}`.`{tbl}`")).mappings().all()
    return [{"name": r["Field"], "type": r["Type"], "key": r["Key"], "nullable": r["Null"]} for r in rows]


# ---------- Schema for RAG ----------

def read_schema(engine, databases: list[str]) -> list[dict]:
    """Structure of every table: columns + types, primary key, foreign keys (no data)."""
    if not databases:
        return []
    params = {f"d{i}": d for i, d in enumerate(databases)}
    in_list = ", ".join(f":{k}" for k in params)
    with engine.connect() as conn:
        columns = conn.execute(text(
            f"SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, COLUMN_KEY "
            f"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA IN ({in_list}) "
            f"ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION"), params).fetchall()
        fks = conn.execute(text(
            f"SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_SCHEMA, "
            f"REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
            f"WHERE TABLE_SCHEMA IN ({in_list}) AND REFERENCED_TABLE_NAME IS NOT NULL"), params).fetchall()

    tables: dict[str, dict] = {}
    for schema, table, column, col_type, key in columns:
        name = f"{schema}.{table}"
        if name not in tables:
            if len(tables) >= MAX_TABLES_TO_INDEX:
                continue
            tables[name] = {"name": name, "database": schema, "table": table,
                            "columns": [], "primary_key": [], "foreign_keys": []}
        tables[name]["columns"].append({"name": column, "type": col_type})
        if key == "PRI":
            tables[name]["primary_key"].append(column)
    for schema, table, column, ref_schema, ref_table, ref_column in fks:
        name = f"{schema}.{table}"
        if name in tables:
            tables[name]["foreign_keys"].append(
                {"column": column, "ref_table": f"{ref_schema}.{ref_table}", "ref_column": ref_column})
    return list(tables.values())


def schema_hash(schema: list[dict]) -> str:
    """Fingerprint of the schema structure. Changes only when tables/columns/keys change."""
    return hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()


def add_sample_values(engine, schema: list[dict], per_column: int = 3) -> None:
    """Add up to `per_column` distinct example values to each column (skips sensitive/long columns)."""
    with engine.connect() as conn:
        conn.execute(text(f"SET SESSION max_execution_time = {QUERY_TIMEOUT_SECONDS * 1000}"))
        for table in schema:
            db_name = _check_identifier(table["database"], "database")
            tbl = _check_identifier(table["table"], "table")
            for col in table["columns"]:
                col["samples"] = []
                skip_type = re.match(r"(tiny|medium|long)?(blob|text)|binary|varbinary|json|geometry", col["type"])
                if SENSITIVE_COLUMN.search(col["name"]) or skip_type or not SAFE_IDENTIFIER.fullmatch(col["name"]):
                    continue
                try:
                    rows = conn.execute(text(
                        f"SELECT DISTINCT `{col['name']}` FROM `{db_name}`.`{tbl}` "
                        f"WHERE `{col['name']}` IS NOT NULL LIMIT {per_column}")).fetchall()
                    col["samples"] = [str(r[0])[:40] for r in rows]
                except Exception:
                    pass  # samples are optional; never fail indexing because of one column


# ---------- Running queries ----------

def explain(engine, sql: str) -> None:
    """Run EXPLAIN on validated SQL to check it against the real schema. Raises on error."""
    sql = safety.validate(sql)
    with engine.connect() as conn:
        conn.execute(text(f"EXPLAIN {sql}"))


def run_query(engine, sql: str) -> list[dict]:
    """Validate, then run a read-only query with a timeout. Returns rows as a list of dicts."""
    sql = safety.validate(sql)
    with engine.connect() as conn:
        # MySQL/TiDB stop any SELECT that runs longer than this (value in milliseconds).
        conn.execute(text(f"SET SESSION max_execution_time = {QUERY_TIMEOUT_SECONDS * 1000}"))
        result = conn.execute(text(sql))
        # Rename duplicate column names (e.g. a.id, b.id -> id, id_2) so no data is lost.
        seen, columns = {}, []
        for name in result.keys():
            seen[name] = seen.get(name, 0) + 1
            columns.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
        return [dict(zip(columns, row)) for row in result.fetchall()]
