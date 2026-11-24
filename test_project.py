"""Unit tests. No OpenAI calls and no database needed.

Run:  pytest -q
"""
import datetime
import decimal
from unittest import mock

import pytest

import db
import eval as evaluation
import llm
import rag
import safety


# ---------- safety.py ----------

@pytest.mark.parametrize("sql", [
    "SELECT name FROM customers",
    "WITH t AS (SELECT 1 AS x) SELECT x FROM t",
    "SELECT updated_at FROM orders",          # word 'update' inside a column name is fine
    "SELECT 1 UNION SELECT 2",
    "SHOW TABLES",
    "DESCRIBE customers",
    "EXPLAIN SELECT * FROM customers",
])
def test_read_only_queries_are_allowed(sql):
    assert safety.validate(sql)


@pytest.mark.parametrize("sql, reason", [
    ("DELETE FROM customers", "not allowed"),
    ("UPDATE products SET price = 0", "not allowed"),
    ("DROP TABLE customers", "not allowed"),
    ("INSERT INTO t VALUES (1)", "not allowed"),
    ("GRANT ALL ON *.* TO someone", "not allowed"),
    ("SELECT 1; DROP TABLE customers", "Exactly one"),
    ("SELECT * FROM customers FOR UPDATE", "LOCK"),
    ("SELECT LOAD_FILE('/etc/passwd')", "LOAD_FILE"),
    ("SELECT SLEEP(10)", "SLEEP"),
    ("SELECT * INTO OUTFILE '/tmp/x' FROM customers", "parse"),
    ("", "empty"),
])
def test_dangerous_queries_are_blocked(sql, reason):
    with pytest.raises(ValueError, match=reason):
        safety.validate(sql)


def test_limit_is_added_only_when_missing():
    assert safety.validate("SELECT * FROM customers").endswith("LIMIT 100")
    assert safety.validate("SELECT * FROM customers LIMIT 5").endswith("LIMIT 5")
    assert "LIMIT" not in safety.validate("SHOW TABLES")


def test_explain_check_only_for_select_queries():
    assert safety.needs_explain_check("SELECT 1")
    assert not safety.needs_explain_check("SHOW TABLES")


# ---------- db.py ----------

@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "10.0.0.5", "172.20.1.1", "192.168.1.10", "169.254.169.254"])
def test_private_hosts_are_blocked(host):
    assert db.is_private_host(host)


def test_public_ip_is_allowed():
    assert not db.is_private_host("8.8.8.8")


def test_user_connections_get_memory_only_keys():
    cfg = {"host": "example.com", "port": 4000, "database": "shop"}
    assert not db.connection_key(cfg).startswith("mem")
    assert db.connection_key({**cfg, "memory_only": True}).startswith("mem")
    assert db.connection_key(cfg) != db.connection_key({**cfg, "database": "other"})


def test_identifiers_are_validated():
    assert db._check_identifier("classicmodels", "database") == "classicmodels"
    with pytest.raises(ValueError):
        db._check_identifier("shop; DROP", "database")


def _engine_with_grants(lines):
    conn = mock.MagicMock()
    conn.__enter__.return_value.execute.return_value = [(line,) for line in lines]
    engine = mock.Mock()
    engine.connect.return_value = conn
    return engine


def test_write_privileges_detection():
    read_only = _engine_with_grants(["GRANT USAGE ON *.* TO `r`@`%`", "GRANT SELECT, SHOW VIEW ON `shop`.* TO `r`@`%`"])
    writer = _engine_with_grants(["GRANT SELECT, INSERT ON `shop`.* TO `w`@`%`"])
    admin = _engine_with_grants(["GRANT ALL PRIVILEGES ON *.* TO `a`@`%` WITH GRANT OPTION"])
    assert db.write_privileges(read_only) == []
    assert db.write_privileges(writer) == ["INSERT"]
    assert db.write_privileges(admin) == ["ALL PRIVILEGES", "GRANT OPTION"]


# ---------- rag.py (in-memory Chroma, fake 3-number embeddings) ----------

@pytest.fixture
def memory_key():
    key = "memtest000001"
    yield key
    rag.forget(key)


def test_table_document_contains_columns_keys_and_samples():
    doc = rag.table_document({
        "name": "shop.orders", "primary_key": ["id"],
        "columns": [{"name": "id", "type": "int", "samples": ["1", "2"]}, {"name": "status", "type": "varchar(10)"}],
        "foreign_keys": [{"column": "customer_id", "ref_table": "shop.customers", "ref_column": "id"}],
    })
    assert "Table: shop.orders" in doc and "status (varchar(10))" in doc
    assert "e.g. '1', '2'" in doc and "Foreign key: customer_id -> shop.customers.id" in doc


def test_retrieval_adds_foreign_key_tables_and_respects_database_filter(memory_key):
    col = rag._schema_collection(memory_key)
    col.add(
        ids=["shop.orders", "shop.customers", "shop.reviews", "hospital.invoices"],
        documents=["orders", "customers", "reviews", "invoices"],
        embeddings=[[1, 0, 0], [0, 1, 0], [0, 0.2, 1], [0.95, 0.05, 0]],
        metadatas=[{"database": "shop", "fk_targets": "shop.customers"}, {"database": "shop", "fk_targets": ""},
                   {"database": "shop", "fk_targets": ""}, {"database": "hospital", "fk_targets": ""}],
    )
    everywhere = {t["name"]: t["via"] for t in rag.retrieve_tables(memory_key, [1, 0, 0], k=2)}
    assert everywhere["shop.orders"] == "similarity"
    assert "hospital.invoices" in everywhere          # similar table from another database
    assert everywhere["shop.customers"] == "foreign key"  # added because orders references it

    shop_only = {t["name"] for t in rag.retrieve_tables(memory_key, [1, 0, 0], k=2, database="shop")}
    assert "hospital.invoices" not in shop_only
    assert len(rag.all_tables(memory_key, "shop")) == 3


def test_examples_are_filtered_by_database(memory_key):
    rag._examples_collection(memory_key).add(
        ids=["a", "b"], documents=["total payments", "total invoices"], embeddings=[[1, 0, 0], [0.9, 0.1, 0]],
        metadatas=[{"sql": "SELECT SUM(amount) FROM shop.payments"}, {"sql": "SELECT SUM(total) FROM hospital.invoices"}],
    )
    assert len(rag.retrieve_examples(memory_key, [1, 0, 0], n=3)) == 2
    only_hospital = rag.retrieve_examples(memory_key, [1, 0, 0], n=3, database="hospital")
    assert [e["sql"] for e in only_hospital] == ["SELECT SUM(total) FROM hospital.invoices"]


# ---------- llm.py (model calls mocked) ----------

FAKE_CONTEXT = {"tables": [{"name": "shop.t", "document": "Table: shop.t", "via": "similarity"}], "examples": []}


def _reply(sql, explanation="ok", clarification=""):
    return {"sql": sql, "explanation": explanation, "tables_used": [], "clarification": clarification}, 100


def test_self_correction_retries_with_the_error():
    replies = iter([_reply("SELECT bad FROM shop.t"), _reply("SELECT good FROM shop.t")])
    seen_messages = []

    def fake_chat(messages):
        seen_messages.append(list(messages))
        return next(replies)

    def fake_check(engine, sql):
        if "bad" in sql:
            raise Exception("Unknown column 'bad'")
        return sql + " LIMIT 100"

    with mock.patch.object(llm, "build_context", return_value=FAKE_CONTEXT), \
            mock.patch.object(llm, "_chat_json", side_effect=fake_chat), \
            mock.patch.object(llm, "_check", side_effect=fake_check):
        result = llm.generate_sql(None, {}, "question")
    assert result["error"] is None and result["sql"] == "SELECT good FROM shop.t LIMIT 100"
    assert [a["error"] is None for a in result["attempts"]] == [False, True]
    assert "Unknown column 'bad'" in seen_messages[1][-1]["content"]  # the error was sent back to the model
    assert result["prompt_tokens"] == 200


def test_gives_up_after_three_attempts():
    with mock.patch.object(llm, "build_context", return_value=FAKE_CONTEXT), \
            mock.patch.object(llm, "_chat_json", return_value=_reply("SELECT bad FROM shop.t")), \
            mock.patch.object(llm, "_check", side_effect=Exception("still wrong")):
        result = llm.generate_sql(None, {}, "question")
    assert len(result["attempts"]) == 3 and "after 3 attempts" in result["error"]


def test_refusal_returns_no_sql():
    with mock.patch.object(llm, "build_context", return_value=FAKE_CONTEXT), \
            mock.patch.object(llm, "_chat_json", return_value=_reply("", "Deleting data is not allowed.")):
        result = llm.generate_sql(None, {}, "delete everything")
    assert result["sql"] == "" and "not allowed" in result["error"]


def test_clarifying_question_is_returned():
    with mock.patch.object(llm, "build_context", return_value=FAKE_CONTEXT), \
            mock.patch.object(llm, "_chat_json", return_value=_reply("", clarification="Which year do you mean?")):
        result = llm.generate_sql(None, {}, "sales last year or this year")
    assert result["clarification"] == "Which year do you mean?" and result["sql"] == ""


# ---------- eval.py ----------

def test_result_comparison_ignores_row_order_column_names_and_number_format():
    gold = [{"country": "France", "n": 12}, {"country": "USA", "n": 36}]
    generated = [{"total": decimal.Decimal("36.00"), "c": "USA"}, {"total": 12.0, "c": "France"}]
    assert evaluation.result_signature(gold) == evaluation.result_signature(generated)
    assert evaluation.result_signature(gold) != evaluation.result_signature(gold[:1])


def test_normalize_values():
    assert evaluation.normalize(None) == "NULL"
    assert evaluation.normalize(decimal.Decimal("3.456")) == "3.46"
    assert evaluation.normalize(datetime.date(2005, 3, 1)) == "2005-03-01"


def test_tables_in_gold_sql():
    sql = "SELECT * FROM classicmodels.orders o JOIN classicmodels.customers c ON c.customerNumber = o.customerNumber"
    assert evaluation.tables_in(sql) == {"classicmodels.orders", "classicmodels.customers"}
