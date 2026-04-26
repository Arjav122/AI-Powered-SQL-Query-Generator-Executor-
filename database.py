import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus
import re

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _validate_identifier(value: str, kind: str) -> str:
    if not value or not SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {kind} name.")
    return value


def _build_database_url() -> str:
    encoded_password = quote_plus(MYSQL_PASSWORD)
    if MYSQL_DATABASE:
        return f"mysql+mysqlconnector://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    return f"mysql+mysqlconnector://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}"

try:
    DATABASE_URL = _build_database_url()
    logger.debug("Connecting to MySQL at %s:%s", MYSQL_HOST, MYSQL_PORT)
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    logger.debug("Database engine initialized.")
except Exception as e:
    logger.error("Database initialization failed: %s", str(e))
    raise


def list_databases():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SHOW DATABASES;")).fetchall()
            return {"databases": [row[0] for row in result]}
    except Exception as e:
        return {"error": str(e)}

def list_tables(database_name):
    try:
        db = _validate_identifier(database_name, "database")
        with engine.connect() as connection:
            result = connection.execute(text(f"SHOW TABLES FROM `{db}`;")).fetchall()
            return {"tables": [row[0] for row in result]}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def list_columns(database_name, table_name):
    try:
        db = _validate_identifier(database_name, "database")
        table = _validate_identifier(table_name, "table")
        with engine.connect() as connection:
            result = connection.execute(text(f"SHOW COLUMNS FROM `{db}`.`{table}`;")).fetchall()
            return {"columns": [row[0] for row in result]}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
