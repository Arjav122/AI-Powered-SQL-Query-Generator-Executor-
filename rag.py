"""ChromaDB retrieval: index the schema (one document per table) and few-shot question->SQL examples."""
import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.config import Settings
from openai import OpenAI

import db

CHROMA_PATH = "./chroma_data"
EMBEDDING_MODEL = "text-embedding-3-small"
FEW_SHOT_FILE = Path(__file__).with_name("few_shot.json")
_disk_client = None
_memory_client = None


def _chroma(conn_key: str = ""):
    """Demo database -> saved on disk. User connections ("mem..." keys) -> RAM only, never written to disk."""
    global _disk_client, _memory_client
    settings = Settings(anonymized_telemetry=False)
    if conn_key.startswith("mem"):
        if _memory_client is None:
            _memory_client = chromadb.EphemeralClient(settings=settings)
        return _memory_client
    if _disk_client is None:
        _disk_client = chromadb.PersistentClient(path=CHROMA_PATH, settings=settings)
    return _disk_client


def embed(texts: list[str]) -> list[list[float]]:
    """Embed texts with OpenAI. We pass vectors to Chroma ourselves (no hidden embedding model)."""
    api_key = db.get_setting("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing (set it in .env or Streamlit secrets).")
    response = OpenAI(api_key=api_key).embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def _schema_collection(conn_key: str):
    return _chroma(conn_key).get_or_create_collection(f"schema_{conn_key}", embedding_function=None)


def _examples_collection(conn_key: str):
    return _chroma(conn_key).get_or_create_collection(f"fewshot_{conn_key}", embedding_function=None)


# ---------- Schema index ----------

def table_document(table: dict) -> str:
    """Text the LLM sees for one table (also what gets embedded)."""
    columns = []
    for col in table["columns"]:
        sample = f" e.g. {', '.join(repr(s) for s in col['samples'])}" if col.get("samples") else ""
        columns.append(f"  - {col['name']} ({col['type']}){sample}")
    lines = [f"Table: {table['name']}", "Columns:", *columns]
    if table["primary_key"]:
        lines.append(f"Primary key: {', '.join(table['primary_key'])}")
    for fk in table["foreign_keys"]:
        lines.append(f"Foreign key: {fk['column']} -> {fk['ref_table']}.{fk['ref_column']}")
    return "\n".join(lines)


def ensure_index(engine, cfg: dict, force: bool = False) -> dict:
    """Index the schema into Chroma. Skips work if the schema hash hasn't changed (unless force=True)."""
    conn_key = db.connection_key(cfg)
    schema = db.read_schema(engine, db.user_databases(engine, cfg))
    new_hash = db.schema_hash(schema)
    collection = _schema_collection(conn_key)

    if not force and collection.count() > 0 and (collection.metadata or {}).get("schema_hash") == new_hash:
        return {"status": "up to date", "tables": collection.count()}
    if not schema:
        return {"status": "no tables found", "tables": 0}

    db.add_sample_values(engine, schema)
    documents = [table_document(t) for t in schema]
    _chroma(conn_key).delete_collection(f"schema_{conn_key}")
    collection = _chroma(conn_key).create_collection(
        f"schema_{conn_key}", embedding_function=None, metadata={"schema_hash": new_hash})
    collection.add(
        ids=[t["name"] for t in schema],
        documents=documents,
        embeddings=embed(documents),
        metadatas=[{"fk_targets": ",".join(fk["ref_table"] for fk in t["foreign_keys"])} for t in schema],
    )
    return {"status": "re-indexed", "tables": len(schema)}


def all_tables(conn_key: str) -> list[dict]:
    """Every indexed table (used for full-schema mode)."""
    data = _schema_collection(conn_key).get(include=["documents"])
    return [{"name": i, "document": d, "via": "full schema"} for i, d in zip(data["ids"], data["documents"])]


def retrieve_tables(conn_key: str, query_embedding: list[float], k: int = 5) -> list[dict]:
    """Top-k tables by similarity, plus tables linked by a foreign key (1 hop, both directions)."""
    collection = _schema_collection(conn_key)
    if collection.count() == 0:
        return []
    hits = collection.query(query_embeddings=[query_embedding], n_results=min(k, collection.count()),
                            include=["documents", "metadatas"])
    found = {name: {"name": name, "document": doc, "via": "similarity"}
             for name, doc in zip(hits["ids"][0], hits["documents"][0])}

    everything = collection.get(include=["documents", "metadatas"])
    linked = set()
    for name, meta in zip(everything["ids"], everything["metadatas"]):
        targets = set(filter(None, (meta or {}).get("fk_targets", "").split(",")))
        if name in found:
            linked |= targets            # retrieved table -> tables it references
        elif targets & found.keys():
            linked.add(name)             # tables that reference a retrieved table
    for name, doc in zip(everything["ids"], everything["documents"]):
        if name in linked and name not in found:
            found[name] = {"name": name, "document": doc, "via": "foreign key"}
    return list(found.values())


# ---------- Few-shot examples ----------

def _example_id(question: str) -> str:
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()[:16]


def seed_examples(conn_key: str) -> int:
    """Load few_shot.json into the examples collection (only if it is empty). Returns example count."""
    collection = _examples_collection(conn_key)
    if collection.count() == 0 and FEW_SHOT_FILE.exists():
        examples = json.loads(FEW_SHOT_FILE.read_text(encoding="utf-8"))
        if examples:
            questions = [e["question"] for e in examples]
            collection.upsert(
                ids=[_example_id(q) for q in questions],
                documents=questions,
                embeddings=embed(questions),
                metadatas=[{"sql": e["sql"]} for e in examples],
            )
    return collection.count()


def reset_examples(conn_key: str) -> int:
    """Delete the examples collection and re-seed it from few_shot.json (used by eval.py)."""
    try:
        _chroma(conn_key).delete_collection(f"fewshot_{conn_key}")
    except Exception:
        pass  # didn't exist yet
    return seed_examples(conn_key)


def forget(conn_key: str) -> None:
    """Remove everything stored for a connection (used when a user switches or disconnects)."""
    for name in (f"schema_{conn_key}", f"fewshot_{conn_key}"):
        try:
            _chroma(conn_key).delete_collection(name)
        except Exception:
            pass  # nothing stored yet


def add_example(conn_key: str, question: str, sql: str) -> None:
    """Save a question->SQL pair the user liked (👍) so similar questions get it as an example."""
    _examples_collection(conn_key).upsert(
        ids=[_example_id(question)], documents=[question],
        embeddings=embed([question]), metadatas=[{"sql": sql}])


def retrieve_examples(conn_key: str, query_embedding: list[float], n: int = 3) -> list[dict]:
    collection = _examples_collection(conn_key)
    if collection.count() == 0:
        return []
    hits = collection.query(query_embeddings=[query_embedding], n_results=min(n, collection.count()),
                            include=["documents", "metadatas"])
    return [{"question": q, "sql": m["sql"]} for q, m in zip(hits["documents"][0], hits["metadatas"][0])]
