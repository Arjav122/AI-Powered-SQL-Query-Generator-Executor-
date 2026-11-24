"""Streamlit UI. Calls db.py / llm.py directly (no separate backend needed)."""
import streamlit as st

import db
import llm
import safety

st.set_page_config(page_title="AI SQL Assistant", page_icon="🧠", layout="wide")
st.title("🧠 AI SQL Assistant")
st.caption("Generate and run read-only SQL queries from natural language.")

st.session_state.setdefault("generated_sql", "")
st.session_state.setdefault("databases", [])

try:
    engine = db.get_engine()
except Exception as exc:
    st.error(f"Could not set up the database connection: {exc}")
    st.stop()

# ---------- Sidebar: 3-level schema browser ----------
st.sidebar.header("Schema Explorer")
if st.sidebar.button("Refresh Databases"):
    try:
        st.session_state.databases = db.list_databases(engine)
    except Exception as exc:
        st.sidebar.error(f"Unable to fetch databases: {exc}")

selected_db = st.sidebar.selectbox("Database", [""] + st.session_state.databases)
tables = []
if selected_db:
    try:
        tables = db.list_tables(engine, selected_db)
    except Exception as exc:
        st.sidebar.error(f"Unable to fetch tables: {exc}")

selected_tables = st.sidebar.multiselect("Tables (for JOIN/UNION)", tables)
for table_name in selected_tables[:3]:
    try:
        st.sidebar.write(f"Columns: {table_name}")
        st.sidebar.write(db.list_columns(engine, selected_db, table_name))
    except Exception as exc:
        st.sidebar.error(f"Unable to fetch columns for {table_name}: {exc}")

if tables:
    st.sidebar.write("Suggested tables")
    st.sidebar.write(tables[:3])

# ---------- Main: generate + run ----------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Generate SQL")
    if not selected_db:
        st.info("Select a database from sidebar first for better SQL quality.")
    elif not selected_tables:
        st.info("Select one or more tables from sidebar for accurate JOIN/UNION queries.")
    question = st.text_area(
        "Ask in plain English",
        placeholder="Example: Show top 10 customers by total order value.",
        height=180,
    )
    if st.button("Generate SQL", type="primary"):
        if len(question.strip()) < 3:
            st.warning("Please type a question first.")
        else:
            try:
                with st.spinner("Generating SQL (with self-correction)..."):
                    st.session_state.generation = llm.generate_sql(
                        engine, question, selected_db or None, selected_tables or None
                    )
            except Exception as exc:
                st.session_state.generation = {"error": str(exc), "attempts": [], "sql": ""}
            st.session_state.generated_sql = st.session_state.generation.get("sql", "")

    gen = st.session_state.get("generation")
    if gen:
        if gen.get("error"):
            st.error(f"Error generating SQL: {gen['error']}")
        else:
            st.code(gen["sql"], language="sql")
            st.markdown(f"**What this query does:** {gen['explanation']}")
            if gen.get("tables_used"):
                st.caption("Tables used: " + ", ".join(gen["tables_used"]))
        attempts = gen.get("attempts", [])
        if attempts:
            with st.expander(f"Attempts ({len(attempts)})", expanded=len(attempts) > 1):
                for i, attempt in enumerate(attempts, 1):
                    status = "✅ passed EXPLAIN check" if attempt["error"] is None else f"❌ {attempt['error']}"
                    st.markdown(f"**Attempt {i}:** {status}")
                    if attempt["sql"]:
                        st.code(attempt["sql"], language="sql")

with col2:
    st.subheader("Execute SQL")
    sql_to_run = st.text_area("Read-only SQL only (you can edit it)", value=st.session_state.generated_sql, height=180)
    run_col, explain_col = st.columns(2)
    if explain_col.button("Explain this SQL"):
        try:
            with st.spinner("Explaining..."):
                st.info(llm.explain_sql(sql_to_run))
        except Exception as exc:
            st.error(f"Could not explain SQL: {exc}")
    if run_col.button("Run Query", type="primary"):
        try:
            safe_sql = safety.validate(sql_to_run)
            if safe_sql != sql_to_run.strip().rstrip(";").strip():
                st.caption(f"Ran as: `{safe_sql}` (LIMIT {safety.DEFAULT_LIMIT} added automatically)")
            rows = db.run_query(engine, safe_sql)
            if rows:
                st.dataframe(rows, width="stretch")
            else:
                st.info("Query ran successfully but returned no rows.")
        except ValueError as exc:
            st.error(f"Query blocked: {exc}")
        except Exception as exc:
            st.error(f"Error executing query: {exc}")
