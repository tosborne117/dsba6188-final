"""DSBA 6188 RAG Agent: entry point.

Run from this folder:
    streamlit run streamlit_app.py

The sidebar settings here are shared by both pages.
"""

import streamlit as st

from rag import config, stores

st.set_page_config(page_title="RAG Agent", page_icon=":material/smart_toy:")


def pick_collection(backend):
    """Pick an existing collection/table, or type a new name for Create vectors."""
    kind = "collection" if backend == "Qdrant" else "table"
    try:
        names = stores.list_collections(backend)
    except Exception as e:
        st.error(f"Cannot list {backend} {kind}s: {e}")
        return None
    # Snowflake stores table names in upper case
    default = config.DEFAULT_COLLECTION
    if backend == "Snowflake":
        default = default.upper()
    picked = st.selectbox(
        kind.capitalize(),
        names,
        index=names.index(default) if default in names else (0 if names else None),
        key=f"{backend.lower()}_collection",
        accept_new_options=True,
        placeholder=f"Type a new {kind} name",
        help=f"{len(names)} {kind}(s) in {backend} that this app can search. "
        "Type a new name to create it on the Create vectors page.",
    )
    if not names:
        st.info(f"No {kind}s in {backend} yet. Type a name for your first {kind}.")
    # An empty database has nothing to preselect, so the user must type a name
    return picked or ""

page = st.navigation(
    [
        st.Page(
            "app_pages/ingest.py",
            title="Create vectors",
            icon=":material/upload_file:",
            default=True,
        ),
        st.Page(
            "app_pages/chat.py",
            title="Chat",
            icon=":material/chat:",
        ),
    ],
    position="top",
)

with st.sidebar:
    st.header("Vector database")
    st.selectbox("Backend", config.BACKENDS, key="backend")
    backend = st.session_state.backend
    name = None
    if not config.missing_for_backend(backend):
        name = pick_collection(backend)
    if name is None:
        # No connection to the database: type the name
        name = st.text_input(
            "Collection / table name",
            value=config.DEFAULT_COLLECTION,
            key="collection_name",
            help="Qdrant collection name or Snowflake table name.",
        )
    # Both pages read the selected name from here
    st.session_state.collection = name
    st.selectbox(
        "Embedding provider",
        config.PROVIDERS,
        key="embed_provider",
        help="Create vectors and Chat must use the same embedding model "
        "for one collection. Use one collection per embedding model.",
    )
    provider = st.session_state.embed_provider
    st.caption(f"Embeddings: {config.embed_label(provider)} ({config.EMBED_DIM[provider]} dims)")

    # Tell the user which .env values are still empty
    needed = config.missing_for_provider(provider) + config.missing_for_backend(
        st.session_state.backend
    )
    if needed:
        st.warning("Add these to your .env file, then restart the app:\n\n- " + "\n- ".join(needed))
    else:
        st.success(f"{st.session_state.backend} settings found in .env")

# Both pages need a collection/table name
if not st.session_state.collection:
    kind = "collection" if backend == "Qdrant" else "table"
    st.info(
        f"Name the {kind} first. Type a {kind} name in the sidebar.",
        icon=":material/edit:",
    )
    st.stop()

page.run()
