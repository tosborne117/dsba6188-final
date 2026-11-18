# DSBA 6188 RAG Agent

A Streamlit app with two pages:

- **Chat**: an Ollama or Gemini agent (LangGraph ReAct) with the RAG tools `search_documents` and `list_documents`.
- **Create vectors**: upload PDFs, split them into chunks, embed them, and store them.

Vector database: **Qdrant** or **Snowflake** (select in the sidebar).

The sidebar list shows what you can query:

- **Qdrant**: the **Collection** list shows every collection in your cluster.
- **Snowflake**: the **Table** list shows the tables in the current schema that
  have the `SOURCE`, `CHUNK_TEXT`, and `EMBEDDING` columns.

Select one to query it. To make a new one, type a new name in the list, then
run **Create vectors**. If the database has none yet, both pages stay blank and
ask you to type a name first. If the app cannot connect, a text box replaces the list.

See `PLAN.html` for the design and diagrams.

## Setup

The app packages are in the Python 3.14 venv. `activate_venv.sh` is in the
parent `Code` folder.

```bash
source ../activate_venv.sh 14   # run from dsba6188_rag_agent
pip install -r requirements.txt
cp .env.example .env      # then fill in the values
streamlit run streamlit_app.py
```

For Snowflake, put your key at `keys/rsa_key.p8` (see `keys/README.md`).

## Files

| File | Job |
| --- | --- |
| `streamlit_app.py` | Navigation and shared sidebar (backend, collection list, providers) |
| `app_pages/chat.py` | Chat UI, shows each tool call |
| `app_pages/ingest.py` | PDF upload, chunk preview, "Create vectors" |
| `rag/config.py` | Reads `.env` |
| `rag/llm.py` | Gemini chat model and embeddings |
| `rag/agent.py` | Agent and the `search_documents` tool |
| `rag/pdf.py` | PDF to pages to chunks |
| `rag/stores.py` | One interface for both databases; lists collections/tables |
| `rag/snowflake_store.py` | Snowflake vector store (RSA key auth, `VECTOR` column) |

## Notes

- Use one collection per embedding model. The Chat page turns RAG off if the
  collection was made with a different model from the sidebar embedding provider.
  If you change the model or dimension, use a new collection/table.
- The collection list refreshes every 60 seconds and right after **Create vectors**.
- Default chunk size is 600 characters with 100 characters of overlap. Change
  them on the **Create vectors** page.
- Gemma models are hidden in the model list. They do not support tool calling.
