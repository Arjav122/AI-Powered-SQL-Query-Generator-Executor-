import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
API_PORT = os.getenv("BACKEND_PORT", "8000")
API_URL = f"http://{API_HOST}:{API_PORT}"

st.set_page_config(page_title="AI SQL Assistant", page_icon="🧠", layout="wide")
st.title("🧠 AI SQL Assistant")
st.caption("Generate and run read-only SQL queries from natural language.")

if "generated_sql" not in st.session_state:
    st.session_state.generated_sql = ""
if "databases" not in st.session_state:
    st.session_state.databases = []


def get_json(url: str):
    try:
        response = requests.get(url, timeout=20)
        if response.ok:
            return response.json(), None
        return None, response.text
    except requests.RequestException as exc:
        return None, str(exc)


def post_json(url: str, payload: dict):
    try:
        response = requests.post(url, json=payload, timeout=45)
        if response.ok:
            return response.json(), None
        return None, response.text
    except requests.RequestException as exc:
        return None, str(exc)


st.sidebar.header("Schema Explorer")
if st.sidebar.button("Refresh Databases"):
    data, error = get_json(f"{API_URL}/list_databases/")
    if error:
        st.sidebar.error(f"Unable to fetch databases: {error}")
    else:
        st.session_state.databases = data.get("databases", [])

selected_db = st.sidebar.selectbox("Database", [""] + st.session_state.databases)
tables = []
if selected_db:
    data, error = get_json(f"{API_URL}/list_tables/{selected_db}")
    if error:
        st.sidebar.error(f"Unable to fetch tables: {error}")
    else:
        tables = data.get("tables", [])

selected_tables = st.sidebar.multiselect("Tables (for JOIN/UNION)", tables)
for table_name in selected_tables[:3]:
    data, error = get_json(f"{API_URL}/list_columns/{selected_db}/{table_name}")
    if error:
        st.sidebar.error(f"Unable to fetch columns for {table_name}: {error}")
    else:
        st.sidebar.write(f"Columns: {table_name}")
        st.sidebar.write(data.get("columns", []))

if tables:
    st.sidebar.write("Suggested tables")
    st.sidebar.write(tables[:3])

col1, col2 = st.columns(2)

with col1:
    st.subheader("Generate SQL")
    if not selected_db:
        st.info("Select a database from sidebar first for better SQL quality.")
    elif not selected_tables:
        st.info("Select one or more tables from sidebar for accurate JOIN/UNION queries.")
    natural_language_query = st.text_area(
        "Ask in plain English",
        placeholder="Example: Show top 10 customers by total order value.",
        height=180,
    )
    if st.button("Generate SQL", type="primary"):
        payload = {
            "natural_language_query": natural_language_query,
            "database_name": selected_db or None,
            "table_names": selected_tables or None,
        }
        data, error = post_json(f"{API_URL}/generate_sql/", payload)
        if error:
            st.error(f"Error generating SQL: {error}")
            st.session_state.generated_sql = ""
        else:
            st.session_state.generated_sql = data.get("sql_query", "")

    if st.session_state.generated_sql:
        st.code(st.session_state.generated_sql, language="sql")

with col2:
    st.subheader("Execute SQL")
    manual_sql_query = st.text_area(
        "Read-only SQL only",
        value=st.session_state.generated_sql,
        height=180,
    )
    if st.button("Run Query"):
        payload = {"sql_query": manual_sql_query}
        data, error = post_json(f"{API_URL}/execute_sql/", payload)
        if error:
            st.error(f"Error executing query: {error}")
        else:
            results = data.get("results", [])
            if results:
                st.dataframe(results, use_container_width=True)
            else:
                st.info("Query ran successfully but returned no rows.")