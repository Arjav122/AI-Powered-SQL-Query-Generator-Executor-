"""Streamlit UI. Calls db.py / llm.py / rag.py directly (no separate backend needed)."""
try:  # Streamlit Cloud has an old sqlite3; ChromaDB needs a newer one (pysqlite3-binary, Linux only).
    __import__("pysqlite3")
    import sys

    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import datetime
import decimal
import re

import pandas as pd
import streamlit as st

import db
import llm
import rag
import safety

st.set_page_config(page_title="AI SQL Assistant", page_icon="🧠", layout="wide")
st.title("🧠 AI SQL Assistant")
st.caption("Ask questions in plain English. Get read-only SQL, an explanation, and results.")

ss = st.session_state
ss.setdefault("history", [])   # last 20 generations, newest first
ss.setdefault("own_cfg", None)  # credentials for "Connect my own" (session memory only)
ss.setdefault("indexed", {})   # connection key -> index status
# Values set by buttons are applied here, before the widgets that own them are drawn.
for widget_key in ("question", "sql_box"):
    if f"pending_{widget_key}" in ss:
        ss[widget_key] = ss.pop(f"pending_{widget_key}")


# ---------- Helpers ----------

def to_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Rows -> DataFrame with MySQL Decimals as floats and dates as datetimes (so charts work)."""
    df = pd.DataFrame(rows)
    for col in df.columns:
        values = df[col].dropna()
        if values.empty:
            continue
        if isinstance(values.iloc[0], decimal.Decimal):
            df[col] = df[col].astype(float)
        elif isinstance(values.iloc[0], (datetime.date, datetime.datetime)):
            df[col] = pd.to_datetime(df[col])
    return df


def is_date_column(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    values = series.dropna().astype(str)  # also accept '2024-05' / '2024-05-01' strings
    return not values.empty and values.str.fullmatch(r"\d{4}-\d{2}(-\d{2})?").all()


def draw_chart(df: pd.DataFrame) -> None:
    """1 text + 1 number column -> bar chart; 1 date + 1 number column -> line chart; else nothing."""
    if len(df.columns) != 2 or len(df) < 2:
        return
    is_number = pd.api.types.is_numeric_dtype
    for label, value in (df.columns, df.columns[::-1]):
        if not is_number(df[value]) or is_number(df[label]):
            continue
        if is_date_column(df[label]):
            chart_df = df.assign(**{label: pd.to_datetime(df[label].astype(str))}).sort_values(label)
            st.line_chart(chart_df, x=label, y=value)
        else:
            st.bar_chart(df, x=label, y=value)
        return


def set_feedback(question: str, value: str) -> None:
    for item in ss.history:
        if item["question"] == question:
            item["feedback"] = value


@st.cache_data(ttl=300, show_spinner=False)
def cached_tables(_engine, conn_key: str, database: str) -> list[str]:
    return db.list_tables(_engine, database)


@st.cache_data(ttl=300, show_spinner=False)
def cached_columns(_engine, conn_key: str, database: str, table: str) -> list[dict]:
    return db.list_columns(_engine, database, table)


# ---------- Sidebar: connection, RAG, history ----------

with st.sidebar:
    st.header("Database")
    mode = st.radio("Connection", ["Demo database", "Connect my own"], horizontal=True)
    if mode == "Demo database":
        cfg = db.demo_config()
    else:
        st.info("🔒 Use a **read-only** MySQL user, not your admin account. The app only runs read-only "
                "queries, but a read-only user means your database itself refuses any change.")
        with st.expander("How to create a read-only user"):
            st.code("CREATE USER 'ai_reader'@'%' IDENTIFIED BY 'strong-password';\n"
                    "GRANT SELECT, SHOW VIEW ON your_database.* TO 'ai_reader'@'%';", language="sql")
            st.caption("Delete it any time with: DROP USER 'ai_reader'@'%';")
        with st.form("own_db"):
            host = st.text_input("Host", placeholder="gateway01.xx.prod.aws.tidbcloud.com")
            port = st.number_input("Port", value=4000, min_value=1, max_value=65535)
            user = st.text_input("User")
            password = st.text_input("Password", type="password")
            database = st.text_input("Database (optional)")
            use_ssl = st.checkbox("Use SSL", value=True)
            submitted = st.form_submit_button("Connect")
        if submitted:
            new_cfg = {"host": host.strip(), "port": int(port), "user": user.strip(),
                       "password": password, "database": database.strip(), "ssl": use_ssl}
            if not new_cfg["host"] or not new_cfg["user"]:
                st.error("Host and user are required.")
            elif db.is_private_host(new_cfg["host"]):
                st.error("Local/private addresses (localhost, 127.x, 10.x, 172.16-31.x, 192.168.x) are not allowed here.")
            else:
                try:
                    new_engine = db.get_engine(new_cfg)
                    db.test_connection(new_engine)
                    ss.own_cfg = new_cfg
                    try:
                        ss.own_write_privileges = db.write_privileges(new_engine)
                    except Exception:
                        ss.own_write_privileges = None  # couldn't check (unusual setup)
                except Exception as exc:
                    ss.own_cfg = None
                    st.error(f"Connection failed: {exc}")
        cfg = ss.own_cfg
        if cfg is None:
            st.info("Fill in the form and click Connect.")
        else:
            privileges = ss.get("own_write_privileges")
            if privileges:
                st.warning("⚠️ This user can change data (" + ", ".join(privileges[:6])
                           + (", ..." if len(privileges) > 6 else "") + "). The app still blocks every "
                           "write query, but a read-only user is safer.")
            elif privileges is None:
                st.caption("Could not check this user's permissions.")
            else:
                st.caption("✅ Read-only user: the database itself will refuse any change.")

    if cfg is not None:
        engine = db.get_engine(cfg)
        conn_key = db.connection_key(cfg)
        if conn_key not in ss.indexed:  # first use in this session: test, then index if schema changed
            try:
                db.test_connection(engine)
                with st.spinner("Indexing schema..."):
                    ss.indexed[conn_key] = rag.ensure_index(engine, cfg)
                    if mode == "Demo database":
                        rag.seed_examples(conn_key)
            except Exception as exc:
                st.error(f"Database not ready: {exc}")
                st.stop()
        st.success(f"Connected · {ss.indexed[conn_key]['tables']} tables indexed")

        use_rag = st.toggle("Use RAG (relevant tables + examples)", value=True,
                            help="Off = send the full schema with no examples (baseline).")
        if st.button("Re-index schema", width="stretch"):
            with st.spinner("Re-indexing..."):
                ss.indexed[conn_key] = rag.ensure_index(engine, cfg, force=True)
            st.toast(f"Re-indexed {ss.indexed[conn_key]['tables']} tables")
        st.caption("ℹ️ Table/column names and a few sample values are sent to OpenAI to generate SQL.")

    st.header("History")
    if not ss.history:
        st.caption("Your last 20 questions will appear here.")
    for i, item in enumerate(ss.history):
        mark = {"up": "👍 ", "down": "👎 "}.get(item.get("feedback"), "")
        if st.button(f"{mark}{item['question'][:45]}", key=f"history_{i}", width="stretch"):
            ss.pending_question, ss.pending_sql_box = item["question"], item["sql"]
            ss.generation, ss.result = item["generation"], None
            st.rerun()

if cfg is None:
    st.info("Connect to a database from the sidebar to start.")
    st.stop()

# ---------- Main tabs ----------

ask_tab, schema_tab = st.tabs(["Ask", "Schema"])

with ask_tab:
    question = st.text_area("Your question", key="question", height=90,
                            placeholder="Example: Total fees collected from students in each city")
    if st.button("Generate SQL", type="primary"):
        if len(question.strip()) < 3:
            st.warning("Please type a question first.")
        else:
            try:
                with st.spinner("Retrieving schema and generating SQL..."):
                    gen = llm.generate_sql(engine, cfg, question, use_rag=use_rag)
            except Exception as exc:
                gen = {"error": str(exc), "sql": "", "attempts": [], "retrieved": [], "explanation": ""}
            ss.generation, ss.result = gen, None
            if not gen["error"]:
                ss.history.insert(0, {"question": question, "sql": gen["sql"], "generation": gen})
                del ss.history[20:]
            ss.pending_sql_box = gen["sql"]
            st.rerun()

    gen = ss.get("generation")
    if gen:
        if gen.get("retrieved"):
            colors = {"similarity": "blue", "foreign key": "orange", "full schema": "gray"}
            chips = " ".join(f":{colors[t['via']]}-badge[{t['name']}]" for t in gen["retrieved"])
            st.markdown(f"**Tables sent to the model:** {chips}")
            if any(t["via"] == "foreign key" for t in gen["retrieved"]):
                st.caption("Blue = similar to your question · Orange = linked by a foreign key")
        if gen.get("error"):
            st.error(f"Could not generate SQL: {gen['error']}")
        else:
            st.markdown(f"**What this query does:** {gen['explanation']}")
        attempts = gen.get("attempts", [])
        if attempts:
            with st.expander(f"Attempts ({len(attempts)})", expanded=len(attempts) > 1):
                for i, attempt in enumerate(attempts, 1):
                    status = "✅ passed EXPLAIN check" if attempt["error"] is None else f"❌ {attempt['error']}"
                    st.markdown(f"**Attempt {i}:** {status}")
                    if attempt["sql"]:
                        st.code(attempt["sql"], language="sql")

    sql_text = st.text_area("SQL (you can edit it before running)", key="sql_box", height=130)
    run_col, explain_col, _ = st.columns([1, 1, 3])
    run_clicked = run_col.button("Run query", type="primary", width="stretch")
    if explain_col.button("Explain SQL", width="stretch"):
        try:
            with st.spinner("Explaining..."):
                st.info(llm.explain_sql(sql_text))
        except Exception as exc:
            st.error(f"Could not explain SQL: {exc}")

    if run_clicked:
        original = sql_text.strip().rstrip(";").strip()
        try:
            safe_sql = safety.validate(sql_text)
            with st.spinner("Running..."):
                rows = db.run_query(engine, safe_sql)
            ss.result = {"rows": rows, "sql": safe_sql, "original_sql": original,
                         "question": question, "limit_added": safe_sql != original}
        except ValueError as exc:
            ss.result = None
            st.error(f"Query blocked: {exc}")
        except Exception as exc:
            ss.result = None
            st.error(f"Error running query: {exc}")

    result = ss.get("result")
    if result:
        if result["limit_added"]:
            st.caption(f"LIMIT {safety.DEFAULT_LIMIT} was added automatically.")
        if not result["rows"]:
            st.info("Query ran successfully but returned no rows.")
        else:
            df = to_dataframe(result["rows"])
            st.dataframe(df, width="stretch", hide_index=True)
            st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode("utf-8"),
                               file_name="results.csv", mime="text/csv")
            draw_chart(df)

        up_col, down_col, _ = st.columns([1, 1, 3])
        if up_col.button("👍 Good answer", width="stretch"):
            try:
                rag.add_example(conn_key, result["question"], result["original_sql"])
                set_feedback(result["question"], "up")
                st.toast("Saved as an example for similar questions.")
            except Exception as exc:
                st.error(f"Could not save example: {exc}")
        if down_col.button("👎 Wrong", width="stretch"):
            set_feedback(result["question"], "down")
            st.toast("Thanks, noted. Try rephrasing or edit the SQL.")

with schema_tab:
    try:
        databases = db.user_databases(engine, cfg)
        db_col, table_col = st.columns(2)
        chosen_db = db_col.selectbox("Database", databases)
        tables = cached_tables(engine, conn_key, chosen_db) if chosen_db else []
        chosen_table = table_col.selectbox("Table", tables)
        if chosen_table:
            st.dataframe(pd.DataFrame(cached_columns(engine, conn_key, chosen_db, chosen_table)),
                         width="stretch", hide_index=True)
    except Exception as exc:
        st.error(f"Could not read schema: {exc}")
