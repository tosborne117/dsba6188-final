"""A small LangChain vector store on a Snowflake table.

The table has one row per chunk:

    ID          STRING
    SOURCE      STRING
    PAGE        INT
    CHUNK_TEXT  STRING
    EMBED_MODEL STRING
    EMBEDDING   VECTOR(FLOAT, <dim>)

Search uses VECTOR_COSINE_SIMILARITY, so no extra Snowflake service is needed.
"""

import json
import re
import uuid
from pathlib import Path

import snowflake.connector
from cryptography.hazmat.primitives import serialization
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from rag import config

INSERT_BATCH = 100


def load_private_key():
    """Return the RSA private key as DER bytes, which the connector expects.

    The key comes from SNOWFLAKE_PRIVATE_KEY_PATH (a .p8 file) or from
    SNOWFLAKE_PRIVATE_KEY (the PEM text itself). The path wins if both are set.
    """
    path = config.get("SNOWFLAKE_PRIVATE_KEY_PATH")
    if path:
        key_path = Path(path).expanduser()
        if not key_path.is_absolute():
            key_path = config.APP_DIR / key_path
        pem = key_path.read_bytes()
    else:
        # A one-line .env value stores line breaks as "\n"
        pem = config.get("SNOWFLAKE_PRIVATE_KEY").replace("\\n", "\n").encode()

    passphrase = config.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    key = serialization.load_pem_private_key(
        pem, password=passphrase.encode() if passphrase else None
    )
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connect():
    """Open a Snowflake connection with key-pair (RSA) authentication."""
    return snowflake.connector.connect(
        account=config.get("SNOWFLAKE_ACCOUNT"),
        user=config.get("SNOWFLAKE_USER"),
        private_key=load_private_key(),
        role=config.get("SNOWFLAKE_ROLE"),
        warehouse=config.get("SNOWFLAKE_WAREHOUSE"),
        database=config.get("SNOWFLAKE_DATABASE"),
        schema=config.get("SNOWFLAKE_SCHEMA"),
    )


def safe_table_name(name):
    """Allow only letters, digits, and underscores, because the name goes into SQL."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(
            f"'{name}' is not a valid table name. Use letters, digits, and underscores."
        )
    return name.upper()


class SnowflakeVectorStore(VectorStore):
    def __init__(self, conn, table, embedding, dim=768):
        self.conn = conn
        self.table = safe_table_name(table)
        self._embedding = embedding
        self.dim = dim

    @property
    def embeddings(self):
        return self._embedding

    def create_table(self, replace=False):
        verb = "CREATE OR REPLACE TABLE" if replace else "CREATE TABLE IF NOT EXISTS"
        self.conn.cursor().execute(
            f"""{verb} {self.table} (
                ID STRING,
                SOURCE STRING,
                PAGE INT,
                CHUNK_TEXT STRING,
                EMBED_MODEL STRING,
                EMBEDDING VECTOR(FLOAT, {self.dim})
            )"""
        )

    def stored_embed_model(self):
        """Return the embedding model of the first row, or None."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(f"SELECT EMBED_MODEL FROM {self.table} LIMIT 1")
        except snowflake.connector.ProgrammingError:
            return None  # an older table with no EMBED_MODEL column
        row = cursor.fetchone()
        return row[0] if row else None

    def add_texts(self, texts, metadatas=None, **kwargs):
        texts = list(texts)
        metadatas = metadatas or [{} for _ in texts]
        vectors = self._embedding.embed_documents(texts)
        ids = [str(uuid.uuid4()) for _ in texts]

        rows = [
            (
                id_,
                meta.get("source"),
                meta.get("page"),
                text,
                meta.get("embed_model"),
                json.dumps(vector),
            )
            for id_, text, meta, vector in zip(ids, texts, metadatas, vectors)
        ]
        cursor = self.conn.cursor()
        # Snowflake cannot bind a VECTOR directly. Send the vector as JSON text
        # and cast it: text -> VARIANT -> ARRAY -> VECTOR.
        for start in range(0, len(rows), INSERT_BATCH):
            batch = rows[start : start + INSERT_BATCH]
            values = ", ".join(["(%s, %s, %s, %s, %s, %s)"] * len(batch))
            params = [value for row in batch for value in row]
            cursor.execute(
                f"""INSERT INTO {self.table}
                    (ID, SOURCE, PAGE, CHUNK_TEXT, EMBED_MODEL, EMBEDDING)
                SELECT column1, column2, column3, column4, column5,
                       PARSE_JSON(column6)::ARRAY::VECTOR(FLOAT, {self.dim})
                FROM VALUES {values}""",
                params,
            )
        return ids

    def similarity_search_with_score(self, query, k=4, **kwargs):
        vector = json.dumps(self._embedding.embed_query(query))
        cursor = self.conn.cursor()
        cursor.execute(
            f"""SELECT CHUNK_TEXT, SOURCE, PAGE,
                   VECTOR_COSINE_SIMILARITY(
                       EMBEDDING, PARSE_JSON(%s)::ARRAY::VECTOR(FLOAT, {self.dim})
                   ) AS SCORE
            FROM {self.table}
            ORDER BY SCORE DESC
            LIMIT %s""",
            (vector, int(k)),
        )
        return [
            (Document(page_content=text, metadata={"source": source, "page": page}), score)
            for text, source, page, score in cursor.fetchall()
        ]

    def similarity_search(self, query, k=4, **kwargs):
        return [doc for doc, _ in self.similarity_search_with_score(query, k)]

    @classmethod
    def from_texts(cls, texts, embedding, metadatas=None, *, conn, table, **kwargs):
        store = cls(conn, table, embedding)
        store.create_table()
        store.add_texts(texts, metadatas)
        return store
