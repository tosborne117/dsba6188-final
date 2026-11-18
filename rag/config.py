"""Load settings from .env files.

The app reads two .env files:
1. dsba6188_rag_agent/.env  (this project)
2. Code/.env                (the parent folder, shared by other demos)

Values in the project .env win. Values that are already set in the
shell environment win over both.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent.parent

load_dotenv(APP_DIR / ".env")
load_dotenv(APP_DIR.parent / ".env")

# Model providers. Ollama runs locally, so it has no API quota.
OLLAMA = "Ollama"
GOOGLE = "Google AI Studio"
PROVIDERS = [OLLAMA, GOOGLE]

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

DEFAULT_CHAT_MODEL = {
    OLLAMA: os.getenv("OLLAMA_CHAT_MODEL", "gemma4:e2b"),
    GOOGLE: os.getenv("GOOGLE_CHAT_MODEL", "gemini-3.5-flash"),
}

# Embeddings: the model that creates the vectors must also embed the queries.
# If you change a model or dimension, use a new collection/table.
EMBED_MODEL = {
    OLLAMA: os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:v1.5"),
    GOOGLE: os.getenv("GOOGLE_EMBED_MODEL", "gemini-embedding-001"),
}
EMBED_DIM = {
    OLLAMA: int(os.getenv("OLLAMA_EMBED_DIM", "768")),
    GOOGLE: int(os.getenv("GOOGLE_EMBED_DIM", "768")),
}

DEFAULT_COLLECTION = os.getenv("RAG_COLLECTION", "dsba6188_docs")

BACKENDS = ["Qdrant", "Snowflake"]


def embed_label(provider):
    """Name of the embedding model, saved with each chunk, e.g. 'ollama/nomic-embed-text:v1.5'."""
    prefix = "ollama" if provider == OLLAMA else "google"
    return f"{prefix}/{EMBED_MODEL[provider]}"


def get(name, default=None):
    """Return one setting. Empty strings count as missing."""
    value = os.getenv(name, "").strip()
    return value or default


def missing(names):
    """Return the names in `names` that have no value."""
    return [n for n in names if not get(n)]


QDRANT_VARS = ["QDRANT_URL", "QDRANT_API_KEY"]
SNOWFLAKE_VARS = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
]
# Separate Snowflake source for text-to-SQL.
# These settings do not change the database used for RAG vector storage.
SNOWFLAKE_SQL_VARS = [
    "SNOWFLAKE_SQL_DATABASE",
    "SNOWFLAKE_SQL_SCHEMA",
]


def missing_for_sql():
    """Return missing settings required for Snowflake text-to-SQL."""
    return missing_for_backend("Snowflake") + missing(SNOWFLAKE_SQL_VARS)

def missing_for_provider(provider):
    """Return the .env names that the selected model provider still needs."""
    return missing(["GOOGLE_API_KEY"]) if provider == GOOGLE else []


def missing_for_backend(backend):
    """Return the .env names that the selected backend still needs."""
    if backend == "Qdrant":
        return missing(QDRANT_VARS)
    names = missing(SNOWFLAKE_VARS)
    # Snowflake needs a key from one of two places (see .env.example)
    if not (get("SNOWFLAKE_PRIVATE_KEY_PATH") or get("SNOWFLAKE_PRIVATE_KEY")):
        names.append("SNOWFLAKE_PRIVATE_KEY_PATH (or SNOWFLAKE_PRIVATE_KEY)")
    return names
