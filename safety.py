"""Read-only SQL validation with sqlglot (parses SQL into a tree instead of using regex).

Run `python safety.py` to see the checks on example queries.
"""
import logging

import sqlglot
from sqlglot import exp

logging.getLogger("sqlglot").setLevel(logging.ERROR)  # hide "falling back to Command" warnings

DEFAULT_LIMIT = 100

# Node types that change data, schema or permissions. Rejected anywhere in the tree.
WRITE_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Drop, exp.Create, exp.Alter,
    exp.TruncateTable, exp.Command, exp.Set, exp.Into, exp.Lock,
)
# Functions that read server files, stall the server or take locks.
BLOCKED_FUNCTIONS = {"LOAD_FILE", "SLEEP", "BENCHMARK", "GET_LOCK", "RELEASE_LOCK"}


def validate(sql: str) -> str:
    """Return a safe version of `sql` (with LIMIT added if needed). Raise ValueError if not allowed."""
    if not sql or not sql.strip():
        raise ValueError("SQL is empty.")
    try:
        statements = [s for s in sqlglot.parse(sql, read="mysql") if s is not None]
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"Could not parse SQL: {str(exc).splitlines()[0]}") from exc

    if len(statements) != 1:
        raise ValueError(f"Exactly one SQL statement is allowed (found {len(statements)}).")
    tree = statements[0]

    # Allowed: SELECT (incl. WITH ... SELECT), UNION/INTERSECT/EXCEPT of SELECTs, SHOW, DESCRIBE/EXPLAIN.
    if isinstance(tree, exp.Command) or not isinstance(tree, (exp.Select, exp.SetOperation, exp.Show, exp.Describe)):
        name = tree.name.upper() if isinstance(tree, exp.Command) else tree.key.upper()
        raise ValueError(f"{name} statements are not allowed. Only SELECT, WITH...SELECT, SHOW, DESCRIBE, EXPLAIN.")

    for node in tree.walk():
        if isinstance(node, WRITE_NODES):
            raise ValueError(f"Blocked: the query contains a {node.key.upper()} clause (read-only mode).")
        if isinstance(node, exp.Func):
            func_name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name()
            if func_name in BLOCKED_FUNCTIONS:
                raise ValueError(f"Blocked: function {func_name}() is not allowed.")

    # Auto-add LIMIT so a query can't pull millions of rows into the browser.
    if isinstance(tree, (exp.Select, exp.SetOperation)) and not tree.args.get("limit"):
        return tree.limit(DEFAULT_LIMIT).sql(dialect="mysql")
    return sql.strip().rstrip(";").strip()


def needs_explain_check(sql: str) -> bool:
    """True for SELECT/WITH/UNION queries, which can be checked with EXPLAIN before running."""
    try:
        return isinstance(sqlglot.parse_one(sql, read="mysql"), (exp.Select, exp.SetOperation))
    except Exception:
        return False


if __name__ == "__main__":
    examples = [
        "SELECT name FROM students",
        "WITH t AS (SELECT 1 AS x) SELECT x FROM t",
        "SELECT updated_at FROM orders LIMIT 5",
        "SHOW TABLES",
        "DESCRIBE students",
        "EXPLAIN SELECT * FROM students",
        "SELECT 1; DROP TABLE students",
        "DELETE FROM students",
        "GRANT ALL ON *.* TO hacker",
        "SELECT * FROM students FOR UPDATE",
        "SELECT LOAD_FILE('/etc/passwd')",
        "SELECT * INTO OUTFILE '/tmp/x' FROM students",
    ]
    for q in examples:
        try:
            print(f"ALLOW  {q}\n       -> {validate(q)}")
        except ValueError as e:
            print(f"BLOCK  {q}\n       -> {e}")
