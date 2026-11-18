"""Create vectors page: PDF -> pages -> chunks -> embeddings -> vector database."""

import pandas as pd
import streamlit as st

from rag import config, stores
from rag.pdf import pdf_to_pages, split_pages

backend = st.session_state.backend
collection = st.session_state.collection
provider = st.session_state.embed_provider

st.write(
    f"Target: **{collection}** in **{backend}**, embedded with "
    f"**{config.embed_label(provider)}**. Change them in the sidebar."
)

needed = config.missing_for_provider(provider) + config.missing_for_backend(backend)
if needed:
    st.error("Add these to your .env file, then restart the app: " + ", ".join(needed))
    st.stop()

# Step 1: upload
files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)

# Step 2: chunk settings
col1, col2 = st.columns(2)
chunk_size = col1.number_input("Chunk size (characters)", 200, 4000, 600, 100)
chunk_overlap = col2.number_input("Chunk overlap (characters)", 0, 1000, 100, 50)
replace = st.checkbox(
    "Replace the existing collection/table",
    help="Off: add the new chunks to the old ones. On: delete old chunks first.",
)

if not files:
    st.info("Upload one or more PDFs to start.")
    st.stop()

if chunk_overlap >= chunk_size:
    st.error("Chunk overlap must be smaller than chunk size.")
    st.stop()

# Step 3: extract and split (fast, so run on every rerun to show a preview)
pages, problems = [], []
for f in files:
    try:
        file_pages = pdf_to_pages(f.name, f.getvalue())
        if not file_pages:
            problems.append(f"{f.name}: no text found (scanned PDF? It needs OCR first).")
        pages.extend(file_pages)
    except Exception as e:
        problems.append(f"{f.name}: {e}")

for p in problems:
    st.warning(p)

chunks = split_pages(pages, chunk_size, chunk_overlap)

c1, c2, c3 = st.columns(3)
c1.metric("Files", len(files))
c2.metric("Pages with text", len(pages))
c3.metric("Chunks", len(chunks))

if not chunks:
    st.stop()

with st.expander("Preview chunks"):
    st.dataframe(
        pd.DataFrame(
            {
                "source": c.metadata["source"],
                "page": c.metadata["page"],
                "chars": len(c.page_content),
                "text": c.page_content[:200],
            }
            for c in chunks
        ),
        hide_index=True,
    )

# Step 4: embed and store
if st.button("Create vectors", type="primary", icon=":material/rocket_launch:"):
    with st.status(f"Embedding {len(chunks)} chunks into {backend}...") as status:
        try:
            stores.write_chunks(backend, collection, chunks, replace, provider)
            stores.after_write()
        except Exception as e:
            status.update(label="Failed", state="error")
            st.error(f"Error: {e}")
            st.stop()
        status.update(label=f"Stored {len(chunks)} chunks in {collection}", state="complete")
    st.success("Done. Go to the **Chat** page to ask questions.")
