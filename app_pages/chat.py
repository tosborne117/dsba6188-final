
"""Chat page: combined PDF RAG and Snowflake text-to-SQL assistant."""

import json
import time

import pandas as pd
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from rag import config, llm, stores
from rag.agent import build_agent
from rag.ui import apply_chat_theme, close_assistant


@st.cache_data(ttl=300, show_spinner=False)
def cached_models(provider):
    return llm.list_chat_models(provider)


# ---------------------------------------------------------
# Application configuration
# ---------------------------------------------------------

backend = st.session_state.backend
collection = st.session_state.collection
embed_provider = st.session_state.embed_provider

chat_open = apply_chat_theme()

if not chat_open:
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------
# Sidebar settings
# ---------------------------------------------------------

with st.sidebar:
    st.header("Chat settings")

    chat_provider = st.selectbox(
        "Chat provider",
        config.PROVIDERS,
    )

    default_model = config.DEFAULT_CHAT_MODEL[chat_provider]
    model_options = [default_model]

    if not config.missing_for_provider(chat_provider):
        try:
            model_options = cached_models(chat_provider) or model_options
        except Exception as e:
            st.error(f"Could not load {chat_provider} models: {e}")

    model_name = st.selectbox(
        "Model",
        model_options,
        index=model_options.index(default_model)
        if default_model in model_options else 0,
        help="Only models that support tool calling are listed.",
    )

    temperature = st.slider(
        "Temperature",
        0.0,
        2.0,
        0.3,
        0.1,
    )

    st.divider()
    st.subheader("Information sources")

    use_rag = st.toggle(
        "Use RAG tools",
        value=True,
    )

    top_k = st.slider(
        "Chunks per document search",
        1,
        10,
        4,
        disabled=not use_rag,
    )

    use_sql = st.toggle(
        "Use Snowflake SQL tools",
        value=True,
    )

    if use_sql:
        st.caption(
            f"SQL source: "
            f"{config.get('SNOWFLAKE_SQL_DATABASE', 'Not configured')}."
            f"{config.get('SNOWFLAKE_SQL_SCHEMA', 'Not configured')}"
        )

    if st.button(
        "Clear chat history",
        icon=":material/delete:",
    ):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------
# Provider validation
# ---------------------------------------------------------

if config.missing_for_provider(chat_provider):
    st.error(
        "GOOGLE_API_KEY is missing. Add it to your .env file "
        "and restart the application."
    )
    st.stop()


# ---------------------------------------------------------
# Document library
# ---------------------------------------------------------

def show_library(sources):
    """Show document and chunk counts."""

    label = (
        f"Library: {len(sources)} documents, "
        f"{sum(sources.values())} chunks"
    )

    with st.expander(label, icon=":material/library_books:"):
        st.dataframe(
            pd.DataFrame(
                sources.items(),
                columns=["Document", "Chunks"],
            ),
            hide_index=True,
        )


# ---------------------------------------------------------
# Tool result rendering
# ---------------------------------------------------------

def render_tool_result(result):
    """Render SQL results as a table and other results as text."""

    try:
        data = json.loads(result) if isinstance(result, str) else result
    except (json.JSONDecodeError, TypeError):
        st.text(result)
        return

    if isinstance(data, dict) and data.get("type") == "sql_result":
        st.caption("Executed SQL")

        with st.expander("View SQL query"):
            st.code(data.get("sql", ""), language="sql")

        columns = data.get("columns", [])
        rows = data.get("rows", [])

        if rows and columns:
            dataframe = pd.DataFrame(rows, columns=columns)

            st.dataframe(
                dataframe,
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("The query returned no rows.")

        st.caption(
            f"Returned {data.get('row_count', 0)} rows."
            + (
                " Results were limited to 100 rows."
                if data.get("truncated")
                else ""
            )
        )

    elif isinstance(data, dict) and data.get("type") == "table_list":
        st.write(
            f"Available tables in "
            f"{data.get('database')}.{data.get('schema')}:"
        )
        st.write(data.get("tables", []))

    elif isinstance(data, dict) and data.get("type") == "column_list":
        st.write(f"Columns in {data.get('table')}:")
        st.dataframe(
            pd.DataFrame(data.get("columns", [])),
            hide_index=True,
            width="stretch",
        )

    else:
        st.text(result)


def step_label(step):
    """Create a readable tool activity label."""

    tool_name = step.get("tool", "unknown tool")
    query = step.get("query", "")

    return f"{tool_name}: {query}" if query else tool_name


def show_steps(steps):
    """Display tool calls and their results."""

    if not steps:
        return

    with st.expander(
        f"Used tools {len(steps)} time(s)",
        type="compact",
    ):
        for step in steps:
            with st.expander(step_label(step), type="step"):
                render_tool_result(step["result"])


# ---------------------------------------------------------
# Open RAG vector store
# ---------------------------------------------------------

store = None
get_sources = None

if use_rag:
    if (
        config.missing_for_backend(backend)
        or config.missing_for_provider(embed_provider)
    ):
        st.info(
            "RAG is unavailable because some settings are missing. "
            "Chat can still use other enabled sources."
        )

    else:
        try:
            if stores.collection_exists(backend, collection):
                stored = stores.stored_embed_model(backend, collection)
                current = config.embed_label(embed_provider)

                if stored and stored != current:
                    st.error(
                        f"'{collection}' was created with **{stored}**, "
                        f"but the selected embedding model is **{current}**. "
                        "Change the provider or select another collection."
                    )

                else:
                    if not stored:
                        st.warning(
                            f"'{collection}' does not record its embedding model. "
                            "Search results may be incorrect if the vectors "
                            "were created with a different model."
                        )

                    store = stores.open_store(
                        backend,
                        collection,
                        embed_provider,
                    )

                    get_sources = lambda: stores.list_sources(
                        backend,
                        collection,
                    )

                    with st.sidebar:
                        st.divider()
                        st.subheader("System Status")

                        st.caption(
                            f"Searching **{collection}** in **{backend}** "
                            f"with `{current}`."
                        )

                        show_library(get_sources())

            else:
                st.info(
                    f"'{collection}' does not exist in {backend} yet. "
                    "Go to **Create vectors** to upload PDFs."
                )

        except Exception as e:
            st.error(f"Could not open {backend}: {e}")


# ---------------------------------------------------------
# Open analytical Snowflake connection
# ---------------------------------------------------------

sql_conn = None

if use_sql:
    missing_sql = config.missing_for_sql()

    if missing_sql:
        st.warning(
            "Snowflake SQL is unavailable. Add these settings to your .env: "
            + ", ".join(missing_sql)
        )

    else:
        try:
            sql_conn = stores.snowflake_sql_connection()

            st.sidebar.success(
                "Snowflake SQL connection ready: "
                f"{config.get('SNOWFLAKE_SQL_DATABASE')}."
                f"{config.get('SNOWFLAKE_SQL_SCHEMA')}"
            )

        except Exception as e:
            st.sidebar.error(f"Could not connect to Snowflake SQL: {e}")



# ---------------------------------------------------------
# Floating chatbot window
# ---------------------------------------------------------

with st.container(key="chat_window"):

    # -----------------------------------------------------
    # Header
    # -----------------------------------------------------

    header_col, close_col = st.columns([9, 1])

    with header_col:
        st.markdown(
            """
            <div class="assistant-heading">
                Eric Virtual Assistant
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Optional close button
    # Uncomment this section if you want the close button visible.

    # with close_col:
    #     if st.button("✕", key="close_chatbot", help="Close chatbot"):
    #         close_assistant()
    #         st.rerun()

    st.divider()

    # -----------------------------------------------------
    # Reserve the conversation area
    # -----------------------------------------------------

    history_area = st.empty()

    # -----------------------------------------------------
    # Input form
    # -----------------------------------------------------

    with st.form("chat_form", clear_on_submit=True):

        prompt = st.text_input(
            "Message",
            placeholder="Ask about your documents or Snowflake data...",
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button(
            "Send",
            use_container_width=True,
        )

    # -----------------------------------------------------
    # Render conversation inside its own scrollable area
    # -----------------------------------------------------

    with history_area.container():

        with st.container(height=470, key="chat_history"):

            # Display previous conversation
            for message in st.session_state.messages:

                with st.chat_message(message["role"]):
                    show_steps(message.get("steps", []))
                    st.markdown(message["content"])

            # -------------------------------------------------
            # Process submitted question
            # -------------------------------------------------

            if submitted and prompt.strip():

                # Display the user's new question
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Build conversation history
                history = [
                    HumanMessage(m["content"])
                    if m["role"] == "user"
                    else AIMessage(m["content"])
                    for m in st.session_state.messages
                ]

                history.append(HumanMessage(prompt))

                # Build agent
                agent = build_agent(
                    provider=chat_provider,
                    model_name=model_name,
                    temperature=temperature,
                    store=store,
                    top_k=top_k,
                    get_sources=get_sources,
                    sql_conn=sql_conn,
                    use_sql=use_sql and sql_conn is not None,
                )

                steps = {}
                answer = ""
                start = time.time()

                # Generate assistant response
                with st.chat_message("assistant"):

                    try:
                        with st.status(
                            ":shimmer[Thinking]",
                            type="compact",
                        ) as status:

                            for update in agent.stream(
                                {"messages": history},
                                stream_mode="updates",
                            ):

                                for node_output in update.values():

                                    for msg in node_output.get("messages", []):

                                        if (
                                            isinstance(msg, AIMessage)
                                            and msg.tool_calls
                                        ):

                                            for call in msg.tool_calls:

                                                steps[call["id"]] = {
                                                    "tool": call["name"],
                                                    "query": (
                                                        call["args"].get("query")
                                                        or call["args"].get("table_name")
                                                        or call["args"].get("sql")
                                                        or ""
                                                    ),
                                                    "result": "",
                                                }

                                        elif (
                                            isinstance(msg, ToolMessage)
                                            and msg.tool_call_id in steps
                                        ):

                                            step = steps[msg.tool_call_id]
                                            step["result"] = msg.text

                                            with st.status(
                                                step_label(step),
                                                type="step",
                                                state="complete",
                                            ):
                                                render_tool_result(msg.text)

                                        elif isinstance(msg, AIMessage):
                                            answer = msg.text

                            status.update(
                                label=(
                                    f"Thought for "
                                    f"{time.time() - start:.0f} seconds"
                                ),
                                state="complete",
                            )

                    except Exception as e:
                        st.error(f"Error: {e}")
                        st.stop()

                    st.markdown(answer or "_No answer returned._")

                # -------------------------------------------------
                # Save both turns
                # -------------------------------------------------

                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": prompt,
                    }
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "steps": list(steps.values()),
                    }
                )

                # Refresh to display the saved conversation
                st.rerun()
