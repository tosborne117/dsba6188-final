"""One entry point for both vector databases.

The chat page and the ingest page call these functions only, so they do not
need to know which database is in use.

`provider` is the embedding provider (Ollama or Google AI Studio). Each chunk
stores the name of its embedding model, so the chat page can check that the
query uses the same model.
"""

import streamlit as st

from rag import config, llm


@st.cache_resource(show_spinner="Connecting to Snowflake...")
def snowflake_connection():
    """Open one Snowflake connection and reuse it across reruns."""
    from rag.snowflake_store import connect

    return connect()
@st.cache_resource(show_spinner="Connecting to Snowflake SQL...")
def snowflake_sql_connection():
    """Open and reuse the analytical Snowflake connection."""
    from rag.text_to_sql import connect_sql

    return connect_sql()

@st.cache_resource(show_spinner=False)
def qdrant_client():
    from qdrant_client import QdrantClient

    return QdrantClient(url=config.get("QDRANT_URL"), api_key=config.get("QDRANT_API_KEY"))


@st.cache_data(ttl=60, show_spinner=False)
def list_collections(backend):
    """Return the Qdrant collections, or Snowflake vector-store tables."""
    if backend == "Qdrant":
        return sorted(
            c.name for c in qdrant_client().get_collections().collections
        )

    database = config.get("SNOWFLAKE_DATABASE").upper()
    schema = config.get("SNOWFLAKE_SCHEMA").upper()

    cursor = snowflake_connection().cursor()

    try:
        cursor.execute(
            f"""
            SELECT TABLE_NAME
            FROM {database}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND COLUMN_NAME IN ('SOURCE', 'CHUNK_TEXT', 'EMBEDDING')
            GROUP BY TABLE_NAME
            HAVING COUNT(DISTINCT COLUMN_NAME) = 3
            ORDER BY TABLE_NAME
            """,
            (schema,),
        )

        return [row[0] for row in cursor.fetchall()]

    finally:
        cursor.close()


def collection_exists(backend, name):
    if backend == "Qdrant":
        return qdrant_client().collection_exists(name)

    from rag.snowflake_store import safe_table_name

    database = config.get("SNOWFLAKE_DATABASE").upper()
    schema = config.get("SNOWFLAKE_SCHEMA").upper()
    table = safe_table_name(name)

    cursor = snowflake_connection().cursor()

    try:
        cursor.execute(
            f"SHOW TABLES LIKE '{table}' IN SCHEMA {database}.{schema}"
        )
        return bool(cursor.fetchall())
    finally:
        cursor.close()


def stored_embed_model(backend, name):
    """Return the embedding model saved in the collection, or None if unknown."""
    if backend == "Qdrant":
        points, _ = qdrant_client().scroll(
            collection_name=name, limit=1, with_payload=True, with_vectors=False
        )
        if not points:
            return None
        return (points[0].payload.get("metadata") or {}).get("embed_model")

    from rag.snowflake_store import SnowflakeVectorStore

    return SnowflakeVectorStore(snowflake_connection(), name, None).stored_embed_model()


@st.cache_data(ttl=60, show_spinner=False)
def list_sources(backend, name):
    """Return {source file: number of chunks} for one collection/table."""
    if backend == "Qdrant":
        counts, offset = {}, None
        while True:
            # Read only the source field, not the text or the vectors
            points, offset = qdrant_client().scroll(
                collection_name=name,
                limit=1000,
                offset=offset,
                with_payload=["metadata.source"],
                with_vectors=False,
            )
            for p in points:
                source = (p.payload.get("metadata") or {}).get("source", "unknown")
                counts[source] = counts.get(source, 0) + 1
            if offset is None:
                return dict(sorted(counts.items()))

    from rag.snowflake_store import safe_table_name

    cursor = snowflake_connection().cursor()
    cursor.execute(
        f"SELECT SOURCE, COUNT(*) FROM {safe_table_name(name)} GROUP BY SOURCE ORDER BY SOURCE"
    )
    return dict(cursor.fetchall())


def open_store(backend, name, provider):
    """Open an existing collection (Qdrant) or table (Snowflake) for search."""
    if backend == "Qdrant":
        from langchain_qdrant import QdrantVectorStore

        return QdrantVectorStore(
            client=qdrant_client(), collection_name=name, embedding=llm.embeddings(provider)
        )
    from rag.snowflake_store import SnowflakeVectorStore

    return SnowflakeVectorStore(
        snowflake_connection(), name, llm.embeddings(provider), config.EMBED_DIM[provider]
    )


def write_chunks(backend, name, chunks, replace, provider):
    """Embed `chunks` and store them. `replace=True` deletes old data first."""
    for chunk in chunks:
        chunk.metadata["embed_model"] = config.embed_label(provider)

    if backend == "Qdrant":
        from langchain_qdrant import QdrantVectorStore

        QdrantVectorStore.from_documents(
            chunks,
            llm.embeddings(provider),
            url=config.get("QDRANT_URL"),
            api_key=config.get("QDRANT_API_KEY"),
            collection_name=name,
            force_recreate=replace,
        )
        return
    from rag.snowflake_store import SnowflakeVectorStore

    store = SnowflakeVectorStore(
        snowflake_connection(), name, llm.embeddings(provider), config.EMBED_DIM[provider]
    )
    store.create_table(replace=replace)
    store.add_documents(chunks)


def after_write():
    """Clear the cached lists so the sidebar and Chat page show the new data."""
    list_sources.clear()
    list_collections.clear()
