"""Read-only SQL checks. (Phase 2 replaces these regex checks with sqlglot.)"""
import re

READ_ONLY_START = re.compile(r"^\s*(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN)\b", re.IGNORECASE)
BLOCKED_WORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|RENAME|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def check_read_only(sql: str) -> None:
    """Raise ValueError if the SQL is not a read-only statement."""
    if not READ_ONLY_START.search(sql):
        raise ValueError("Only read-only SQL is allowed (SELECT/WITH/SHOW/DESCRIBE/EXPLAIN).")
    if BLOCKED_WORDS.search(sql):
        raise ValueError("Write/DDL SQL statements are blocked for safety.")
